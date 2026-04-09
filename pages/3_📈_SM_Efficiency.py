"""
CR Pulse — S&M Efficiency Initiative Dashboard
Tracks three levers: MQL Quality, MQL→SQL Conversion, Win Rate
Auto-populates from HubSpot where possible. Manual entry for cost/efficiency.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from database.db import get_db
from pages._sm_cohort_loader import load_weekly_cohorts_from_files

ROOT = Path(__file__).parent.parent

@st.cache_data(ttl=1800, show_spinner=False)
def load_weekly_cohorts(quarter: str, year: int):
    """
    Try JSON files first (local dev), fall back to DB (cloud / after sync).
    Returns {'sal': [...], 'aec': [...], 'file_date': str} or None.
    """
    data = load_weekly_cohorts_from_files(quarter, year, ROOT)
    if data is not None:
        return data
    # Fall back to DB
    return get_db().get_weekly_cohorts(quarter, year)

# ── Config ────────────────────────────────────────────────────────────────────
_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
_default_q = st.session_state.get('current_quarter', 'Q2')
_default_y = st.session_state.get('current_year', 2026)

with st.sidebar:
    st.markdown("**Quarter**")
    QUARTER = st.selectbox("Quarter", _quarters, index=_quarters.index(_default_q),
                           key='sm_quarter', label_visibility='collapsed')
    YEAR = st.number_input("Year", min_value=2024, max_value=2030,
                           value=_default_y, step=1, key='sm_year')

# KPI names for this page (stored in the same KPI table as main dashboard)
SM_KPIS = {
    # Lever 1
    'SM_SAL_Cost_Per_SQL': {'label': 'SAL Cost/SQL', 'target': '$1,300', 'lever': 1, 'source': 'Manual', 'format': 'currency'},
    'SM_AEC_Cost_Per_SQL': {'label': 'AEC Cost/SQL', 'target': '$1,700', 'lever': 1, 'source': 'Manual', 'format': 'currency'},
    'SM_ICP_MQL_Share': {'label': '% MQLs from ICP Verticals', 'target': '90%', 'lever': 1, 'source': 'HubSpot', 'format': 'pct'},
    # Lever 2
    'SM_SAL_MQL_Volume': {'label': 'SAL ICP MQLs',        'target': '180',  'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_AEC_MQL_Volume': {'label': 'AEC ICP MQLs',        'target': '105',  'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_SAL_MQL_SAL':    {'label': 'SAL MQL→SAL %',       'target': '55%',  'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_MQL_SAL':    {'label': 'AEC MQL→SAL %',       'target': '40%',  'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_SAL_SAL_SQL':    {'label': 'SAL SAL→SQL %',       'target': '60%',  'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_SAL_SQL':    {'label': 'AEC SAL→SQL %',       'target': '60%',  'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_SAL_MQL_SQL':    {'label': 'SAL MQL→SQL % (e2e)', 'target': '35%',  'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_MQL_SQL':    {'label': 'AEC MQL→SQL % (e2e)', 'target': '35%',  'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_SAL_SQL_Volume': {'label': 'SAL SQLs (Mkt)',      'target': '67',   'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_AEC_SQL_Volume': {'label': 'AEC SQLs (Mkt)',      'target': '57',   'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_SAL_Pipeline_ARR': {'label': 'SAL Pipeline Created', 'target': '$600,000',   'lever': 2, 'source': 'HubSpot', 'format': 'currency'},
    'SM_AEC_Pipeline_ARR': {'label': 'AEC Pipeline Created', 'target': '$1,600,000', 'lever': 2, 'source': 'HubSpot', 'format': 'currency'},
    # Lever 3
    'SM_SAL_Win_Rate': {'label': 'SAL Win Rate', 'target': '20%', 'lever': 3, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_Win_Rate': {'label': 'AEC Win Rate', 'target': '25%', 'lever': 3, 'source': 'HubSpot', 'format': 'pct'},
    'SM_SAL_Disc_Demo': {'label': 'SAL Discovery→Demo %', 'target': '45%', 'lever': 3, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_Disc_Demo': {'label': 'AEC Discovery→Demo %', 'target': '45%', 'lever': 3, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_Demo_ROI': {'label': 'AEC Demo→ROI %', 'target': '70%', 'lever': 3, 'source': 'HubSpot', 'format': 'pct'},
    'SM_SAL_Touches': {'label': 'SAL Avg Touches/Deal', 'target': '15', 'lever': 3, 'source': 'HubSpot', 'format': 'float'},
    'SM_SAL_Contacts': {'label': 'SAL Avg Contacts/Deal', 'target': '2.0', 'lever': 3, 'source': 'HubSpot', 'format': 'float'},
    'SM_SAL_Vertical_Pct': {'label': 'SAL % in SAL Verticals', 'target': '80%', 'lever': 3, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_Stage1_Count': {'label': 'AEC Deals in Discovery', 'target': '<15', 'lever': 3, 'source': 'HubSpot', 'format': 'int'},
    # Roll-up
    'SM_SAL_Bookings': {'label': 'SAL New Logo Bookings', 'target': '$180,000', 'lever': 0, 'source': 'HubSpot', 'format': 'currency'},
    'SM_AEC_Bookings': {'label': 'AEC New Logo Bookings', 'target': '$292,000', 'lever': 0, 'source': 'HubSpot', 'format': 'currency'},
    'SM_Efficiency': {'label': 'S&M Efficiency', 'target': '0.55x', 'lever': 0, 'source': 'Manual', 'format': 'text'},
}

STATUS_COLORS = {
    'On Track': ('🟢', '#e6f4ea'),
    'At Risk': ('🟡', '#fff8e1'),
    'Behind': ('🔴', '#fde8e8'),
}


def fmt_value(value, format_type):
    if value is None or str(value).strip() in ('', 'nan', 'None'):
        return '—'
    v = str(value).strip()
    if format_type == 'currency':
        try:
            n = float(v.replace('$', '').replace(',', ''))
            return f"${n:,.0f}"
        except:
            return v
    if format_type == 'pct':
        try:
            n = float(v.replace('%', ''))
            return f"{n:.1f}%"
        except:
            return v
    if format_type == 'int':
        try:
            return f"{int(float(v)):,}"
        except:
            return v
    if format_type == 'float':
        try:
            return f"{float(v):.1f}"
        except:
            return v
    return v


def calc_status(actual, target, format_type, inverse=False):
    """Calculate status based on actual vs target."""
    if not actual or not target or str(actual).strip() in ('', '—', 'None'):
        return '', ''
    try:
        a = float(str(actual).replace('$', '').replace(',', '').replace('%', '').replace('x', ''))
        t = float(str(target).replace('$', '').replace(',', '').replace('%', '').replace('x', '').replace('<', '').replace('>', ''))
    except:
        return '', ''

    if target.startswith('<'):
        pct = (t / a) * 100 if a > 0 else 100
    elif inverse:
        pct = (t / a) * 100 if a > 0 else 0
    else:
        pct = (a / t) * 100 if t > 0 else 0

    if pct >= 90:
        return 'On Track', '🟢'
    elif pct >= 70:
        return 'At Risk', '🟡'
    else:
        return 'Behind', '🔴'


# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 S&M Efficiency — Weekly Review")
st.caption(f"{QUARTER} {YEAR} · Target: 0.65x S&M efficiency by end of 2026 · Updated {date.today().strftime('%B %-d, %Y')}")

# Links
st.markdown(
    '<div style="font-size:0.8rem; margin-bottom:16px;">'
    '<a href="https://docs.google.com/document/d/1ji-Z0hPMJiIds-MuWaK_pMwJczu9qD1coLT0EqDPvrE/edit" target="_blank">S&M Efficiency Plan</a>'
    ' &nbsp;|&nbsp; '
    '<a href="https://docs.google.com/document/d/1W1V98mV60higwSsOrZd7fzHqVwg8qlpMerjPQabrMDk/edit" target="_blank">SAL Win Rate</a>'
    ' &nbsp;|&nbsp; '
    '<a href="https://docs.google.com/document/d/1m0DlU-gzvDeW3rq1WYzz2DR4R8Uj5-i118NDckjuo9A/edit" target="_blank">AEC Win Rate</a>'
    ' &nbsp;|&nbsp; '
    '<a href="https://docs.google.com/document/d/1KcxW6ymZK57dk3pQ6HMBSjbsSDe8hkJ5tfRmqFYTN1E/edit" target="_blank">MQL→SQL Analysis</a>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# ── Load KPI data ─────────────────────────────────────────────────────────────
db = get_db()
sm_data = {}
all_kpis = db.get_latest_kpis(QUARTER, YEAR)
if not all_kpis.empty:
    for _, row in all_kpis.iterrows():
        if row['kpi_name'] in SM_KPIS:
            sm_data[row['kpi_name']] = row


def _val(kpi_name):
    """Returns (numeric_or_None, formatted_str) for a KPI."""
    if kpi_name not in SM_KPIS:
        return None, '—'
    d = sm_data.get(kpi_name)
    if d is None:
        return None, '—'
    raw = (d.actual_value if hasattr(d, 'actual_value') else d.get('actual_value', '')) or ''
    raw = str(raw).strip()
    if raw in ('', 'None', 'nan'):
        return None, '—'
    try:
        n = float(raw.replace('%', '').replace('$', '').replace(',', '').replace('x', ''))
        return n, fmt_value(raw, SM_KPIS[kpi_name]['format'])
    except Exception:
        return None, raw


def _sts(n, target_n, higher_is_better=True):
    """Returns (emoji, border_color, bg_color) given numeric actual and target."""
    if n is None or target_n is None or target_n == 0:
        return '', '#cccccc', '#f5f5f5'
    pct = (n / target_n * 100) if higher_is_better else (target_n / n * 100 if n > 0 else 0)
    if pct >= 90:   return '🟢', '#4caf50', '#e8f5e9'
    elif pct >= 70: return '🟡', '#ffc107', '#fff8e1'
    else:           return '🔴', '#f44336', '#fdecea'


# ── Roll-up KPI band ──────────────────────────────────────────────────────────
sal_b_n, sal_b_f = _val('SM_SAL_Bookings')
aec_b_n, aec_b_f = _val('SM_AEC_Bookings')
eff_n,   eff_f   = _val('SM_Efficiency')
tot_b_n  = (sal_b_n or 0) + (aec_b_n or 0)
tot_b_f  = f"${tot_b_n:,.0f}" if (sal_b_n or aec_b_n) else '—'

c1, c2, c3, c4 = st.columns(4)
c1.metric("SAL Bookings",   sal_b_f, "Target: $180K")
c2.metric("AEC Bookings",   aec_b_f, "Target: $292K")
c3.metric("Total Bookings", tot_b_f, "Target: $472K")
c4.metric("S&M Efficiency", eff_f,   "Target: 0.55–0.60x")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Full Funnel Snapshot  (SAL / AEC / Total tabs)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="font-size:1.1rem;font-weight:700;color:#0F7D64;margin-bottom:2px;">Full Funnel Snapshot</div>'
    '<div style="font-size:0.82rem;color:#666;margin-bottom:10px;">'
    'Quarter-to-date actuals vs. targets — ICP MQLs → SALs → SQLs → Won</div>',
    unsafe_allow_html=True,
)

VTGT = {
    'SAL': {'mql': 180, 'mql_sal': 55.0, 'sal_sql': 60.0, 'mql_sql': 35.0,
            'sql': 67, 'win': 20.0, 'bookings': 180000, 'pipeline': 600000, 'cost_sql': 1300},
    'AEC': {'mql': 105, 'mql_sal': 40.0, 'sal_sql': 60.0, 'mql_sql': 35.0,
            'sql': 57, 'win': 25.0, 'bookings': 292000, 'pipeline': 1600000, 'cost_sql': 1700},
}


def _card_html(label, value, target_str, border, bg):
    return (
        f'<div style="border-left:4px solid {border};border-radius:8px;padding:14px 10px;'
        f'background:{bg};text-align:center;min-height:105px;">'
        f'<div style="font-size:0.68rem;font-weight:600;color:#555;text-transform:uppercase;'
        f'letter-spacing:0.5px;margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:2rem;font-weight:700;line-height:1.1;color:#111;">{value}</div>'
        f'<div style="font-size:0.68rem;color:#aaa;margin-top:5px;">Target: {target_str}</div>'
        f'</div>'
    )


def _arrow_html(rate, label, border):
    return (
        f'<div style="text-align:center;padding-top:18px;">'
        f'<div style="font-size:0.63rem;color:#999;margin-bottom:2px;">{label}</div>'
        f'<div style="font-size:1.05rem;font-weight:700;color:{border};">{rate}</div>'
        f'<div style="font-size:1.4rem;color:{border};line-height:1;">→</div>'
        f'</div>'
    )


def render_funnel_tab(v):
    tgt = VTGT[v]
    mql_n,    mql_f    = _val(f'SM_{v}_MQL_Volume')
    mqlsal_n, mqlsal_f = _val(f'SM_{v}_MQL_SAL')
    salsql_n, salsql_f = _val(f'SM_{v}_SAL_SQL')
    sql_n,    sql_f    = _val(f'SM_{v}_SQL_Volume')
    win_n,    win_f    = _val(f'SM_{v}_Win_Rate')
    book_n,   book_f   = _val(f'SM_{v}_Bookings')
    pipe_n,   pipe_f   = _val(f'SM_{v}_Pipeline_ARR')
    cost_n,   cost_f   = _val(f'SM_{v}_Cost_Per_SQL')
    icp_n,    icp_f    = _val('SM_ICP_MQL_Share')
    mqlsql_n, mqlsql_f = _val(f'SM_{v}_MQL_SQL')
    disc_n,   disc_f   = _val(f'SM_{v}_Disc_Demo')

    sal_est = int(round(mql_n * mqlsal_n / 100)) if mql_n and mqlsal_n else None

    _, c_mql,    bg_mql    = _sts(mql_n,    tgt['mql'])
    _, c_mqlsal, bg_mqlsal = _sts(mqlsal_n, tgt['mql_sal'])
    _, c_salsql, bg_salsql = _sts(salsql_n, tgt['sal_sql'])
    _, c_sql,    bg_sql    = _sts(sql_n,    tgt['sql'])
    _, c_win,    bg_win    = _sts(win_n,    tgt['win'])
    _, c_book,   bg_book   = _sts(book_n,   tgt['bookings'])

    ca, cb, cc, cd, ce, cf, cg = st.columns([4, 2, 4, 2, 4, 2, 4])
    ca.markdown(_card_html('ICP MQLs',   mql_f, str(tgt['mql']), c_mql, bg_mql), unsafe_allow_html=True)
    cb.markdown(_arrow_html(mqlsal_f, 'MQL→SAL', c_mqlsal), unsafe_allow_html=True)
    cc.markdown(_card_html('SALs (est.)', str(sal_est) if sal_est else '—',
                            f"{tgt['mql_sal']:.0f}% of MQLs", c_mqlsal, bg_mqlsal), unsafe_allow_html=True)
    cd.markdown(_arrow_html(salsql_f, 'SAL→SQL', c_salsql), unsafe_allow_html=True)
    ce.markdown(_card_html('SQLs (Mkt)', sql_f, str(tgt['sql']), c_sql, bg_sql), unsafe_allow_html=True)
    cf.markdown(_arrow_html(win_f, 'Win Rate', c_win), unsafe_allow_html=True)
    cg.markdown(_card_html('Bookings',   book_f,
                            '$180K' if v == 'SAL' else '$292K', c_book, bg_book), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    s1, s2, s3, s4, s5 = st.columns(5)
    ei = _sts(icp_n,    90)[0]
    ec = _sts(cost_n,   tgt['cost_sql'], higher_is_better=False)[0]
    ep = _sts(pipe_n,   tgt['pipeline'])[0]
    em = _sts(mqlsql_n, tgt['mql_sql'])[0]
    ed = _sts(disc_n,   45)[0]
    s1.metric("% MQLs ICP",    icp_f,    f"{ei} Target: 90%")
    s2.metric("Cost / SQL",    cost_f,   f"{ec} Target: ${tgt['cost_sql']:,}")
    s3.metric("Pipeline",      pipe_f,   f"{ep} Target: ${'600K' if v == 'SAL' else '1.6M'}")
    s4.metric("MQL→SQL (e2e)", mqlsql_f, f"{em} Target: {tgt['mql_sql']:.0f}%")
    s5.metric("Disc→Demo %",   disc_f,   f"{ed} Target: 45%")


def render_total_funnel():
    sal_mql_n,    _ = _val('SM_SAL_MQL_Volume')
    aec_mql_n,    _ = _val('SM_AEC_MQL_Volume')
    sal_mqlsal_n, _ = _val('SM_SAL_MQL_SAL')
    aec_mqlsal_n, _ = _val('SM_AEC_MQL_SAL')
    sal_salsql_n, _ = _val('SM_SAL_SAL_SQL')
    aec_salsql_n, _ = _val('SM_AEC_SAL_SQL')
    sal_sql_n,    _ = _val('SM_SAL_SQL_Volume')
    aec_sql_n,    _ = _val('SM_AEC_SQL_Volume')
    sal_book_n,   _ = _val('SM_SAL_Bookings')
    aec_book_n,   _ = _val('SM_AEC_Bookings')
    sal_pipe_n,   _ = _val('SM_SAL_Pipeline_ARR')
    aec_pipe_n,   _ = _val('SM_AEC_Pipeline_ARR')
    icp_n,    icp_f = _val('SM_ICP_MQL_Share')
    sal_mqlsql_n, _ = _val('SM_SAL_MQL_SQL')
    aec_mqlsql_n, _ = _val('SM_AEC_MQL_SQL')

    tot_mql  = (sal_mql_n  or 0) + (aec_mql_n  or 0)
    sal_sals = round(sal_mql_n * sal_mqlsal_n / 100) if sal_mql_n and sal_mqlsal_n else 0
    aec_sals = round(aec_mql_n * aec_mqlsal_n / 100) if aec_mql_n and aec_mqlsal_n else 0
    tot_sals = sal_sals + aec_sals
    tot_sql  = (sal_sql_n  or 0) + (aec_sql_n  or 0)
    tot_book = (sal_book_n or 0) + (aec_book_n or 0)
    tot_pipe = (sal_pipe_n or 0) + (aec_pipe_n or 0)

    mqlsal_pct = round(tot_sals / tot_mql * 100, 1) if tot_mql > 0 else None
    salsql_pct = round(tot_sql  / tot_sals * 100, 1) if tot_sals > 0 else None
    # Weighted blended MQL→SQL: weighted avg of SAL and AEC
    tot_mqlsql_n = None
    if sal_mql_n and aec_mql_n and (sal_mqlsql_n is not None or aec_mqlsql_n is not None):
        s = ((sal_mqlsql_n or 0) * sal_mql_n + (aec_mqlsql_n or 0) * aec_mql_n) / (sal_mql_n + aec_mql_n)
        tot_mqlsql_n = round(s, 1)

    mql_f    = str(int(tot_mql))  if tot_mql  else '—'
    sal_f    = str(int(tot_sals)) if tot_sals else '—'
    sql_f    = str(int(tot_sql))  if tot_sql  else '—'
    mqlsal_f = f"{mqlsal_pct:.1f}%" if mqlsal_pct is not None else '—'
    salsql_f = f"{salsql_pct:.1f}%" if salsql_pct is not None else '—'
    book_f   = f"${tot_book:,.0f}" if tot_book else '—'
    pipe_f   = f"${tot_pipe:,.0f}" if tot_pipe else '—'
    mqlsql_f = f"{tot_mqlsql_n:.1f}%" if tot_mqlsql_n is not None else '—'

    MQL_SAL_BLENDED = 49.5   # (180×55 + 105×40) / 285
    _, c_mql,    bg_mql    = _sts(tot_mql  if tot_mql  else None, 285)
    _, c_mqlsal, bg_mqlsal = _sts(mqlsal_pct, MQL_SAL_BLENDED)
    _, c_salsql, bg_salsql = _sts(salsql_pct, 60.0)
    _, c_sql,    bg_sql    = _sts(tot_sql   if tot_sql  else None, 124)
    _, c_book,   bg_book   = _sts(tot_book  if tot_book else None, 472000)

    ca, cb, cc, cd, ce, cf, cg = st.columns([4, 2, 4, 2, 4, 2, 4])
    ca.markdown(_card_html('ICP MQLs',   mql_f,  '285',               c_mql,    bg_mql),    unsafe_allow_html=True)
    cb.markdown(_arrow_html(mqlsal_f, 'MQL→SAL', c_mqlsal),                                  unsafe_allow_html=True)
    cc.markdown(_card_html('SALs (est.)', sal_f,  '~50% of MQLs',     c_mqlsal, bg_mqlsal), unsafe_allow_html=True)
    cd.markdown(_arrow_html(salsql_f, 'SAL→SQL', c_salsql),                                  unsafe_allow_html=True)
    ce.markdown(_card_html('SQLs (Mkt)', sql_f,  '124',               c_sql,    bg_sql),    unsafe_allow_html=True)
    cf.markdown(_arrow_html('—',      'Win Rate', '#cccccc'),                                 unsafe_allow_html=True)
    cg.markdown(_card_html('Bookings',   book_f,  '$472K',             c_book,   bg_book),   unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    s1, s2, s3, s4 = st.columns(4)
    ei = _sts(icp_n,        90)[0]
    ep = _sts(tot_pipe if tot_pipe else None, 2200000)[0]
    em = _sts(tot_mqlsql_n, 35.0)[0]
    eb = _sts(tot_book  if tot_book  else None, 472000)[0]
    s1.metric("% MQLs ICP",    icp_f,    f"{ei} Target: 90%")
    s2.metric("MQL→SQL (e2e)", mqlsql_f, f"{em} Target: 35%")
    s3.metric("Pipeline Total", pipe_f,  f"{ep} Target: $2.2M")
    s4.metric("Bookings Total", book_f,  f"{eb} Target: $472K")


f_sal, f_aec, f_total = st.tabs(['🏢 SAL', '🏗️ AEC', '📊 Total'])
with f_sal:   render_funnel_tab('SAL')
with f_aec:   render_funnel_tab('AEC')
with f_total: render_total_funnel()

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Weekly Funnel Review  (SAL / AEC / Total tabs)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="font-size:1.1rem;font-weight:700;color:#0F7D64;margin-bottom:2px;">Weekly Funnel Review</div>'
    '<div style="font-size:0.82rem;color:#666;margin-bottom:10px;">'
    'Week-by-week pipeline health · Cumulative conversion rates vs. targets</div>',
    unsafe_allow_html=True,
)

cohort_data = load_weekly_cohorts(QUARTER, YEAR)

if cohort_data is None:
    st.info(f"No weekly data yet for {QUARTER} {YEAR}. Run `fetch_hubspot_mqls.py` and `fetch_hubspot_deals.py` first.")
else:
    st.caption(f"Source files last updated: {cohort_data['file_date']}")

    MQL_SAL_TGT = {'SAL': 55.0, 'AEC': 40.0}
    SAL_SQL_TGT  = 60.0
    CONV_TGT     = 35.0
    ICP_TGT      = 90.0
    MQL_SAL_BLENDED = 49.5  # (180×55 + 105×40) / 285

    sal_rows = cohort_data.get('sal', [])
    aec_rows = cohort_data.get('aec', [])

    # ── Latest week callout ───────────────────────────────────────────────────
    if sal_rows or aec_rows:
        latest_sal = sal_rows[-1] if sal_rows else None
        latest_aec = aec_rows[-1] if aec_rows else None
        lbl = (latest_sal or latest_aec)['week_label']

        st.markdown(
            f'<div style="background:#f0f4f8;border-radius:8px;padding:10px 16px;margin-bottom:12px;">'
            f'<span style="font-weight:600;font-size:0.9rem;">Latest Week: {lbl}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        lc1, lc2, lc3, lc4, lc5, lc6, lc7, lc8 = st.columns(8)
        if latest_sal:
            lc1.metric("SAL MQLs",     latest_sal['icp_mqls'])
            lc2.metric("SAL SALs",     latest_sal['sal_n'])
            lc3.metric("SAL SQL Mkt",  latest_sal['sql_mkt'])
            lc4.metric("SAL Pipeline", f"${latest_sal['pipeline']:,.0f}" if latest_sal['pipeline'] else '—')
        if latest_aec:
            lc5.metric("AEC MQLs",     latest_aec['icp_mqls'])
            lc6.metric("AEC SALs",     latest_aec['sal_n'])
            lc7.metric("AEC SQL Mkt",  latest_aec['sql_mkt'])
            lc8.metric("AEC Pipeline", f"${latest_aec['pipeline']:,.0f}" if latest_aec['pipeline'] else '—')

    def _flag(val, tgt_v):
        return '🟢' if val >= tgt_v else ('🟡' if val >= tgt_v * 0.75 else '🔴')

    _COL_CFG = {
        'Week':       st.column_config.TextColumn('Week',      width='small'),
        'MQLs':       st.column_config.NumberColumn('MQLs',    width='small'),
        '% ICP':      st.column_config.TextColumn('% ICP',     width='small'),
        'SALs':       st.column_config.NumberColumn('SALs',    width='small'),
        'MQL→SAL':    st.column_config.TextColumn('MQL→SAL',  width='small'),
        'SQL Mkt':    st.column_config.NumberColumn('SQL Mkt', width='small'),
        'SQL Sls':    st.column_config.NumberColumn('SQL Sls', width='small'),
        'SQL CSM':    st.column_config.NumberColumn('SQL CSM', width='small'),
        'SQL Tot':    st.column_config.NumberColumn('SQL Tot', width='small'),
        'SAL→SQL':    st.column_config.TextColumn('SAL→SQL',  width='small'),
        'Pipeline':   st.column_config.TextColumn('Pipeline',  width='small'),
        '∑ MQL→SAL':  st.column_config.TextColumn('∑ MQL→SAL',width='small'),
        '∑ SAL→SQL':  st.column_config.TextColumn('∑ SAL→SQL',width='small'),
        '∑ MQL→SQL':  st.column_config.TextColumn('∑ MQL→SQL',width='small'),
    }

    def _progress_bars(cum_mql_sal, mql_sal_t, cum_sal_sql, cum_mql_sql):
        pb1, pb2, pb3 = st.columns(3)
        with pb1:
            st.markdown(f"**MQL→SAL**: {cum_mql_sal:.0f}% vs {mql_sal_t:.0f}% target")
            st.progress(min(cum_mql_sal / mql_sal_t, 1.0) if mql_sal_t else 0)
        with pb2:
            st.markdown(f"**SAL→SQL**: {cum_sal_sql:.0f}% vs {SAL_SQL_TGT:.0f}% target")
            st.progress(min(cum_sal_sql / SAL_SQL_TGT, 1.0) if SAL_SQL_TGT else 0)
        with pb3:
            st.markdown(f"**MQL→SQL**: {cum_mql_sql:.0f}% vs {CONV_TGT:.0f}% target")
            st.progress(min(cum_mql_sql / CONV_TGT, 1.0) if CONV_TGT else 0)

    def render_weekly_table(rows, vertical, mql_sal_t):
        if not rows:
            st.info(f"No {vertical} data for {QUARTER} {YEAR}.")
            return
        mql_tgt   = VTGT[vertical]['mql']
        sql_tgt   = VTGT[vertical]['sql']
        pipe_tgt  = VTGT[vertical]['pipeline']

        display = []
        for r in rows:
            display.append({
                'Week':     r['week_label'],
                'MQLs':     r['icp_mqls'],
                '% ICP':    f"{_flag(r['icp_pct'], ICP_TGT)} {r['icp_pct']:.0f}%",
                'SALs':     r['sal_n'],
                'MQL→SAL':  f"{_flag(r['mql_sal_pct'], mql_sal_t)} {r['mql_sal_pct']:.0f}%",
                'SQL Mkt':  r['sql_mkt'],
                'SQL Sls':  r['sql_sales'],
                'SQL CSM':  r['sql_csm'],
                'SQL Tot':  r['sql_total'],
                'SAL→SQL':  f"{_flag(r['sal_sql_pct'], SAL_SQL_TGT)} {r['sal_sql_pct']:.0f}%",
                'Pipeline': f"${r['pipeline']:,.0f}" if r['pipeline'] else '—',
                '∑ MQL→SAL': f"{_flag(r['cum_mql_sal'], mql_sal_t)} {r['cum_mql_sal']:.0f}%",
                '∑ SAL→SQL': f"{_flag(r['cum_sal_sql'], SAL_SQL_TGT)} {r['cum_sal_sql']:.0f}%",
                '∑ MQL→SQL': f"{_flag(r['cum_mql_sql'], CONV_TGT)} {r['cum_mql_sql']:.0f}%",
            })

        last   = rows[-1]
        t_icp  = sum(r['icp_mqls']    for r in rows)
        t_sals = sum(r['sal_n']        for r in rows)
        t_smkt = sum(r['sql_mkt']      for r in rows)
        t_ssls = sum(r['sql_sales']    for r in rows)
        t_scsm = sum(r['sql_csm']      for r in rows)
        t_stot = sum(r['sql_total']    for r in rows)
        t_pipe = sum(r['pipeline']     for r in rows)
        t_mqlsal = round(t_sals / t_icp  * 100, 1) if t_icp  else 0
        t_salsql = round(t_smkt / t_sals * 100, 1) if t_sals else 0
        t_mqlsql = round(t_smkt / t_icp  * 100, 1) if t_icp  else 0

        display.append({
            'Week': f'📊 {QUARTER} Total', 'MQLs': t_icp,
            '% ICP': '', 'SALs': t_sals,
            'MQL→SAL': f"{_flag(t_mqlsal, mql_sal_t)} {t_mqlsal:.0f}%",
            'SQL Mkt': t_smkt, 'SQL Sls': t_ssls, 'SQL CSM': t_scsm, 'SQL Tot': t_stot,
            'SAL→SQL': f"{_flag(t_salsql, SAL_SQL_TGT)} {t_salsql:.0f}%",
            'Pipeline': f"${t_pipe:,.0f}",
            '∑ MQL→SAL': f"{_flag(last['cum_mql_sal'], mql_sal_t)} {last['cum_mql_sal']:.0f}%",
            '∑ SAL→SQL': f"{_flag(last['cum_sal_sql'], SAL_SQL_TGT)} {last['cum_sal_sql']:.0f}%",
            '∑ MQL→SQL': f"{_flag(last['cum_mql_sql'], CONV_TGT)} {last['cum_mql_sql']:.0f}%",
        })
        display.append({
            'Week': '🎯 Target', 'MQLs': mql_tgt,
            '% ICP': '90%', 'SALs': None,
            'MQL→SAL': f"{mql_sal_t:.0f}%",
            'SQL Mkt': sql_tgt, 'SQL Sls': None, 'SQL CSM': None, 'SQL Tot': None,
            'SAL→SQL': f"{SAL_SQL_TGT:.0f}%",
            'Pipeline': f"${pipe_tgt:,}",
            '∑ MQL→SAL': f"{mql_sal_t:.0f}%",
            '∑ SAL→SQL': f"{SAL_SQL_TGT:.0f}%",
            '∑ MQL→SQL': f"{CONV_TGT:.0f}%",
        })

        st.dataframe(pd.DataFrame(display), use_container_width=True,
                     hide_index=True, column_config=_COL_CFG)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _progress_bars(last['cum_mql_sal'], mql_sal_t, last['cum_sal_sql'], last['cum_mql_sql'])

    def render_total_weekly(sal_r, aec_r):
        if not sal_r and not aec_r:
            st.info(f"No data for {QUARTER} {YEAR}.")
            return

        # SAL and AEC rows are aligned by week (same all_weeks list in build_rows)
        display = []
        cum_icp = cum_sals = cum_sqls_mkt = 0
        t_icp = t_sals = t_smkt = t_ssls = t_scsm = t_stot = t_pipe = 0.0

        for s, a in zip(sal_r, aec_r):
            # total_mqls is the same for same week in both verticals
            total_mqls = s.get('total_mqls', 0)
            icp_mqls   = s['icp_mqls']  + a['icp_mqls']
            sals       = s['sal_n']      + a['sal_n']
            icp_pct    = round(icp_mqls / total_mqls * 100, 1) if total_mqls > 0 else 0
            mql_sal    = round(sals / icp_mqls * 100, 1)       if icp_mqls > 0 else 0
            sql_mkt    = s['sql_mkt']    + a['sql_mkt']
            sql_sales  = s['sql_sales']  + a['sql_sales']
            sql_csm    = s['sql_csm']    + a['sql_csm']
            sql_total  = s['sql_total']  + a['sql_total']
            sal_sql    = round(sql_mkt / sals * 100, 1)        if sals > 0    else 0
            pipeline   = s['pipeline']   + a['pipeline']

            cum_icp      += icp_mqls
            cum_sals     += sals
            cum_sqls_mkt += sql_mkt
            cum_mql_sal  = round(cum_sals     / cum_icp      * 100, 1) if cum_icp      > 0 else 0
            cum_sal_sql  = round(cum_sqls_mkt / cum_sals     * 100, 1) if cum_sals     > 0 else 0
            cum_mql_sql  = round(cum_sqls_mkt / cum_icp      * 100, 1) if cum_icp      > 0 else 0

            t_icp  += icp_mqls; t_sals += sals; t_smkt += sql_mkt
            t_ssls += sql_sales; t_scsm += sql_csm; t_stot += sql_total; t_pipe += pipeline

            display.append({
                'Week':     s['week_label'],
                'MQLs':     icp_mqls,
                '% ICP':    f"{_flag(icp_pct, ICP_TGT)} {icp_pct:.0f}%",
                'SALs':     sals,
                'MQL→SAL':  f"{_flag(mql_sal, MQL_SAL_BLENDED)} {mql_sal:.0f}%",
                'SQL Mkt':  sql_mkt,
                'SQL Sls':  sql_sales,
                'SQL CSM':  sql_csm,
                'SQL Tot':  sql_total,
                'SAL→SQL':  f"{_flag(sal_sql, SAL_SQL_TGT)} {sal_sql:.0f}%",
                'Pipeline': f"${pipeline:,.0f}" if pipeline else '—',
                '∑ MQL→SAL': f"{_flag(cum_mql_sal, MQL_SAL_BLENDED)} {cum_mql_sal:.0f}%",
                '∑ SAL→SQL': f"{_flag(cum_sal_sql, SAL_SQL_TGT)} {cum_sal_sql:.0f}%",
                '∑ MQL→SQL': f"{_flag(cum_mql_sql, CONV_TGT)} {cum_mql_sql:.0f}%",
            })

        t_icp   = int(t_icp);  t_sals = int(t_sals)
        t_smkt  = int(t_smkt); t_ssls = int(t_ssls)
        t_scsm  = int(t_scsm); t_stot = int(t_stot)
        t_mqlsal = round(t_sals / t_icp  * 100, 1) if t_icp  else 0
        t_salsql = round(t_smkt / t_sals * 100, 1) if t_sals else 0
        t_mqlsql = round(t_smkt / t_icp  * 100, 1) if t_icp  else 0

        display.append({
            'Week': f'📊 {QUARTER} Total', 'MQLs': t_icp,
            '% ICP': '', 'SALs': t_sals,
            'MQL→SAL': f"{_flag(t_mqlsal, MQL_SAL_BLENDED)} {t_mqlsal:.0f}%",
            'SQL Mkt': t_smkt, 'SQL Sls': t_ssls, 'SQL CSM': t_scsm, 'SQL Tot': t_stot,
            'SAL→SQL': f"{_flag(t_salsql, SAL_SQL_TGT)} {t_salsql:.0f}%",
            'Pipeline': f"${t_pipe:,.0f}",
            '∑ MQL→SAL': f"{_flag(cum_mql_sal, MQL_SAL_BLENDED)} {cum_mql_sal:.0f}%",
            '∑ SAL→SQL': f"{_flag(cum_sal_sql, SAL_SQL_TGT)} {cum_sal_sql:.0f}%",
            '∑ MQL→SQL': f"{_flag(cum_mql_sql, CONV_TGT)} {cum_mql_sql:.0f}%",
        })
        display.append({
            'Week': '🎯 Target', 'MQLs': 285,
            '% ICP': '90%', 'SALs': None,
            'MQL→SAL': f"{MQL_SAL_BLENDED:.0f}%",
            'SQL Mkt': 124, 'SQL Sls': None, 'SQL CSM': None, 'SQL Tot': None,
            'SAL→SQL': f"{SAL_SQL_TGT:.0f}%",
            'Pipeline': '$2.2M',
            '∑ MQL→SAL': f"{MQL_SAL_BLENDED:.0f}%",
            '∑ SAL→SQL': f"{SAL_SQL_TGT:.0f}%",
            '∑ MQL→SQL': f"{CONV_TGT:.0f}%",
        })

        st.dataframe(pd.DataFrame(display), use_container_width=True,
                     hide_index=True, column_config=_COL_CFG)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _progress_bars(cum_mql_sal, MQL_SAL_BLENDED, cum_sal_sql, cum_mql_sql)

    w_sal, w_aec, w_total = st.tabs(['🏢 SAL Weekly', '🏗️ AEC Weekly', '📊 Total Weekly'])
    with w_sal:   render_weekly_table(sal_rows, 'SAL', MQL_SAL_TGT['SAL'])
    with w_aec:   render_weekly_table(aec_rows, 'AEC', MQL_SAL_TGT['AEC'])
    with w_total: render_total_weekly(sal_rows, aec_rows)

st.markdown("---")

# ── Manual Entry ──────────────────────────────────────────────────────────────
with st.expander("✏️ Update S&M Metrics (Manual Entry)"):
    st.caption("For metrics not auto-populated from HubSpot (Cost/SQL, S&M Efficiency)")

    col1, col2, col3 = st.columns([2, 1, 1])

    manual_kpis = {k: v for k, v in SM_KPIS.items() if v['source'] == 'Manual'}
    manual_kpis['SM_Efficiency'] = SM_KPIS['SM_Efficiency']

    with col1:
        kpi_options = {v['label']: k for k, v in SM_KPIS.items()}
        selected_label = st.selectbox("Metric", list(kpi_options.keys()))
        selected_kpi = kpi_options[selected_label]
    with col2:
        new_value = st.text_input("Value", placeholder="e.g. $1,250 or 0.58x")
    with col3:
        comments = st.text_input("Comments", placeholder="Optional")

    if st.button("💾 Save", type="primary"):
        if new_value.strip():
            config = SM_KPIS[selected_kpi]
            status, _ = calc_status(new_value, config['target'], config['format'])
            try:
                db.save_kpi({
                    'kpi_name': selected_kpi,
                    'owner': 'S&M Initiative',
                    'cadence': 'Weekly',
                    'quarter': QUARTER,
                    'year': YEAR,
                    'date': date.today(),
                    'target_value': config['target'],
                    'actual_value': new_value.strip(),
                    'status': status,
                    'variance_pct': None,
                    'source': 'Manual',
                    'comments': comments.strip(),
                    'updated_by': 'S&M Dashboard',
                })
                st.toast(f"✅ Saved: {selected_label} = {new_value}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")

# ── Action Items ──────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:1.1rem; font-weight:700; color:#0F7D64; margin-bottom:8px;">'
    'Win Rate Action Items — Q2 Execution</div>',
    unsafe_allow_html=True,
)

actions = [
    {"#": 1, "Action": "Discovery-first mandate", "Segment": "SAL", "Timeline": "Apr W1", "Owner": "Pete", "Status": "Not started"},
    {"#": 2, "Action": "20-touch cadence + sequences", "Segment": "SAL", "Timeline": "Apr W2-3", "Owner": "Pete/AE", "Status": "Not started"},
    {"#": 3, "Action": "Multi-threading (2+ contacts)", "Segment": "SAL", "Timeline": "Apr W4", "Owner": "Pete", "Status": "Not started"},
    {"#": 4, "Action": "Assign dedicated SAL coach", "Segment": "SAL", "Timeline": "Apr W1", "Owner": "Pete", "Status": "Not started"},
    {"#": 5, "Action": "SAL vertical focus 80%+", "Segment": "SAL", "Timeline": "Apr W3", "Owner": "Pete/AE", "Status": "Not started"},
    {"#": 6, "Action": "BDR qualification gate", "Segment": "SAL", "Timeline": "Apr W3", "Owner": "Shannon", "Status": "Not started"},
    {"#": 7, "Action": "Impact quantification in discovery", "Segment": "AEC", "Timeline": "Apr W1", "Owner": "Pete", "Status": "Not started"},
    {"#": 8, "Action": "Planning cycle alignment", "Segment": "AEC", "Timeline": "Apr W1", "Owner": "Pete/AEs", "Status": "Not started"},
    {"#": 9, "Action": "Post-discovery sequence", "Segment": "AEC", "Timeline": "Apr W2", "Owner": "Pete/Bryce", "Status": "Not started"},
    {"#": 10, "Action": "Transfer SE deals to AEs", "Segment": "AEC", "Timeline": "Apr W1", "Owner": "Pete", "Status": "Not started"},
    {"#": 11, "Action": "Model deal cycle (Big-D)", "Segment": "AEC", "Timeline": "Apr W2", "Owner": "Pete", "Status": "Not started"},
]

df_actions = pd.DataFrame(actions)
st.dataframe(df_actions, use_container_width=True, hide_index=True)
