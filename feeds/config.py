"""
Feed Aggregator Configuration
Zero-cost sources using free tiers only
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class SourceType(Enum):
    RSS = "rss"
    TWITTER = "twitter"
    TELEGRAM = "telegram"
    REDDIT = "reddit"
    OSINT = "osint"


@dataclass
class SourceConfig:
    name: str
    source_type: SourceType
    url: Optional[str] = None
    handle: Optional[str] = None
    poll_interval: int = 300  # seconds
    priority: int = 5  # 1-10, higher = more important
    enabled: bool = True


# Default source configurations
SOURCES: Dict[str, List[SourceConfig]] = {
    "rss": [
        SourceConfig(
            name="Reuters Top News",
            source_type=SourceType.RSS,
            url="https://feeds.reuters.com/reuters/topNews",
            poll_interval=300,
            priority=8
        ),
        SourceConfig(
            name="BBC World",
            source_type=SourceType.RSS,
            url="http://feeds.bbci.co.uk/news/world/rss.xml",
            poll_interval=300,
            priority=8
        ),
        SourceConfig(
            name="Al Jazeera",
            source_type=SourceType.RSS,
            url="https://www.aljazeera.com/xml/rss/all.xml",
            poll_interval=300,
            priority=7
        ),
        SourceConfig(
            name="AP News",
            source_type=SourceType.RSS,
            url="https://rsshub.app/apnews/topics/apf-topnews",
            poll_interval=300,
            priority=8
        ),
    ],
    "twitter": [
        # Using Nitter instances for free access
        SourceConfig(
            name="Elon Musk",
            source_type=SourceType.TWITTER,
            handle="@elonmusk",
            poll_interval=600,
            priority=6
        ),
        SourceConfig(
            name="Reuters",
            source_type=SourceType.TWITTER,
            handle="@reuters",
            poll_interval=300,
            priority=7
        ),
        SourceConfig(
            name="Breaking News",
            source_type=SourceType.TWITTER,
            handle="@breakingnews",
            poll_interval=300,
            priority=9
        ),
    ],
    "telegram": [
        SourceConfig(
            name="Breaking News",
            source_type=SourceType.TELEGRAM,
            handle="@breakingnews",
            poll_interval=300,
            priority=8
        ),
        SourceConfig(
            name="Intel Slava",
            source_type=SourceType.TELEGRAM,
            handle="@intelslava",
            poll_interval=600,
            priority=6
        ),
    ],
    "reddit": [
        SourceConfig(
            name="World News",
            source_type=SourceType.REDDIT,
            handle="r/worldnews",
            poll_interval=300,
            priority=7
        ),
        SourceConfig(
            name="Geopolitics",
            source_type=SourceType.REDDIT,
            handle="r/geopolitics",
            poll_interval=600,
            priority=6
        ),
        SourceConfig(
            name="OSINT",
            source_type=SourceType.REDDIT,
            handle="r/OSINT",
            poll_interval=600,
            priority=7
        ),
        SourceConfig(
            name="Conflict News",
            source_type=SourceType.REDDIT,
            handle="r/conflictnews",
            poll_interval=600,
            priority=6
        ),
    ],
    "osint": [
        SourceConfig(
            name="ADS-B Exchange",
            source_type=SourceType.OSINT,
            url="https://api.adsbexchange.com/v2/",
            poll_interval=60,  # Aircraft data updates frequently
            priority=5
        ),
        SourceConfig(
            name="MarineTraffic",
            source_type=SourceType.OSINT,
            url="https://www.marinetraffic.com/en/ais/home/",
            poll_interval=300,
            priority=4
        ),
    ]
}

# Rate limiting configuration
RATE_LIMITS = {
    "default": {
        "requests_per_minute": 30,
        "burst_size": 10,
    },
    "rss": {
        "requests_per_minute": 20,
        "burst_size": 5,
    },
    "twitter": {
        "requests_per_minute": 10,  # Be polite to Nitter
        "burst_size": 3,
    },
    "telegram": {
        "requests_per_minute": 15,
        "burst_size": 5,
    },
    "reddit": {
        "requests_per_minute": 30,  # 60 requests per minute for OAuth
        "burst_size": 10,
    },
    "osint": {
        "requests_per_minute": 10,
        "burst_size": 3,
    },
}

# Retry configuration
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2.0,
}

# Signal scoring weights
SIGNAL_WEIGHTS = {
    "source_reliability": 0.3,
    "recency": 0.2,
    "engagement": 0.2,
    "keyword_importance": 0.3,
}

# High-priority keywords for importance scoring
PRIORITY_KEYWORDS = [
    "breaking", "urgent", "alert", "emergency",
    "war", "conflict", "attack", "strike",
    "sanctions", "embargo", "diplomatic",
    "election", "coup", "protest", "revolution",
    "cyberattack", "hack", "breach",
    "natural disaster", "earthquake", "hurricane",
    "market crash", "economic crisis",
]
