"""
Signal Classification Engine
Categorizes incoming signals by type and importance
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import re


class SignalType(Enum):
    BREAKING = "breaking"      # 🔴 Urgent news, disasters
    OSINT = "osint"           # 🟡 Satellite, analysis data
    SOCIAL = "social"         # 🔵 X/Twitter, Telegram
    MILITARY = "military"     # 🟢 Aircraft, naval tracking
    ECONOMIC = "economic"     # 🟠 Market moves, policy


class ImportanceLevel(Enum):
    LOW = 0.2
    MEDIUM = 0.5
    HIGH = 0.8
    CRITICAL = 1.0


@dataclass
class Signal:
    id: str
    timestamp: datetime
    source: str
    source_type: str  # rss, twitter, telegram, osint
    content: str
    classification: SignalType = SignalType.OSINT
    importance: float = 0.5
    entities: List[str] = field(default_factory=list)
    location: Optional[str] = None
    related_situation: Optional[str] = None
    raw_data: dict = field(default_factory=dict)


class SignalClassifier:
    """Classify signals by content and source"""
    
    # Keywords for each classification
    PATTERNS = {
        SignalType.BREAKING: [
            'breaking', 'urgent', 'alert', 'disaster', 'crash', 'explosion',
            'attack', 'assassination', 'coup', 'invasion', 'declaration of war',
            'emergency', 'evacuation', 'lockdown'
        ],
        SignalType.MILITARY: [
            'military', 'troop', 'deployment', 'aircraft', 'navy', 'carrier',
            'missile', 'drone', 'uav', 'fighter jet', 'bomber', 'tank',
            'artillery', 'naval', 'submarine', 'callsign', 'squawk'
        ],
        SignalType.ECONOMIC: [
            'market', 'stock', 'trading', 'fed', 'federal reserve', 'inflation',
            'gdp', 'earnings', 'revenue', 'merger', 'acquisition', 'bankruptcy',
            'sanctions', 'tariff', 'trade war'
        ],
        SignalType.SOCIAL: [
            'trending', 'viral', 'tweet', 'post', 'rumor', 'speculation',
            'whale', 'pump', 'dump', 'sentiment', 'viral'
        ]
    }
    
    def classify(self, content: str, source: str, source_type: str) -> SignalType:
        """Classify signal based on content and source"""
        content_lower = content.lower()
        
        # Check each pattern
        scores = {}
        for sig_type, keywords in self.PATTERNS.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[sig_type] = score
        
        # Return highest scoring type, or OSINT as default
        if scores:
            return max(scores, key=scores.get)
        
        # Source-based fallback
        if source_type in ['twitter', 'telegram']:
            return SignalType.SOCIAL
        elif source_type in ['adsb', 'vessel']:
            return SignalType.MILITARY
        
        return SignalType.OSINT


class ImportanceScorer:
    """Score signal importance 0-1"""
    
    # High-impact keywords boost score
    IMPACT_KEYWORDS = [
        'war', 'nuclear', 'invasion', 'coup', 'assassination',
        'crash', 'collapse', 'crisis', 'emergency', 'breaking'
    ]
    
    # Trusted sources get boost
    TRUSTED_SOURCES = [
        'reuters', 'bloomberg', 'ft.com', 'wsj', 'cnn', 'bbc',
        'defense', 'military', 'government'
    ]
    
    def score(self, content: str, source: str, classification: SignalType) -> float:
        """Calculate importance score"""
        score = 0.0
        content_lower = content.lower()
        source_lower = source.lower()
        
        # Base score by classification
        base_scores = {
            SignalType.BREAKING: 0.8,
            SignalType.MILITARY: 0.6,
            SignalType.ECONOMIC: 0.5,
            SignalType.SOCIAL: 0.3,
            SignalType.OSINT: 0.4
        }
        score += base_scores.get(classification, 0.4)
        
        # Keyword boost
        for kw in self.IMPACT_KEYWORDS:
            if kw in content_lower:
                score += 0.1
        
        # Source credibility
        for trusted in self.TRUSTED_SOURCES:
            if trusted in source_lower:
                score += 0.1
                break
        
        # Content length factor (very short = less important)
        if len(content) < 50:
            score -= 0.1
        
        return min(1.0, max(0.0, score))


class EntityExtractor:
    """Extract entities from signal content"""
    
    # Common locations
    LOCATIONS = [
        'ukraine', 'russia', 'china', 'taiwan', 'israel', 'gaza', 'iran',
        'korea', 'japan', 'india', 'pakistan', 'syria', 'lebanon',
        'poland', 'germany', 'france', 'uk', 'usa', 'america',
        'moscow', 'beijing', 'washington', 'london', 'paris', 'tel aviv'
    ]
    
    # Organizations
    ORGS = [
        'nato', 'eu', 'un', 'federal reserve', 'ecb', 'imf', 'world bank',
        'pentagon', 'kremlin', 'white house', 'congress', 'parliament'
    ]
    
    def extract(self, content: str) -> tuple[List[str], Optional[str]]:
        """Extract entities and primary location"""
        content_lower = content.lower()
        entities = []
        location = None
        
        for loc in self.LOCATIONS:
            if loc in content_lower:
                entities.append(loc.title())
                if not location:
                    location = loc.title()
        
        for org in self.ORGS:
            if org in content_lower:
                entities.append(org.upper())
        
        return entities, location


def process_signal(raw_content: str, source: str, source_type: str, signal_id: str = None) -> Signal:
    """Process raw signal into classified Signal object"""
    from uuid import uuid4
    
    classifier = SignalClassifier()
    scorer = ImportanceScorer()
    extractor = EntityExtractor()
    
    # Classify
    classification = classifier.classify(raw_content, source, source_type)
    
    # Score
    importance = scorer.score(raw_content, source, classification)
    
    # Extract entities
    entities, location = extractor.extract(raw_content)
    
    return Signal(
        id=signal_id or str(uuid4())[:8],
        timestamp=datetime.utcnow(),
        source=source,
        source_type=source_type,
        content=raw_content,
        classification=classification,
        importance=importance,
        entities=entities,
        location=location
    )
