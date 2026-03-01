# Intel Monitor - Glint-Style Intelligence Dashboard

Real-time intelligence monitoring terminal inspired by glint.trade. No trading, just pure information flow.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run intel_monitor.py
```

## Features

- **Dark Terminal UI** - Glint-inspired interface
- **Signal Classification** - BREAKING, OSINT, SOCIAL, MILITARY, ECONOMIC
- **Real-time Feed** - Auto-refreshing signal stream
- **Mock Data Mode** - Run without API keys for demo

## Signal Types

| Badge | Type | Description |
|-------|------|-------------|
| 🔴 BREAKING | Urgent news, disasters, major events |
| 🟡 OSINT | Satellite, analysis, public intel |
| 🔵 SOCIAL | X/Twitter, Telegram, social media |
| 🟢 MILITARY | Aircraft, naval, troop movements |
| 🟠 ECONOMIC | Markets, policy, financial data |

## Architecture

```
intel-monitor/
├── intel_monitor.py      # Main dashboard
├── mock_signals.py       # Demo data generator
├── style.css            # Terminal theme
├── signals/             # Classification engine
│   └── classifier.py
└── feeds/               # Data sources
    ├── sources/
    │   ├── rss_feed.py
    │   └── twitter_monitor.py
    └── config.py
```

## Live Data Sources (Optional)

Configure in `feeds/config.py`:
- RSS feeds (news sites)
- X/Twitter accounts
- Telegram channels
- OSINT feeds

## License

MIT
