"""
Intel Monitor Dashboard
Glint-Style Real-Time Intelligence Terminal
"""

import streamlit as st
import os
import sys
import random
from datetime import datetime, timedelta

# Add dashboard directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mock_signals import get_generator, CLASSIFICATIONS

# Page configuration
st.set_page_config(
    page_title="Intel Monitor | Signal Intelligence",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load CSS
css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.selected_signal = None
    st.session_state.filter_classification = None
    st.session_state.last_refresh = datetime.utcnow()
    # Generate initial batch of signals
    generator = get_generator()
    generator.generate_batch(15)

# Get generator instance
generator = get_generator()

# Auto-refresh logic
auto_refresh = st.sidebar.checkbox("Auto-refresh (10s)", value=True)
if auto_refresh:
    # Add new signals periodically
    time_since_refresh = (datetime.utcnow() - st.session_state.last_refresh).total_seconds()
    if time_since_refresh > 10:
        generator.generate_batch(random.randint(1, 3))
        st.session_state.last_refresh = datetime.utcnow()
        st.rerun()

# Manual refresh button
if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    generator.generate_batch(random.randint(1, 3))
    st.session_state.last_refresh = datetime.utcnow()
    st.rerun()

# Header
st.markdown("""
<div class="header-container">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div class="header-title">Intel Monitor</div>
            <div style="margin-top: 0.25rem;">
                <span class="status-indicator">
                    <span class="status-dot"></span>
                    <span>LIVE FEED ACTIVE</span>
                </span>
            </div>
        </div>
        <div style="text-align: right;">
            <div class="timestamp" id="live-clock">{} UTC</div>
            <div style="font-size: 0.7rem; color: #606070; margin-top: 0.2rem;">
                Last update: {}
            </div>
        </div>
    </div>
</div>
""".format(
    datetime.utcnow().strftime("%H:%M:%S"),
    generator.last_update.strftime("%H:%M:%S")
), unsafe_allow_html=True)

# Sidebar - Active Situations
st.sidebar.markdown('<div class="sidebar-title">📊 Active Situations</div>', unsafe_allow_html=True)

situations = generator.get_active_situations()
for sit in situations:
    activity_class = "high" if sit["activity"] > 75 else "medium" if sit["activity"] > 40 else "low"
    trend_icon = "↗" if sit["trend"] == "rising" else "→" if sit["trend"] == "stable" else "↘"
    trend_class = f"trend-{sit['trend']}"
    
    st.sidebar.markdown(f"""
    <div class="situation-item">
        <span class="situation-name">{sit['name']}</span>
        <div class="situation-activity">
            <div class="activity-bar">
                <div class="activity-fill {activity_class}" style="width: {sit['activity']}%"></div>
            </div>
            <span class="activity-value">{sit['activity']}%</span>
            <span class="trend-indicator {trend_class}">{trend_icon}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Sidebar - Filters
st.sidebar.markdown('<div class="sidebar-title" style="margin-top: 1.5rem;">🔍 Filters</div>', unsafe_allow_html=True)

filter_options = ["ALL"] + list(CLASSIFICATIONS.keys())
selected_filter = st.sidebar.radio(
    "Classification",
    filter_options,
    index=0,
    label_visibility="collapsed"
)

st.session_state.filter_classification = None if selected_filter == "ALL" else selected_filter

# Classification legend
st.sidebar.markdown('<div class="sidebar-title" style="margin-top: 1.5rem;">📋 Legend</div>', unsafe_allow_html=True)

for cls, config in CLASSIFICATIONS.items():
    st.sidebar.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
        <span style="font-size: 1rem;">{config['icon']}</span>
        <span class="classification-badge badge-{cls.lower()}">{cls}</span>
    </div>
    """, unsafe_allow_html=True)

# Main content area - Signal Feed
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
    <div style="font-size: 0.8rem; color: #9090a0;">
        📡 Signal Feed <span class="terminal-cursor"></span>
    </div>
    <div style="font-size: 0.7rem; color: #606070;">
        Showing latest intelligence signals
    </div>
</div>
""", unsafe_allow_html=True)

# Get signals with filtering
signals = generator.get_signals(
    limit=30,
    classification=st.session_state.filter_classification
)

# Display signals
if signals:
    for i, signal in enumerate(signals):
        cls_lower = signal.classification.lower()
        config = CLASSIFICATIONS[signal.classification]
        
        # Format timestamp
        time_str = signal.timestamp.strftime("%H:%M:%S")
        
        # Confidence class
        conf_lower = signal.confidence.lower().replace(" ", "-")
        
        # Tags HTML
        tags_html = "".join([f'<span class="signal-tag">{tag}</span>' for tag in signal.tags])
        
        # Create signal card
        signal_html = f"""
        <div class="signal-card {cls_lower}">
            <div class="signal-header">
                <span class="signal-timestamp">{time_str}</span>
                <span class="classification-badge badge-{cls_lower}">
                    {config['icon']} {signal.classification}
                </span>
                <span class="signal-source">
                    {signal.source_icon} {signal.source}
                </span>
                <span class="confidence-indicator confidence-{conf_lower}">
                    {signal.confidence}
                </span>
            </div>
            <div class="signal-title">{signal.title}</div>
            <div class="signal-content">{signal.content}</div>
            <div class="signal-tags">{tags_html}</div>
        </div>
        """
        
        st.markdown(signal_html, unsafe_allow_html=True)
        
        # Add expander for full details (every 5th signal to reduce clutter)
        if i % 5 == 0:
            with st.expander(f"🔍 View Details - {signal.id}"):
                st.markdown(f"""
                **Signal ID:** `{signal.id}`  
                **Timestamp:** {signal.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}  
                **Classification:** {signal.classification}  
                **Source:** {signal.source}  
                **Location:** {signal.location or 'N/A'}  
                **Confidence:** {signal.confidence}  
                **Tags:** {', '.join(signal.tags)}
                
                ---
                **Full Content:**
                {signal.content}
                """)
else:
    st.info("No signals available. Click 'Refresh Now' to generate signals.")

# Stats bar at bottom
stats = generator.get_stats()

st.markdown(f"""
<div class="stats-container">
    <div class="stat-item">
        <span class="stat-label">Signals</span>
        <span class="stat-value">{stats['total']}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Signals/min</span>
        <span class="stat-value">{stats['per_minute']:.1f}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Active Sources</span>
        <span class="stat-value">{stats['sources_active']}</span>
    </div>
    <div class="stat-breakdown">
        <span class="stat-badge" style="color: #ff3333;">
            🔴 {stats['by_classification']['BREAKING']}
        </span>
        <span class="stat-badge" style="color: #ffcc00;">
            🟡 {stats['by_classification']['OSINT']}
        </span>
        <span class="stat-badge" style="color: #3399ff;">
            🔵 {stats['by_classification']['SOCIAL']}
        </span>
        <span class="stat-badge" style="color: #00cc66;">
            🟢 {stats['by_classification']['MILITARY']}
        </span>
        <span class="stat-badge" style="color: #ff9933;">
            🟠 {stats['by_classification']['ECONOMIC']}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; padding: 1rem; margin-top: 1rem; border-top: 1px solid #2a2a3a;">
    <span style="font-size: 0.7rem; color: #606070;">
        Intel Monitor v1.0 | Glint-Style Intelligence Terminal | 
        <span style="color: #00cc66;">●</span> System Operational
    </span>
</div>
""", unsafe_allow_html=True)
