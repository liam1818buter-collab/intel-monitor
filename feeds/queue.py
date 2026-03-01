"""
Signal Queue Module
In-memory queue with deduplication and priority scoring
"""

import hashlib
import time
from typing import List, Optional, Dict, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class SignalSource(Enum):
    RSS = "rss"
    TWITTER = "twitter"
    TELEGRAM = "telegram"
    REDDIT = "reddit"
    OSINT = "osint"
    MANUAL = "manual"


class SignalType(Enum):
    NEWS = "news"
    ALERT = "alert"
    SOCIAL = "social"
    INTELLIGENCE = "intelligence"
    TRANSPORT = "transport"
    EVENT = "event"


@dataclass
class Signal:
    """A signal from any source"""
    id: str = field(default_factory=lambda: hashlib.md5(
        str(time.time()).encode()
    ).hexdigest()[:16])
    source: SignalSource = SignalSource.MANUAL
    source_name: str = ""
    signal_type: SignalType = SignalType.NEWS
    title: str = ""
    content: str = ""
    url: Optional[str] = None
    author: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    importance_score: float = 0.0  # 0-10
    metadata: Dict = field(default_factory=dict)
    processed: bool = False
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique ID from content hash"""
        content = f"{self.source.value}:{self.source_name}:{self.title}:{self.content[:200]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "source": self.source.value,
            "source_name": self.source_name,
            "signal_type": self.signal_type.value,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "author": self.author,
            "timestamp": self.timestamp,
            "importance_score": self.importance_score,
            "metadata": self.metadata,
            "processed": self.processed,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Signal":
        """Create from dictionary"""
        return cls(
            id=data.get("id", ""),
            source=SignalSource(data.get("source", "manual")),
            source_name=data.get("source_name", ""),
            signal_type=SignalType(data.get("signal_type", "news")),
            title=data.get("title", ""),
            content=data.get("content", ""),
            url=data.get("url"),
            author=data.get("author"),
            timestamp=data.get("timestamp", time.time()),
            importance_score=data.get("importance_score", 0.0),
            metadata=data.get("metadata", {}),
            processed=data.get("processed", False),
        )


class SignalQueue:
    """
    Priority queue for signals with deduplication
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        dedup_window: int = 3600,  # 1 hour
        priority_keywords: Optional[List[str]] = None
    ):
        self.max_size = max_size
        self.dedup_window = dedup_window
        self.priority_keywords = priority_keywords or []
        
        # Storage
        self._queue: List[Signal] = []
        self._seen_hashes: Set[str] = set()
        self._seen_timestamps: Dict[str, float] = {}
        
        # Statistics
        self._stats = {
            "added": 0,
            "deduplicated": 0,
            "dropped": 0,
            "retrieved": 0,
        }
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def _generate_content_hash(self, signal: Signal) -> str:
        """Generate content hash for deduplication"""
        # Normalize content
        content = f"{signal.title.lower().strip()}:{signal.content[:300].lower().strip()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def _calculate_importance(self, signal: Signal) -> float:
        """Calculate importance score for a signal"""
        score = 0.0
        
        # Base score from source priority
        source_scores = {
            SignalSource.RSS: 5.0,
            SignalSource.TWITTER: 4.0,
            SignalSource.TELEGRAM: 4.5,
            SignalSource.REDDIT: 3.5,
            SignalSource.OSINT: 6.0,
            SignalSource.MANUAL: 7.0,
        }
        score += source_scores.get(signal.source, 3.0)
        
        # Check priority keywords
        text = f"{signal.title} {signal.content}".lower()
        keyword_hits = sum(1 for kw in self.priority_keywords if kw.lower() in text)
        score += min(keyword_hits * 1.5, 5.0)  # Max 5 points from keywords
        
        # Recency boost (newer = higher)
        age_hours = (time.time() - signal.timestamp) / 3600
        if age_hours < 1:
            score += 2.0
        elif age_hours < 6:
            score += 1.0
        elif age_hours < 24:
            score += 0.5
        
        # Engagement boost (if available)
        if signal.metadata:
            likes = signal.metadata.get("likes", 0)
            shares = signal.metadata.get("shares", 0)
            comments = signal.metadata.get("comments", 0)
            engagement = likes + shares * 2 + comments
            score += min(engagement / 1000, 2.0)  # Max 2 points
        
        return min(score, 10.0)  # Cap at 10
    
    async def add(self, signal: Signal) -> bool:
        """Add a signal to the queue"""
        async with self._lock:
            # Calculate importance
            signal.importance_score = self._calculate_importance(signal)
            
            # Generate content hash for deduplication
            content_hash = self._generate_content_hash(signal)
            
            # Clean old entries from dedup window
            now = time.time()
            old_hashes = [
                h for h, ts in self._seen_timestamps.items()
                if now - ts > self.dedup_window
            ]
            for h in old_hashes:
                self._seen_hashes.discard(h)
                del self._seen_timestamps[h]
            
            # Check for duplicate
            if content_hash in self._seen_hashes:
                self._stats["deduplicated"] += 1
                logger.debug(f"Deduplicated signal: {signal.title[:50]}...")
                return False
            
            # Check if queue is full
            if len(self._queue) >= self.max_size:
                # Remove lowest priority item
                self._queue.sort(key=lambda s: s.importance_score)
                removed = self._queue.pop(0)
                self._stats["dropped"] += 1
                logger.debug(f"Dropped low-priority signal: {removed.title[:50]}...")
            
            # Add to queue and tracking
            signal.id = content_hash[:16]
            self._queue.append(signal)
            self._seen_hashes.add(content_hash)
            self._seen_timestamps[content_hash] = now
            self._stats["added"] += 1
            
            # Sort by importance (highest first)
            self._queue.sort(key=lambda s: s.importance_score, reverse=True)
            
            logger.debug(
                f"Added signal: {signal.title[:50]}... (score: {signal.importance_score:.2f})"
            )
            return True
    
    async def add_many(self, signals: List[Signal]) -> int:
        """Add multiple signals, return count added"""
        added = 0
        for signal in signals:
            if await self.add(signal):
                added += 1
        return added
    
    async def get(self, count: int = 1, mark_processed: bool = True) -> List[Signal]:
        """Get highest priority signals from the queue"""
        async with self._lock:
            # Get unprocessed signals
            unprocessed = [s for s in self._queue if not s.processed]
            
            # Sort by importance
            unprocessed.sort(key=lambda s: s.importance_score, reverse=True)
            
            # Get top N
            result = unprocessed[:count]
            
            if mark_processed:
                for signal in result:
                    signal.processed = True
            
            self._stats["retrieved"] += len(result)
            return result
    
    async def get_new_signals(self, count: int = 100) -> List[Signal]:
        """Get new (unprocessed) signals"""
        return await self.get(count=count, mark_processed=True)
    
    async def peek(self, count: int = 10) -> List[Signal]:
        """Peek at signals without marking processed"""
        return await self.get(count=count, mark_processed=False)
    
    async def clear(self) -> None:
        """Clear all signals"""
        async with self._lock:
            self._queue.clear()
            self._seen_hashes.clear()
            self._seen_timestamps.clear()
            logger.info("Signal queue cleared")
    
    async def get_stats(self) -> Dict:
        """Get queue statistics"""
        async with self._lock:
            unprocessed = sum(1 for s in self._queue if not s.processed)
            return {
                "total_signals": len(self._queue),
                "unprocessed": unprocessed,
                "processed": len(self._queue) - unprocessed,
                **self._stats,
            }
    
    async def size(self) -> int:
        """Get current queue size"""
        async with self._lock:
            return len(self._queue)
    
    async def unprocessed_count(self) -> int:
        """Get count of unprocessed signals"""
        async with self._lock:
            return sum(1 for s in self._queue if not s.processed)
    
    def __len__(self) -> int:
        return len(self._queue)


