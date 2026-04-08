"""
CR Pulse — 2026 Annual KPI Tracker

Tracks cumulative progress toward annual targets for the 4 HubSpot KPIs:
  New Logo Pipeline Created, New Logo ARR, SQL, Expansion ARR

Data: sums quarterly actuals from the kpis table (Q1–Q4 2026).
Targets: loaded from config/targets.yaml > annual > hubspot_kpis.
"""

import yaml
import streamlit as st
import pandas as pd
from pathlib import Path
from database.db import get_db

# ── Config ─────────────────────────────────────────────────────────────────────
YEAR = 2026
QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4']

# Layout: Row 1 = ARR pair, Row 2 = Pipeline + SQL side by side
ANNUAL_KPI_LAYOUT = [
    ['New Logo ARR', 'Expansion ARR'],
    ['New Logo Pipeline Created', 'SQL'],
]
ANNUAL_KPIS = [kpi for row in ANNUAL_KPI_LAYOUT for kpi in row]

CURRENCY_KPIS = {'New Logo Pipeline Created', 'New Logo ARR', 'Expansion ARR'}

KPI_ICONS = {
    'New Logo Pipeline Created': '🏗️',
    'New Logo ARR':              '💰',
    'SQL':                       '🎯',
    'Expansion ARR':             '📈',
}

KPI_OWNERS = {
    'New Logo Pipeline Created': 'Marketing',
    'New Logo ARR':              'Sales',
    'SQL':                       'Sales / Marketing',
    'Expansion ARR':             'CS',
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def load_annual_targets() -> dict:
    path = Path(__file__).parent.parent / 'config' / 'targets.yaml'
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get('annual', {}).get('hubspot_kpis', {})


def parse_num(value) -> float:
    if value is None:
        return 0.0
    s = str(value).strip().replace('$', '').replace(',', '').replace('%', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def fmt_currency(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


def fmt_value(v: float, kpi_name: str) -> str:
    if kpi_name in CURRENCY_KPIS:
        return fmt_currency(v)
    return f"{int(v):,}"


def get_quarterly_actuals(db, kpi_name: str) -> dict:
    """Return {quarter: latest_actual_float} for each quarter in YEAR."""
    result = {}
    for q in QUARTERS:
        df = db.get_latest_kpis(q, YEAR)
        if df.empty:
            result[q] = None
            continue
        row = df[df['kpi_name'] == kpi_name]
        if row.empty:
            result[q] = None
            continue
        val = parse_num(row.iloc[0]['actual_value'])
        result[q] = val if val > 0 else None
    return result


def pace_color(pct: float) -> str:
    if pct >= 90:
        return '#2ecc71'
    if pct >= 70:
        return '#f39c12'
    return '#e74c3c'


# ── Page ───────────────────────────────────────────────────────────────────────
st.set_page_config(page_title='2026 Annual Dashboard', layout='wide')
st.title('📅 2026 Annual KPI Tracker')
st.caption(f'Cumulative HubSpot actuals vs. full-year targets — updated each time HubSpot syncs')

db = get_db()
targets = load_annual_targets()

# ── Year progress bar ─────────────────────────────────────────────────────────
from datetime import date
today = date.today()
year_start = date(YEAR, 1, 1)
year_end   = date(YEAR, 12, 31)
year_total   = (year_end - year_start).days + 1
year_elapsed = min(max((today - year_start).days + 1, 0), year_total)
year_pct     = year_elapsed / year_total * 100

st.markdown(f"""
<div style="margin-bottom:24px">
  <div style="display:flex;justify-content:space-between;font-size:13px;color:#888;margin-bottom:4px">
    <span>Jan 1</span>
    <span style="font-weight:600;color:#333">Year {year_pct:.0f}% elapsed ({year_elapsed}/{year_total} days)</span>
    <span>Dec 31</span>
  </div>
  <div style="background:#e9ecef;border-radius:6px;height:10px">
    <div style="background:#6c757d;width:{year_pct:.1f}%;height:10px;border-radius:6px"></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
def kpi_card(col, kpi_name: str):
    target_raw = targets.get(kpi_name, '')
    target_val = parse_num(target_raw)
    q_actuals  = get_quarterly_actuals(db, kpi_name)
    ytd        = sum(v for v in q_actuals.values() if v is not None)
    pct        = (ytd / target_val * 100) if target_val > 0 else 0
    bar_color  = pace_color(pct)
    bar_pct    = min(pct, 100)

    with col:
        st.markdown(f"#### {KPI_ICONS[kpi_name]} {kpi_name}")
        st.caption(f"Owner: {KPI_OWNERS[kpi_name]}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("YTD Actual",    fmt_value(ytd, kpi_name))
        m2.metric("Annual Target", fmt_value(target_val, kpi_name))
        m3.metric("% to Target",   f"{pct:.1f}%")
        m4.metric("Remaining",     fmt_value(max(target_val - ytd, 0), kpi_name))

        st.markdown(f"""
        <div style="margin:4px 0 10px 0">
          <div style="background:#e9ecef;border-radius:6px;height:10px">
            <div style="background:{bar_color};width:{bar_pct:.1f}%;height:10px;border-radius:6px"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        rows, running = [], 0.0
        for q in QUARTERS:
            val = q_actuals.get(q)
            running += val if val is not None else 0.0
            rows.append({
                'Quarter':       q,
                'Actual':        fmt_value(val, kpi_name) if val is not None else '—',
                'Running Total': fmt_value(running, kpi_name),
                '% of Annual':   f"{running/target_val*100:.1f}%" if target_val > 0 else '—',
                'Status':        '✅' if val is not None else '⏳',
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                'Quarter':       st.column_config.TextColumn('Quarter', width=70),
                'Actual':        st.column_config.TextColumn('Actual',  width=120),
                'Running Total': st.column_config.TextColumn('Running', width=120),
                '% of Annual':   st.column_config.TextColumn('% Annual', width=90),
                'Status':        st.column_config.TextColumn('',        width=40),
            }
        )


for row_kpis in ANNUAL_KPI_LAYOUT:
    cols = st.columns(len(row_kpis), gap="large")
    for col, kpi_name in zip(cols, row_kpis):
        kpi_card(col, kpi_name)
    st.divider()
