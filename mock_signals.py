"""
Mock Signal Generator for Intel Monitor Dashboard
Generates realistic-looking intelligence signals for demo purposes
"""

import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import uuid

@dataclass
class Signal:
    id: str
    timestamp: datetime
    classification: str  # BREAKING, OSINT, SOCIAL, MILITARY, ECONOMIC
    source: str
    source_icon: str
    title: str
    content: str
    location: Optional[str] = None
    confidence: str = "MEDIUM"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

# Signal classification configurations
CLASSIFICATIONS = {
    "BREAKING": {
        "color": "#ff3333",
        "bg_color": "rgba(255, 51, 51, 0.15)",
        "icon": "🔴",
        "sources": ["Reuters", "AP News", "BBC Breaking", "CNN Breaking", "Bloomberg"],
        "source_icons": ["📡", "📰", "📺", "🌐", "💹"],
    },
    "OSINT": {
        "color": "#ffcc00",
        "bg_color": "rgba(255, 204, 0, 0.15)",
        "icon": "🟡",
        "sources": ["Bellingcat", "GeoConfirmed", "OSINT Defender", "IntelCrab", "Jack Posobiec"],
        "source_icons": ["🔍", "🛰️", "📊", "🗺️", "🕵️"],
    },
    "SOCIAL": {
        "color": "#3399ff",
        "bg_color": "rgba(51, 153, 255, 0.15)",
        "icon": "🔵",
        "sources": ["Twitter/X", "Telegram", "Reddit", "LinkedIn", "Mastodon"],
        "source_icons": ["🐦", "✈️", "🤖", "💼", "🐘"],
    },
    "MILITARY": {
        "color": "#00cc66",
        "bg_color": "rgba(0, 204, 102, 0.15)",
        "icon": "🟢",
        "sources": ["FlightRadar24", "ADS-B Exchange", "NASA SpaceFlight", "C4ISRNET", "Jane's"],
        "source_icons": ["✈️", "📡", "🚀", "🎖️", "⚓"],
    },
    "ECONOMIC": {
        "color": "#ff9933",
        "bg_color": "rgba(255, 153, 51, 0.15)",
        "icon": "🟠",
        "sources": ["Bloomberg", "Reuters Markets", "WSJ", "Financial Times", "CoinDesk"],
        "source_icons": ["💹", "📈", "💵", "🏦", "₿"],
    },
}

# Sample content templates
CONTENT_TEMPLATES = {
    "BREAKING": [
        "Major earthquake magnitude {mag} strikes {location}. Tsunami warning issued for coastal regions.",
        "Explosion reported at {location} industrial facility. Emergency services responding.",
        "{location} declares state of emergency following severe weather event.",
        "Breaking: Major cyberattack detected targeting critical infrastructure in {location}.",
        "Urgent: Evacuation orders issued for {location} due to rapidly spreading wildfire.",
        "{location} authorities report multiple casualties in developing situation.",
        "Alert: Airspace closure over {location} effective immediately.",
    ],
    "OSINT": [
        "Satellite imagery reveals new construction activity at {location} military facility.",
        "Analysis of shipping data shows unusual vessel movements near {location}.",
        "Social media geolocation confirms presence of military equipment in {location}.",
        "Thermal anomaly detected via Sentinel-2 at coordinates near {location}.",
        "Pattern analysis suggests increased activity at {location} supply depot.",
        "Open source flight tracking reveals surveillance missions over {location}.",
        "Historical imagery comparison shows significant changes at {location} facility.",
    ],
    "SOCIAL": [
        "Thread: Unconfirmed reports of unusual activity observed in {location}.",
        "Video circulating shows military convoy movement through {location}.",
        "Local sources reporting sounds of explosions from {location} area.",
        "Eyewitness accounts describe large-scale military exercise near {location}.",
        "Citizen journalists report unusual air traffic patterns over {location}.",
        "Social media chatter indicates heightened alert status in {location}.",
        "Photos emerging from {location} show increased security presence.",
    ],
    "MILITARY": [
        "AWACS aircraft detected on patrol pattern over {location} region.",
        "Stealth aircraft squawk code 7600 near {location} airspace boundary.",
        "Naval strike group repositioning {distance}nm from {location}.",
        "Multiple refueling tankers active in {location} theater.",
        "Hypersonic test flight trajectory passes over {location}.",
        "Carrier strike group conducting exercises in {location} waters.",
        "UAV swarm activity detected near {location} border region.",
    ],
    "ECONOMIC": [
        "{asset} volatility index spikes {percent}% following {location} developments.",
        "Futures markets reacting to supply chain disruption in {location}.",
        "Cryptocurrency markets showing correlation with {location} events.",
        "Commodity prices for {commodity} surge amid {location} uncertainty.",
        "Currency markets: {currency} weakens {percent}% against basket.",
        "Stock futures decline as {location} situation develops.",
        "Energy markets responding to pipeline shutdown near {location}.",
    ],
}

# Locations
LOCATIONS = [
    "Eastern Europe", "Taiwan Strait", "South China Sea", "Black Sea",
    "Middle East", "Korean Peninsula", "Arctic Circle", "Baltic States",
    "Red Sea", "Persian Gulf", "East Mediterranean", "Horn of Africa",
    "Ukraine", "Poland", "Romania", "Turkey", "Israel", "Iran",
    "Japan", "Philippines", "Australia", "India", "Pakistan",
    "North Atlantic", "Pacific Ocean", "Indian Ocean", "Arctic Ocean",
]

