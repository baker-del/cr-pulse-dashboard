"""
CR Pulse — Home page content
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
from database.db import get_db

quarter = st.session_state.get('current_quarter', 'Q1')
year    = st.session_state.get('current_year', 2026)

_logo = Path(__file__).parent / "assets" / "pulse-logo.png"
_c1, _c2 = st.columns([2, 7])
with _c1:
    if _logo.exists():
        st.image(str(_logo), width=160)
with _c2:
    st.title("CR Pulse")
    st.markdown(f"##### {quarter} {year} · Company KPI Dashboard")
st.markdown("---")

db      = get_db()
kpis    = db.get_latest_kpis(quarter, year)
actions = db.get_actions()

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
total_kpis  = 0 if kpis.empty else len(kpis)
on_track    = 0 if kpis.empty or 'status' not in kpis.columns else len(kpis[kpis['status'] == 'On Track'])
at_risk     = 0 if kpis.empty or 'status' not in kpis.columns else len(kpis[kpis['status'] == 'At Risk'])
behind      = 0 if kpis.empty or 'status' not in kpis.columns else len(kpis[kpis['status'] == 'Behind'])
active_acts = len([a for a in actions if a.status not in ('Completed', 'Closed')])

with col1: st.metric("KPIs Tracked", total_kpis)
with col2: st.metric("🟢 On Track",  on_track)
with col3: st.metric("🟡 At Risk",   at_risk)
with col4: st.metric("🔴 Behind",    behind)

st.markdown("---")

# Priority tiles
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    ### 1️⃣ Defend Share
    Net Retention Rate, Logo Retention, GRR, Renewal Risk
    """)

with col2:
    st.markdown("""
    ### 2️⃣ Agentic CX Platform
    Product adoption, Engineering SLAs, Response rates, AI metrics
    """)

with col3:
    st.markdown("""
    ### 3️⃣ Grow AEC & Accounting
    New Logo ARR, Win Rates, Pipeline, SQLs, ACV
    """)

with col4:
    st.markdown("""
    ### ✅ Action Items
    Track and manage actions across all priorities
    """)
    if active_acts > 0:
        st.warning(f"**{active_acts} active actions** need attention")

st.markdown("---")
st.caption(f"CR Pulse · ClearlyRated · {datetime.now().strftime('%b %-d, %Y  %-I:%M %p')}")