class SignalBuffer:
    """
    Temporary buffer for batching signals before adding to main queue
    """
    
    def __init__(self, queue: SignalQueue, batch_size: int = 10, flush_interval: float = 5.0):
        self.queue = queue
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: List[Signal] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the background flush task"""
        self._flush_task = asyncio.create_task(self._flush_loop())
    
    async def stop(self) -> None:
        """Stop the background task and flush remaining"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
    
    async def _flush_loop(self) -> None:
        """Background loop to periodically flush buffer"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
    
    async def add(self, signal: Signal) -> None:
        """Add signal to buffer"""
        async with self._lock:
            self._buffer.append(signal)
            
            if len(self._buffer) >= self.batch_size:
                await self._flush_locked()
    
    async def add_many(self, signals: List[Signal]) -> None:
        """Add multiple signals"""
        async with self._lock:
            self._buffer.extend(signals)
            
            if len(self._buffer) >= self.batch_size:
                await self._flush_locked()
    
    async def flush(self) -> int:
        """Flush buffer to main queue"""
        async with self._lock:
            return await self._flush_locked()
    
    async def _flush_locked(self) -> int:
        """Internal flush (must hold lock)"""
        if not self._buffer:
            return 0
        
        signals = self._buffer[:]
        self._buffer = []
        
        added = await self.queue.add_many(signals)
        logger.debug(f"Flushed {added} signals to queue")
        return added
