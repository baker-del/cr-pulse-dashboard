"""
CR Pulse — S&M Efficiency Initiative Dashboard
Tracks three levers: MQL Quality, MQL→SQL Conversion, Win Rate
Auto-populates from HubSpot where possible. Manual entry for cost/efficiency.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.db import get_db

# ── Config ────────────────────────────────────────────────────────────────────
QUARTER = st.session_state.get('current_quarter', 'Q2')
YEAR = st.session_state.get('current_year', 2026)

# KPI names for this page (stored in the same KPI table as main dashboard)
SM_KPIS = {
    # Lever 1
    'SM_SAL_Cost_Per_SQL': {'label': 'SAL Cost/SQL', 'target': '$1,300', 'lever': 1, 'source': 'Manual', 'format': 'currency'},
    'SM_AEC_Cost_Per_SQL': {'label': 'AEC Cost/SQL', 'target': '$1,700', 'lever': 1, 'source': 'Manual', 'format': 'currency'},
    'SM_ICP_MQL_Share': {'label': '% MQLs from ICP Verticals', 'target': '90%', 'lever': 1, 'source': 'HubSpot', 'format': 'pct'},
    # Lever 2
    'SM_SAL_MQL_SQL': {'label': 'SAL MQL→SQL %', 'target': '25%', 'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_AEC_MQL_SQL': {'label': 'AEC MQL→SQL %', 'target': '20%', 'lever': 2, 'source': 'HubSpot', 'format': 'pct'},
    'SM_SAL_MQL_Volume': {'label': 'SAL ICP MQLs', 'target': '180', 'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_AEC_MQL_Volume': {'label': 'AEC ICP MQLs', 'target': '105', 'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_SAL_SQL_Volume': {'label': 'SAL SQLs Created', 'target': '45', 'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_AEC_SQL_Volume': {'label': 'AEC SQLs Created', 'target': '21', 'lever': 2, 'source': 'HubSpot', 'format': 'int'},
    'SM_SAL_Pipeline_ARR': {'label': 'SAL Pipeline ARR', 'target': '$518,000', 'lever': 2, 'source': 'HubSpot', 'format': 'currency'},
    'SM_AEC_Pipeline_ARR': {'label': 'AEC Pipeline ARR', 'target': '$567,000', 'lever': 2, 'source': 'HubSpot', 'format': 'currency'},
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
st.title("📈 S&M Efficiency")
st.caption(f"{QUARTER} {YEAR} | Target: 0.65x by end of 2026 | Updated: {date.today().strftime('%B %-d, %Y')}")

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

# ── Load data ─────────────────────────────────────────────────────────────────
db = get_db()

# Load any existing S&M KPI data
sm_data = {}
all_kpis = db.get_latest_kpis(QUARTER, YEAR)
if not all_kpis.empty:
    for _, row in all_kpis.iterrows():
        if row['kpi_name'] in SM_KPIS:
            sm_data[row['kpi_name']] = row


# ── Summary metrics ───────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

sal_bookings = sm_data.get('SM_SAL_Bookings', {})
aec_bookings = sm_data.get('SM_AEC_Bookings', {})
efficiency = sm_data.get('SM_Efficiency', {})

sal_b_val = sal_bookings.get('actual_value', '') if isinstance(sal_bookings, dict) else (sal_bookings.actual_value if hasattr(sal_bookings, 'actual_value') else '')
aec_b_val = aec_bookings.get('actual_value', '') if isinstance(aec_bookings, dict) else (aec_bookings.actual_value if hasattr(aec_bookings, 'actual_value') else '')
eff_val = efficiency.get('actual_value', '') if isinstance(efficiency, dict) else (efficiency.actual_value if hasattr(efficiency, 'actual_value') else '')

c1.metric("SAL Bookings", fmt_value(sal_b_val, 'currency') if sal_b_val else '—', f"Target: $180K")
c2.metric("AEC Bookings", fmt_value(aec_b_val, 'currency') if aec_b_val else '—', f"Target: $292K")
c3.metric("Total Bookings", '—', f"Target: $472K")
c4.metric("S&M Efficiency", eff_val if eff_val else '—', f"Target: 0.55-0.60x")

st.markdown("---")

# ── Lever sections ────────────────────────────────────────────────────────────
def render_lever(lever_num, title, description):
    st.markdown(
        f'<div style="font-size:1.1rem; font-weight:700; color:#0F7D64; margin-bottom:4px;">'
        f'Lever {lever_num} — {title}</div>'
        f'<div style="font-size:0.82rem; color:#666; margin-bottom:12px;">{description}</div>',
        unsafe_allow_html=True,
    )

    lever_kpis = {k: v for k, v in SM_KPIS.items() if v['lever'] == lever_num}

    rows = []
    for kpi_name, config in lever_kpis.items():
        data = sm_data.get(kpi_name)
        if data is not None:
            if hasattr(data, 'actual_value'):
                actual = data.actual_value or ''
            else:
                actual = data.get('actual_value', '')
        else:
            actual = ''

        target = config['target']
        fmt_type = config['format']
        source = config['source']

        status, emoji = calc_status(actual, target, fmt_type,
                                     inverse=(fmt_type == 'currency' and 'Cost' in config['label']))

        rows.append({
            'KPI': config['label'],
            'Target': target,
            'Actual': fmt_value(actual, fmt_type) if actual else '—',
            'Status': f"{emoji} {status}" if status else '',
            'Source': source,
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         'KPI': st.column_config.TextColumn('KPI', width='medium'),
                         'Target': st.column_config.TextColumn('Target', width='small'),
                         'Actual': st.column_config.TextColumn('Actual', width='small'),
                         'Status': st.column_config.TextColumn('Status', width='small'),
                         'Source': st.column_config.TextColumn('Source', width='small'),
                     })


render_lever(1, "MQL Quality & Cost",
    "Owner: Stephen/Freddy | Target: ≤$1,300/SQL SAL, ≤$1,700 AEC, 90% ICP")

render_lever(2, "MQL → SQL Conversion",
    "Owner: Marketing + Sales | Target: 25% SAL, 20% AEC")

render_lever(3, "Win Rate",
    "Owner: Pete | Target: 20% SAL, 25% AEC | Action plans in execution")

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