# Tags by classification
TAGS = {
    "BREAKING": ["URGENT", "ALERT", "EVACUATION", "DISASTER", "EMERGENCY", "CRISIS"],
    "OSINT": ["SATELLITE", "ANALYSIS", "GEOSPATIAL", "FORENSICS", "VERIFICATION"],
    "SOCIAL": ["CROWDSOURCE", "EYEWITNESS", "VIRAL", "UNCONFIRMED", "LOCAL"],
    "MILITARY": ["AERIAL", "NAVAL", "GROUND", "SPECIAL_OPS", "EXERCISE"],
    "ECONOMIC": ["MARKETS", "COMMODITIES", "CRYPTO", "FOREX", "FUTURES"],
}

# Active situations
ACTIVE_SITUATIONS = [
    {"name": "Ukraine Conflict", "activity": 95, "trend": "rising"},
    {"name": "Taiwan Tensions", "activity": 78, "trend": "stable"},
    {"name": "Red Sea Crisis", "activity": 82, "trend": "rising"},
    {"name": "Arctic Militarization", "activity": 45, "trend": "rising"},
    {"name": "Cyber Operations", "activity": 88, "trend": "stable"},
    {"name": "Supply Chain Disruption", "activity": 67, "trend": "falling"},
    {"name": "Space Launches", "activity": 34, "trend": "stable"},
    {"name": "Economic Indicators", "activity": 72, "trend": "rising"},
]

class SignalGenerator:
    def __init__(self):
        self.signals: List[Signal] = []
        self.last_update = datetime.utcnow()
        
    def generate_signal(self, classification: str = None) -> Signal:
        """Generate a single mock signal"""
        if classification is None:
            classification = random.choice(list(CLASSIFICATIONS.keys()))
        
        config = CLASSIFICATIONS[classification]
        source_idx = random.randint(0, len(config["sources"]) - 1)
        source = config["sources"][source_idx]
        source_icon = config["source_icons"][source_idx]
        
        # Generate content
        template = random.choice(CONTENT_TEMPLATES[classification])
        location = random.choice(LOCATIONS)
        
        content_params = {
            "location": location,
            "mag": round(random.uniform(4.5, 8.5), 1),
            "distance": random.randint(50, 500),
            "percent": round(random.uniform(2.5, 15.5), 1),
            "asset": random.choice(["Crude Oil", "Gold", "Bitcoin", "S&P 500", "Nasdaq"]),
            "commodity": random.choice(["Oil", "Gas", "Grain", "Rare Earths", "Lithium"]),
            "currency": random.choice(["USD", "EUR", "JPY", "GBP", "CNY"]),
        }
        
        content = template.format(**content_params)
        
        # Generate title from content
        title = content.split(".")[0][:80] + "..." if len(content) > 80 else content.split(".")[0]
        
        # Generate tags
        tags = random.sample(TAGS[classification], k=random.randint(1, 3))
        
        # Confidence level
        confidence = random.choice(["LOW", "MEDIUM", "HIGH", "VERY HIGH"])
        
        signal = Signal(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.utcnow(),
            classification=classification,
            source=source,
            source_icon=source_icon,
            title=title,
            content=content,
            location=location,
            confidence=confidence,
            tags=tags,
        )
        
        return signal
    
    def generate_batch(self, count: int = 5) -> List[Signal]:
        """Generate a batch of signals"""
        new_signals = []
        for _ in range(count):
            signal = self.generate_signal()
            new_signals.append(signal)
            self.signals.insert(0, signal)
        
        # Keep only last 100 signals
        self.signals = self.signals[:100]
        self.last_update = datetime.utcnow()
        
        return new_signals
    
    def get_signals(self, limit: int = 50, classification: str = None) -> List[Signal]:
        """Get signals with optional filtering"""
        signals = self.signals
        if classification:
            signals = [s for s in signals if s.classification == classification]
        return signals[:limit]
    
    def get_stats(self) -> dict:
        """Get dashboard statistics"""
        total = len(self.signals)
        if total == 0:
            return {
                "total": 0,
                "per_minute": 0,
                "by_classification": {k: 0 for k in CLASSIFICATIONS.keys()},
                "sources_active": 0,
            }
        
        by_classification = {k: 0 for k in CLASSIFICATIONS.keys()}
        for signal in self.signals:
            by_classification[signal.classification] += 1
        
        # Calculate signals per minute (last 10 signals)
        recent = self.signals[:10]
        if len(recent) >= 2:
            time_span = (recent[0].timestamp - recent[-1].timestamp).total_seconds()
            per_minute = (len(recent) / time_span * 60) if time_span > 0 else 0
        else:
            per_minute = 0
        
        sources_active = len(set(s.source for s in self.signals[:20]))
        
        return {
            "total": total,
            "per_minute": round(per_minute, 1),
            "by_classification": by_classification,
            "sources_active": sources_active,
        }
    
    def get_active_situations(self) -> List[dict]:
        """Get active situations with slight variations"""
        situations = []
        for sit in ACTIVE_SITUATIONS:
            # Add slight variation to activity
            variation = random.randint(-5, 5)
            activity = max(0, min(100, sit["activity"] + variation))
            situations.append({
                "name": sit["name"],
                "activity": activity,
                "trend": sit["trend"],
            })
        return sorted(situations, key=lambda x: x["activity"], reverse=True)

# Global generator instance
generator = SignalGenerator()

def get_generator() -> SignalGenerator:
    """Get the global signal generator instance"""
    return generator
