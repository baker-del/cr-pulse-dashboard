"""
CR Pulse — 2026 Annual KPI Tracker
Cumulative progress toward annual targets for 4 HubSpot KPIs.
"""

import yaml
import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
from database.db import get_db

YEAR     = 2026
QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4']

CURRENCY_KPIS = {'New Logo Pipeline Created', 'New Logo ARR', 'Expansion ARR'}

ANNUAL_KPIS = [
    {'name': 'New Logo ARR',              'icon': '💰', 'owner': 'Sales'},
    {'name': 'Expansion ARR',             'icon': '📈', 'owner': 'CS'},
    {'name': 'New Logo Pipeline Created', 'icon': '🏗️', 'owner': 'Marketing'},
    {'name': 'SQL',                       'icon': '🎯', 'owner': 'Sales / Marketing'},
]


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


def fmt_val(v: float, kpi_name: str) -> str:
    if kpi_name in CURRENCY_KPIS:
        return fmt_currency(v)
    return f"{int(v):,}"


def get_quarterly_actuals(db, kpi_name: str) -> dict:
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


def status_color(pct: float) -> str:
    if pct >= 90:  return '#2ecc71'
    if pct >= 70:  return '#f39c12'
    return '#e74c3c'


def status_label(pct: float, year_pct: float) -> tuple[str, str]:
    """Return (label, color) comparing % to target vs % of year elapsed."""
    gap = pct - year_pct
    if pct >= 100:
        return 'Complete', '#2ecc71'
    if gap >= 0:
        return 'On Pace', '#2ecc71'
    if gap >= -10:
        return 'Slightly Behind', '#f39c12'
    return 'Behind Pace', '#e74c3c'


# ── Load data ──────────────────────────────────────────────────────────────────
db      = get_db()
targets = load_annual_targets()

today       = date.today()
year_start  = date(YEAR, 1, 1)
year_end    = date(YEAR, 12, 31)
year_total  = (year_end - year_start).days + 1
year_elapsed = min(max((today - year_start).days + 1, 0), year_total)
year_pct    = year_elapsed / year_total * 100

# Pre-compute all KPI data
kpi_data = []
for kpi in ANNUAL_KPIS:
    name      = kpi['name']
    target    = parse_num(targets.get(name, 0))
    q_actuals = get_quarterly_actuals(db, name)
    ytd       = sum(v for v in q_actuals.values() if v is not None)
    pct       = (ytd / target * 100) if target > 0 else 0
    label, lcolor = status_label(pct, year_pct)
    kpi_data.append({
        **kpi,
        'target':    target,
        'q_actuals': q_actuals,
        'ytd':       ytd,
        'pct':       pct,
        'label':     label,
        'lcolor':    lcolor,
    })


# ── Page header ────────────────────────────────────────────────────────────────
st.title('📅 2026 Annual KPI Tracker')
st.caption('Cumulative HubSpot actuals vs. full-year targets')

# Year progress bar
st.markdown(f"""
<div style="margin:4px 0 28px 0">
  <div style="display:flex;justify-content:space-between;font-size:12px;
              color:#888;margin-bottom:5px;">
    <span>Jan 1</span>
    <span style="font-weight:600;color:#444;">
      {year_pct:.0f}% of year elapsed &nbsp;({today.strftime('%b %-d')})
    </span>
    <span>Dec 31</span>
  </div>
  <div style="background:#e9ecef;border-radius:6px;height:8px;">
    <div style="background:#94a3b8;width:{year_pct:.1f}%;height:8px;border-radius:6px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Section 1: Headline cards (2 per row) ─────────────────────────────────────
st.markdown("#### Year-to-Date Summary")

for i in range(0, len(kpi_data), 2):
    cols = st.columns(2, gap="large")
    for j, col in enumerate(cols):
        if i + j >= len(kpi_data):
            break
        k = kpi_data[i + j]
        bar_pct   = min(k['pct'], 100)
        bar_color = status_color(k['pct'])
        remaining = max(k['target'] - k['ytd'], 0)

        with col:
            st.markdown(f"""
            <div style="border:1px solid #e8e8e8; border-radius:10px; padding:20px 24px;
                        background:#fff; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;
                          margin-bottom:14px;">
                <div>
                  <div style="font-size:0.78rem;font-weight:700;color:#888;
                              text-transform:uppercase;letter-spacing:0.05em;
                              margin-bottom:4px;">{k['icon']} {k['name']}</div>
                  <div style="font-size:2rem;font-weight:800;color:#0F7D64;
                              line-height:1.1;">{fmt_val(k['ytd'], k['name'])}</div>
                  <div style="font-size:0.8rem;color:#999;margin-top:2px;">
                    of {fmt_val(k['target'], k['name'])} target
                  </div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:1.6rem;font-weight:700;color:{bar_color};">
                    {k['pct']:.1f}%
                  </div>
                  <div style="background:{k['lcolor']}22;color:{k['lcolor']};
                              font-size:0.72rem;font-weight:600;padding:2px 8px;
                              border-radius:10px;margin-top:4px;">{k['label']}</div>
                </div>
              </div>
              <div style="background:#f0f2f5;border-radius:6px;height:8px;margin-bottom:10px;">
                <div style="background:{bar_color};width:{bar_pct:.1f}%;height:8px;
                            border-radius:6px;"></div>
              </div>
              <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#999;">
                <span>Owner: {k['owner']}</span>
                <span>{fmt_val(remaining, k['name'])} remaining</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")

st.markdown("---")

# ── Section 2: Quarterly breakdown table ──────────────────────────────────────
st.markdown("#### Quarterly Breakdown")

rows = []
for k in kpi_data:
    row = {'KPI': f"{k['icon']} {k['name']}"}
    running = 0.0
    for q in QUARTERS:
        val = k['q_actuals'].get(q)
        running += val if val is not None else 0.0
        row[q] = fmt_val(val, k['name']) if val is not None else '—'
    row['YTD']    = fmt_val(k['ytd'], k['name'])
    row['Target'] = fmt_val(k['target'], k['name'])
    row['% Done'] = f"{k['pct']:.1f}%"
    rows.append(row)

df = pd.DataFrame(rows)
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        'KPI':    st.column_config.TextColumn('KPI',    width='medium'),
        'Q1':     st.column_config.TextColumn('Q1',     width='small'),
        'Q2':     st.column_config.TextColumn('Q2',     width='small'),
        'Q3':     st.column_config.TextColumn('Q3',     width='small'),
        'Q4':     st.column_config.TextColumn('Q4',     width='small'),
        'YTD':    st.column_config.TextColumn('YTD',    width='small'),
        'Target': st.column_config.TextColumn('Target', width='small'),
        '% Done': st.column_config.TextColumn('% Done', width='small'),
    }
)
