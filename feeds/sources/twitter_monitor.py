"""
Twitter/X Monitor Adapter
Uses Nitter instances for free access to Twitter
"""

import asyncio
import aiohttp
import json
import re
from typing import List, Optional, Dict
from datetime import datetime
from html import unescape
import logging

from ..queue import Signal, SignalSource, SignalType
from ..rate_limiter import RateLimiter
from ..config import SourceConfig

logger = logging.getLogger(__name__)


class TwitterMonitorAdapter:
    """
    Adapter for Twitter/X using Nitter instances (free alternative)
    """
    
    # Working Nitter instances (rotated for reliability)
    NITTER_INSTANCES = [
        "https://nitter.net",
        "https://nitter.cz",
        "https://nitter.privacydev.net",
        "https://nitter.projectsegfault.com",
    ]
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        user_agent: str = "IntelMonitor/1.0"
    ):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.user_agent = user_agent
        self.seen_ids: Dict[str, float] = {}
        self.dedup_window = 86400  # 24 hours
        self.instance_index = 0
        self.failed_instances: set = set()
    
    def _get_nitter_instance(self) -> str:
        """Get next Nitter instance (with rotation)"""
        available = [i for i in self.NITTER_INSTANCES if i not in self.failed_instances]
        
        if not available:
            # Reset failed instances and try again
            self.failed_instances.clear()
            available = self.NITTER_INSTANCES
        
        instance = available[self.instance_index % len(available)]
        self.instance_index += 1
        return instance
    
    async def fetch_tweets(
        self,
        handle: str,
        count: int = 20
    ) -> List[Dict]:
        """Fetch tweets from a handle via Nitter"""
        # Clean handle
        handle = handle.lstrip('@')
        source_id = f"twitter:{handle}"
        
        instance = self._get_nitter_instance()
        url = f"{instance}/{handle}/json"
        
        async def _fetch():
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status in [429, 503, 502]:
                        # Rate limit or service unavailable - mark instance as failed
                        self.failed_instances.add(instance)
                        raise Exception(f"Instance {instance} unavailable (HTTP {response.status})")
                    else:
                        raise Exception(f"HTTP {response.status}")
        
        # Try multiple instances
        last_error = None
        for _ in range(min(3, len(self.NITTER_INSTANCES))):
            try:
                if self.rate_limiter:
                    return await self.rate_limiter.with_retry(source_id, _fetch)
                else:
                    return await _fetch()
            except Exception as e:
                last_error = e
                self.failed_instances.add(instance)
                instance = self._get_nitter_instance()
                url = f"{instance}/{handle}/json"
                await asyncio.sleep(1)
        
        raise last_error or Exception("All Nitter instances failed")
    
    def parse_tweets(
        self,
        data: List[Dict],
        handle: str,
        source_name: str = ""
    ) -> List[Signal]:
        """Parse Nitter JSON into signals"""
        signals = []
        
        if not isinstance(data, list):
            logger.warning(f"Unexpected data format from Nitter: {type(data)}")
            return signals
        
        for tweet in data:
            try:
                signal = self._parse_tweet(tweet, handle, source_name)
                if signal and self._is_new(signal):
                    signals.append(signal)
            except Exception as e:
                logger.debug(f"Error parsing tweet: {e}")
                continue
        
        return signals
    
    def _parse_tweet(
        self,
        tweet: Dict,
        handle: str,
        source_name: str
    ) -> Optional[Signal]:
        """Parse a single tweet"""
        # Extract fields
        tweet_id = str(tweet.get('id', ''))
        content = tweet.get('content', '') or tweet.get('text', '')
        created_at = tweet.get('date', '') or tweet.get('created_at', '')
        likes = tweet.get('likes', 0) or 0
        retweets = tweet.get('retweets', 0) or tweet.get('retweetCount', 0) or 0
        replies = tweet.get('replies', 0) or tweet.get('replyCount', 0) or 0
        
        # Skip if no content
        if not content:
            return None
        
        # Parse date
        timestamp = self._parse_twitter_date(created_at)
        
        # Build URL
        url = f"https://twitter.com/{handle}/status/{tweet_id}"
        
        # Clean content
        content = unescape(content)
        
        # Create title from content (first 100 chars)
        title = content[:100] + "..." if len(content) > 100 else content
        
        # Check for media
        has_media = bool(tweet.get('media'))
        
        return Signal(
            id=tweet_id,
            source=SignalSource.TWITTER,
            source_name=source_name or f"@{handle}",
            signal_type=SignalType.SOCIAL,
            title=title,
            content=content,
            url=url,
            author=handle,
            timestamp=timestamp,
            metadata={
                "tweet_id": tweet_id,
                "likes": likes,
                "shares": retweets,
                "comments": replies,
                "has_media": has_media,
                "created_at": created_at,
            }
        )
    
    def _parse_twitter_date(self, date_str: str) -> float:
        """Parse Twitter date to timestamp"""
        if not date_str:
            return datetime.now().timestamp()
        
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%a %b %d %H:%M:%S +0000 %Y',
            '%Y-%m-%d %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.timestamp()
            except ValueError:
                continue
        
        # Try ISO format
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.timestamp()
        except ValueError:
            pass
        
        return datetime.now().timestamp()
    
    def _is_new(self, signal: Signal) -> bool:
        """Check if signal is new"""
        now = datetime.now().timestamp()
        
        # Clean old entries
        old_ids = [
            sid for sid, ts in self.seen_ids.items()
            if now - ts > self.dedup_window
        ]
        for sid in old_ids:
            del self.seen_ids[sid]
        
        # Check if seen
        if signal.id in self.seen_ids:
            return False
        
        self.seen_ids[signal.id] = now
        return True
    
    async def poll_source(self, config: SourceConfig) -> List[Signal]:
        """Poll a single Twitter source"""
        if not config.handle:
            logger.warning(f"No handle for Twitter source: {config.name}")
            return []
        
        try:
            handle = config.handle.lstrip('@')
            logger.debug(f"Polling Twitter: @{handle}")
            
            data = await self.fetch_tweets(handle)
            signals = self.parse_tweets(data, handle, config.name)
            
            logger.info(f"Retrieved {len(signals)} tweets from @{handle}")
            return signals
            
        except Exception as e:
            logger.error(f"Error polling Twitter {config.name}: {e}")
            return []
    
    async def monitor(
        self,
        configs: List[SourceConfig],
        callback,
        poll_interval: Optional[int] = None
    ) -> None:
        """Continuously monitor Twitter handles"""
        logger.info(f"Starting Twitter monitor with {len(configs)} sources")
        
        while True:
            for config in configs:
                if not config.enabled:
                    continue
                
                try:
                    signals = await self.poll_source(config)
                    if signals:
                        await callback(signals)
                except Exception as e:
                    logger.error(f"Error in Twitter monitor for {config.name}: {e}")
                
                # Be polite between requests
                await asyncio.sleep(2)
            
            # Wait before next poll cycle
            interval = poll_interval or 600
            await asyncio.sleep(interval)
    
    async def search(
        self,
        query: str,
        count: int = 20
    ) -> List[Signal]:
        """Search tweets (limited support via Nitter)"""
        # Note: Nitter search is limited/unreliable
        # This is a placeholder for future implementation
        logger.warning("Twitter search via Nitter is limited")
        return []
