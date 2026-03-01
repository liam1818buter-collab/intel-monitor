"""
Rate Limiter Module
Token bucket implementation with politeness controls
"""

import asyncio
import time
import random
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int
    tokens: float = field(default=0)
    fill_rate: float = field(default=0)
    last_update: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def __post_init__(self):
        self.tokens = self.capacity
    
    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens from the bucket"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.fill_rate
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.fill_rate if self.fill_rate > 0 else float('inf')
            
            if timeout is not None and wait_time > timeout:
                return False
            
            await asyncio.sleep(wait_time)
            self.tokens -= tokens
            return True
    
    async def consume(self, tokens: int = 1) -> None:
        """Consume tokens (blocks until available)"""
        while True:
            async with self.lock:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(
                    self.capacity,
                    self.tokens + elapsed * self.fill_rate
                )
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)


@dataclass
class RetryState:
    """Track retry state for exponential backoff"""
    failures: int = 0
    last_failure: float = field(default_factory=time.time)
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    
    def get_delay(self) -> float:
        """Calculate next retry delay with jitter"""
        delay = min(
            self.base_delay * (self.exponential_base ** self.failures),
            self.max_delay
        )
        # Add jitter (±25%)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        return delay + jitter
    
    def record_failure(self) -> None:
        """Record a failure"""
        self.failures += 1
        self.last_failure = time.time()
    
    def record_success(self) -> None:
        """Reset failure count on success"""
        self.failures = 0
    
    def should_retry(self, max_retries: int = 3) -> bool:
        """Check if we should retry"""
        return self.failures < max_retries


class RateLimiter:
    """
    Centralized rate limiter with token buckets per source
    and exponential backoff for failures
    """
    
    def __init__(
        self,
        default_rpm: int = 30,
        default_burst: int = 10,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self.buckets: Dict[str, TokenBucket] = {}
        self.retry_states: Dict[str, RetryState] = defaultdict(
            lambda: RetryState(
                base_delay=base_delay,
                max_delay=max_delay
            )
        )
        self.default_config = {
            "requests_per_minute": default_rpm,
            "burst_size": default_burst,
        }
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
    def register_source(
        self,
        source_id: str,
        requests_per_minute: Optional[int] = None,
        burst_size: Optional[int] = None
    ) -> None:
        """Register a new source with rate limiting"""
        rpm = requests_per_minute or self.default_config["requests_per_minute"]
        burst = burst_size or self.default_config["burst_size"]
        
        fill_rate = rpm / 60.0
        
        self.buckets[source_id] = TokenBucket(
            capacity=burst,
            fill_rate=fill_rate
        )
        
        logger.debug(
            f"Registered source {source_id}: {rpm} RPM, burst={burst}"
        )
    
    async def acquire(self, source_id: str, tokens: int = 1) -> bool:
        """Acquire permission to make a request"""
        if source_id not in self.buckets:
            # Auto-register with defaults
            self.register_source(source_id)
        
        # Check if we're in backoff
        retry_state = self.retry_states[source_id]
        if retry_state.failures > 0:
            delay = retry_state.get_delay()
            if time.time() - retry_state.last_failure < delay:
                await asyncio.sleep(delay)
        
        bucket = self.buckets[source_id]
        return await bucket.acquire(tokens)
    
    def record_success(self, source_id: str) -> None:
        """Record successful request"""
        self.retry_states[source_id].record_success()
    
    def record_failure(self, source_id: str) -> None:
        """Record failed request for backoff calculation"""
        self.retry_states[source_id].record_failure()
    
    async def with_retry(
        self,
        source_id: str,
        operation,
        *args,
        **kwargs
    ):
        """Execute operation with rate limiting and retry logic"""
        retry_state = self.retry_states[source_id]
        
        for attempt in range(self.max_retries + 1):
            # Wait for rate limit
            await self.acquire(source_id)
            
            try:
                result = await operation(*args, **kwargs)
                self.record_success(source_id)
                return result
                
            except Exception as e:
                self.record_failure(source_id)
                
                if not retry_state.should_retry(self.max_retries):
                    logger.error(
                        f"Max retries exceeded for {source_id}: {e}"
                    )
                    raise
                
                delay = retry_state.get_delay()
                logger.warning(
                    f"Request failed for {source_id} (attempt {attempt + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)
        
        raise Exception(f"Unexpected exit from retry loop for {source_id}")


class PolitenessChecker:
    """
    Check and respect robots.txt
    """
    
    def __init__(self):
        self.robots_cache: Dict[str, str] = {}
        self.cache_ttl = 3600  # 1 hour
        self.last_fetch: Dict[str, float] = {}
    
    async def fetch_robots_txt(self, base_url: str) -> Optional[str]:
        """Fetch robots.txt for a domain"""
        import aiohttp
        
        # Check cache
        now = time.time()
        if base_url in self.last_fetch:
            if now - self.last_fetch[base_url] < self.cache_ttl:
                return self.robots_cache.get(base_url)
        
        try:
            robots_url = f"{base_url.rstrip('/')}/robots.txt"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    robots_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        self.robots_cache[base_url] = content
                        self.last_fetch[base_url] = now
                        return content
        except Exception as e:
            logger.debug(f"Failed to fetch robots.txt from {base_url}: {e}")
        
        return None
    
    def can_fetch(self, robots_txt: Optional[str], user_agent: str, path: str) -> bool:
        """Check if path is allowed for user agent"""
        if not robots_txt:
            return True
        
        # Simple robots.txt parsing
        lines = robots_txt.split('\n')
        current_agent = None
        rules = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'user-agent':
                    if current_agent and rules:
                        # Check if this applies to us
                        if self._agent_matches(current_agent, user_agent):
                            return self._check_path_allowed(rules, path)
                    current_agent = value
                    rules = []
                
                elif key == 'disallow' and current_agent:
                    rules.append(('disallow', value))
                elif key == 'allow' and current_agent:
                    rules.append(('allow', value))
        
        # Check last agent block
        if current_agent and rules:
            if self._agent_matches(current_agent, user_agent):
                return self._check_path_allowed(rules, path)
        
        return True
    
    def _agent_matches(self, pattern: str, user_agent: str) -> bool:
        """Check if user agent matches pattern"""
        pattern = pattern.lower()
        user_agent = user_agent.lower()
        
        if pattern == '*':
            return True
        
        return pattern in user_agent or user_agent in pattern
    
    def _check_path_allowed(self, rules: list, path: str) -> bool:
        """Check if path is allowed given rules"""
        allowed = True
        
        for rule_type, rule_path in rules:
            if path.startswith(rule_path):
                if rule_type == 'disallow':
                    allowed = False
                elif rule_type == 'allow':
                    allowed = True
        
        return allowed
