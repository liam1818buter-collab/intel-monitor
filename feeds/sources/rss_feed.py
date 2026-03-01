"""
RSS Feed Adapter
Poll RSS/Atom feeds for news and updates
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, AsyncGenerator
from datetime import datetime
import logging
from html import unescape

from ..queue import Signal, SignalSource, SignalType
from ..rate_limiter import RateLimiter
from ..config import SourceConfig

logger = logging.getLogger(__name__)


class RSSFeedAdapter:
    """
    Adapter for RSS/Atom feed sources
    """
    
    # Common RSS namespaces
    NAMESPACES = {
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'atom': 'http://www.w3.org/2005/Atom',
        'media': 'http://search.yahoo.com/mrss/',
    }
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        user_agent: str = "IntelMonitor/1.0"
    ):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.user_agent = user_agent
        self.seen_ids: Dict[str, float] = {}  # Track seen items
        self.dedup_window = 86400  # 24 hours
    
    async def fetch_feed(self, url: str) -> Optional[str]:
        """Fetch feed content with rate limiting"""
        source_id = f"rss:{url}"
        
        async def _fetch():
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        raise Exception(f"HTTP {response.status}")
        
        if self.rate_limiter:
            return await self.rate_limiter.with_retry(source_id, _fetch)
        else:
            return await _fetch()
    
    def parse_feed(self, content: str, source_name: str = "") -> List[Signal]:
        """Parse RSS/Atom feed content into signals"""
        signals = []
        
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse feed: {e}")
            return signals
        
        # Detect feed type
        tag = root.tag.lower()
        
        if 'feed' in tag:
            # Atom feed
            signals = self._parse_atom(root, source_name)
        elif 'rss' in tag or 'channel' in tag:
            # RSS feed
            signals = self._parse_rss(root, source_name)
        else:
            # Try RSS structure
            channel = root.find('.//channel')
            if channel is not None:
                signals = self._parse_rss(root, source_name)
            else:
                logger.warning(f"Unknown feed format: {tag}")
        
        return signals
    
    def _parse_rss(self, root: ET.Element, source_name: str) -> List[Signal]:
        """Parse RSS 2.0 feed"""
        signals = []
        
        channel = root.find('.//channel')
        if channel is None:
            return signals
        
        # Get feed title
        feed_title = ""
        title_elem = channel.find('title')
        if title_elem is not None and title_elem.text:
            feed_title = title_elem.text
        
        # Parse items
        for item in channel.findall('item'):
            try:
                signal = self._parse_rss_item(item, feed_title or source_name)
                if signal and self._is_new(signal):
                    signals.append(signal)
            except Exception as e:
                logger.debug(f"Error parsing RSS item: {e}")
                continue
        
        return signals
    
    def _parse_rss_item(self, item: ET.Element, source_name: str) -> Optional[Signal]:
        """Parse single RSS item"""
        # Extract fields
        title = self._get_text(item, 'title')
        link = self._get_text(item, 'link')
        description = self._get_text(item, 'description')
        pub_date = self._get_text(item, 'pubDate')
        guid = self._get_text(item, 'guid')
        
        # Content might be in content:encoded
        content_encoded = item.find('content:encoded', self.NAMESPACES)
        if content_encoded is not None and content_encoded.text:
            content = content_encoded.text
        else:
            content = description
        
        # Parse date
        timestamp = self._parse_date(pub_date)
        
        # Create unique ID
        item_id = guid or link or f"{title}:{timestamp}"
        
        # Clean HTML
        content = self._clean_html(content or "")
        
        return Signal(
            id=hash(item_id) % 10000000000000000,
            source=SignalSource.RSS,
            source_name=source_name,
            signal_type=SignalType.NEWS,
            title=unescape(title or ""),
            content=content,
            url=link,
            timestamp=timestamp,
            metadata={
                "guid": guid,
                "published": pub_date,
            }
        )
    
    def _parse_atom(self, root: ET.Element, source_name: str) -> List[Signal]:
        """Parse Atom feed"""
        signals = []
        
        # Get feed title
        feed_title = ""
        title_elem = root.find('atom:title', self.NAMESPACES)
        if title_elem is not None and title_elem.text:
            feed_title = title_elem.text
        
        # Parse entries
        for entry in root.findall('atom:entry', self.NAMESPACES):
            try:
                signal = self._parse_atom_entry(entry, feed_title or source_name)
                if signal and self._is_new(signal):
                    signals.append(signal)
            except Exception as e:
                logger.debug(f"Error parsing Atom entry: {e}")
                continue
        
        return signals
    
    def _parse_atom_entry(self, entry: ET.Element, source_name: str) -> Optional[Signal]:
        """Parse single Atom entry"""
        title = self._get_text_atom(entry, 'title')
        
        # Get link
        link_elem = entry.find('atom:link', self.NAMESPACES)
        link = link_elem.get('href') if link_elem is not None else None
        
        # Get content
        content = self._get_text_atom(entry, 'content')
        if not content:
            content = self._get_text_atom(entry, 'summary')
        
        # Get published/updated date
        published = self._get_text_atom(entry, 'published')
        updated = self._get_text_atom(entry, 'updated')
        pub_date = published or updated
        
        # Get ID
        entry_id = self._get_text_atom(entry, 'id')
        
        # Parse date
        timestamp = self._parse_atom_date(pub_date)
        
        # Clean content
        content = self._clean_html(content or "")
        
        return Signal(
            id=hash(entry_id or link or title) % 10000000000000000,
            source=SignalSource.RSS,
            source_name=source_name,
            signal_type=SignalType.NEWS,
            title=unescape(title or ""),
            content=content,
            url=link,
            timestamp=timestamp,
            metadata={
                "entry_id": entry_id,
                "published": pub_date,
            }
        )
    
    def _get_text(self, parent: ET.Element, tag: str) -> Optional[str]:
        """Get text content of child element"""
        elem = parent.find(tag)
        if elem is not None:
            return elem.text
        return None
    
    def _get_text_atom(self, parent: ET.Element, tag: str) -> Optional[str]:
        """Get text content of Atom child element"""
        elem = parent.find(f'atom:{tag}', self.NAMESPACES)
        if elem is not None:
            # Handle type="html"
            content_type = elem.get('type', 'text')
            if content_type == 'html':
                return elem.text
            return elem.text
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> float:
        """Parse RSS date string to timestamp"""
        if not date_str:
            return datetime.now().timestamp()
        
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.timestamp()
            except ValueError:
                continue
        
        return datetime.now().timestamp()
    
    def _parse_atom_date(self, date_str: Optional[str]) -> float:
        """Parse Atom date string to timestamp"""
        if not date_str:
            return datetime.now().timestamp()
        
        try:
            # ISO format with timezone
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(date_str)
            return dt.timestamp()
        except ValueError:
            pass
        
        return self._parse_date(date_str)
    
    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from content"""
        import re
        # Remove script and style elements
        html = re.sub(r'<(script|style)[^>]*>[^<]*</\1>', '', html, flags=re.I)
        # Remove HTML tags
        html = re.sub(r'<[^>]+>', ' ', html)
        # Unescape HTML entities
        html = unescape(html)
        # Normalize whitespace
        html = re.sub(r'\s+', ' ', html).strip()
        return html
    
    def _is_new(self, signal: Signal) -> bool:
        """Check if signal is new (not seen before)"""
        # Clean old entries
        now = datetime.now().timestamp()
        old_ids = [
            sid for sid, ts in self.seen_ids.items()
            if now - ts > self.dedup_window
        ]
        for sid in old_ids:
            del self.seen_ids[sid]
        
        # Check if seen
        signal_key = f"{signal.source_name}:{signal.title}"
        if signal_key in self.seen_ids:
            return False
        
        self.seen_ids[signal_key] = now
        return True
    
    async def poll_source(self, config: SourceConfig) -> List[Signal]:
        """Poll a single RSS source"""
        if not config.url:
            logger.warning(f"No URL for RSS source: {config.name}")
            return []
        
        try:
            logger.debug(f"Polling RSS feed: {config.name}")
            content = await self.fetch_feed(config.url)
            
            if content:
                signals = self.parse_feed(content, config.name)
                logger.info(f"Retrieved {len(signals)} signals from {config.name}")
                return signals
            
        except Exception as e:
            logger.error(f"Error polling {config.name}: {e}")
        
        return []
    
    async def monitor(
        self,
        configs: List[SourceConfig],
        callback,
        poll_interval: Optional[int] = None
    ) -> None:
        """Continuously monitor RSS feeds"""
        logger.info(f"Starting RSS monitor with {len(configs)} sources")
        
        while True:
            for config in configs:
                if not config.enabled:
                    continue
                
                try:
                    signals = await self.poll_source(config)
                    if signals:
                        await callback(signals)
                except Exception as e:
                    logger.error(f"Error in RSS monitor for {config.name}: {e}")
                
                # Small delay between sources
                await asyncio.sleep(1)
            
            # Wait before next poll cycle
            interval = poll_interval or 300
            await asyncio.sleep(interval)
