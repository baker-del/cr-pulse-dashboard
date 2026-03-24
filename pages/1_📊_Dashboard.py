"""
CR Pulse — KPI Dashboard
Grouped by strategic priority with inline editing
"""

import re
import streamlit as st
import pandas as pd
from datetime import date
from database.db import get_db
from utils.kpi_calculator import calculate_variance, is_inverse_kpi, calculate_pace_status


# ── Priority groups ─────────────────────────────────────────────────────────────
PRIORITY_GROUPS = {
    "p1": {
        "label": "1️⃣ Defend Share / Retention",
        "kpis": [
            'NRR',
            'GRR',
            'Logo Retention',
            'Renewal ARR risk (Next 180 days)',
            'Renewal Logo Risk (Next 180 days)',
            'High Risk Accounts (Next 6 Months)',
            'High Risk Account ARR (Next 6 Months)',
        ],
    },
    "p2": {
        "label": "2️⃣ One Agentic CX Platform",
        "kpis": [
            'Total Surveys Sent',
            'CRS - Monthly Active Users',
            'CFT - Monthly Active Users',
            'Core Product Adoption (Workflow Penetration)',
            '30-day Response Rate (Overall)',
            '30-day Response Rate excluding Express',
            'Tickets Resolved in Tier 1 within SLA',
            'Tickets out of SLA',
            'Tickets Created (Week)',
            'Data OPS Tickets missing deadline',
            'Incidents',
            'AI Coded %',
            'Emails & SMS Sent',
            'MS Placement in Box',
            'Survey Click Rate (30-day)',
            'Account Risk - Product Issues',
            'Account Risk - Support Issues',
            'Account Risk - Response Rate Issues',
            'Account Risk - Low Surveys Sent',
            'ARR at Risk - All Product Issues',
        ],
    },
    "p3": {
        "label": "3️⃣ Grow in AEC & Accounting",
        "kpis": [
            'Total New ARR Forecast',
            'New Logo ARR',
            'Expansion ARR',
            'New Logo Pipeline Created',
            'SAL New Created',
            'AEC New Created',
            'Current Qtr Qualified Pipeline',
            'SAL Pipeline',
            'AEC Pipeline',
            'Expansion Pipeline (Next 180 Days)',
            'SQL',
            'Cost/Inbound SQL',
            'Win Rate (Overall)',
            'Win Rate (SAL)',
            'Win Rate (AEC)',
            'ACV (Overall)',
            'ACV (SAL)',
            'ACV (AEC)',
        ],
    },
    "other": {
        "label": "4️⃣ Other",
        "kpis": [
            'Employee NPS',
            'Cash EBITDA (Plan vs. Variance)',
        ],
    },
}

# KPIs not shown in the dashboard (granular sub-metrics)
EXCLUDED_KPIS = [
    'SQL - Inbound',
    'SQL - Outbound',
    'New Logo Win Rate - CFT/Project Based',
    'New Logo Win Rate - CR/NPS Based',
]

CURRENCY_KPI_KEYWORDS = ['arr', 'pipeline', 'coverage', 'cost/inbound', 'acv', 'ebitda', 'new created']

# KPIs where status should be judged on pace-to-date, not simple % of final target
# NOTE: Forecast KPIs (Total New ARR Forecast) are EXCLUDED because the forecast
# already projects full-quarter outcome — comparing against pace would double-count.
# Only true accumulation KPIs (ARR to-date, pipeline created, SQLs) use pace logic.
PACE_KPIS = {
    'New Logo ARR',
    'Expansion ARR',
    'New Logo Pipeline Created',
    'SQL',
}

STATUS_OPTIONS = ['🟢 On Track', '🟡 At Risk', '🔴 Behind']
STATUS_EMOJI   = {'On Track': '🟢', 'At Risk': '🟡', 'Behind': '🔴'}

# Display name overrides (internal name → label shown in table)
DISPLAY_NAME_MAP = {
    'New Logo Pipeline Created': 'New Logo Pipeline Created (Forecast)',
    'SAL New Created':           'SAL New Actual',
    'AEC New Created':           'AEC New Actual',
    'New Logo ARR':              'New Logo ARR To-Date',
    'Expansion ARR':             'Expansion ARR To-Date',
}

# KPIs where we extract the forecast from comments and show it as Actual
FORECAST_KPIS = {'New Logo Pipeline Created'}


def extract_forecast(comments: str):
    """Return a numeric string for the forecast embedded in comments.

    Recognises patterns like 'Forecast ~$1.26M', 'Forecast $856k', etc.
    Returns a plain numeric string (e.g. '1260000') or None.
    """
    if not comments:
        return None
    m = re.search(r'[Ff]orecast\s*~?\$?([\d,.]+)\s*([MmKkBb]?)', str(comments))
    if not m:
        return None
    num_str, suffix = m.group(1), m.group(2).upper()
    try:
        num = float(num_str.replace(',', ''))
        if suffix == 'M':
            num *= 1_000_000
        elif suffix == 'K':
            num *= 1_000
        return str(num)
    except ValueError:
        return None


# Sub-KPIs are visually indented under their parent row
SUB_KPIS = {
    'New Logo ARR',
    'Expansion ARR',
    'SAL New Created',
    'AEC New Created',
    'SAL Pipeline',
    'AEC Pipeline',
    'Win Rate (SAL)',
    'Win Rate (AEC)',
    'ACV (SAL)',
    'ACV (AEC)',
}


def quarter_progress(quarter: str, year: int):
    """Return (elapsed_days, total_days, days_remaining, pct_elapsed) for a quarter."""
    q_starts = {'Q1': (1,1), 'Q2': (4,1), 'Q3': (7,1), 'Q4': (10,1)}
    q_ends   = {'Q1': (3,31), 'Q2': (6,30), 'Q3': (9,30), 'Q4': (12,31)}
    mo_s, d_s = q_starts[quarter]
    mo_e, d_e = q_ends[quarter]
    q_start = date(year, mo_s, d_s)
    q_end   = date(year, mo_e, d_e)
    today   = date.today()
    total   = (q_end - q_start).days + 1
    elapsed = min(max((today - q_start).days + 1, 0), total)
    return elapsed, total, total - elapsed, elapsed / total


# ── Formatting helpers ─────────────────────────────────────────────────────────
def is_currency_kpi(kpi_name: str) -> bool:
    return any(k in kpi_name.lower() for k in CURRENCY_KPI_KEYWORDS)


def fmt(value, kpi_name: str) -> str:
    if value is None or str(value).strip() in ('', 'nan', 'None'):
        return ''
    value_str = str(value).strip()
    if '$' in value_str:
        try:
            return f"${float(value_str.replace('$','').replace(',','')):,.0f}"
        except Exception:
            return value_str
    if '%' in value_str:
        try:
            return f"{float(value_str.replace('%','')):.1f}%"
        except Exception:
            return value_str
    try:
        num = float(value_str.replace(',', ''))
    except (ValueError, TypeError):
        return value_str
    # Account Risk KPIs are plain counts (not percentages), even if name has 'rate'
    if kpi_name.lower().startswith('account risk'):
        return f"{int(num):,}" if num == int(num) else f"{num:,.2f}"
    pct_keywords = ['rate', 'retention', 'nrr', 'grr', 'response',
                    'renewal arr risk', 'renewal logo risk', 'renewal risk',
                    'adoption', 'sla', 'missing deadline', 'click', 'coded']
    if any(k in kpi_name.lower() for k in pct_keywords):
        return f"{num:.1f}%"
    if is_currency_kpi(kpi_name):
        # Handle negative currency (e.g., -$418,000 → "-$418,000")
        if num < 0:
            return f"-${abs(num):,.0f}"
        return f"${num:,.0f}"
    return f"{int(num):,}" if num == int(num) else f"{num:,.2f}"


def fmt_date(value) -> str:
    if value is None:
        return ''
    try:
        d = date.fromisoformat(str(value)) if isinstance(value, str) else value
        return d.strftime('%-m/%-d')
    except Exception:
        return str(value)


def clean_actual(raw: str) -> str:
    return str(raw).strip() if raw and str(raw).strip() not in ('', '—') else ''


# ── Header ─────────────────────────────────────────────────────────────────────
quarter = st.session_state.get('current_quarter', 'Q1')
year    = st.session_state.get('current_year', 2026)

col_title, col_add, col_btn = st.columns([5, 1, 1])
with col_title:
    st.title(f"📊 KPI Dashboard — {quarter} {year}")
with col_add:
    st.write("")
    if st.button("＋ Add KPI", use_container_width=True):
        st.session_state['show_add_kpi'] = not st.session_state.get('show_add_kpi', False)
with col_btn:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.markdown("---")

# ── Inline Add KPI form ─────────────────────────────────────────────────────────
if st.session_state.get('show_add_kpi', False):
    st.subheader("Add / Update KPI Value")
    _priority_labels = [g['label'] for g in PRIORITY_GROUPS.values()]
    _priority_keys   = list(PRIORITY_GROUPS.keys())

    ac1, ac2, ac3 = st.columns([2, 2, 3])
    with ac1:
        _sel_priority = st.selectbox("Priority Group", _priority_labels, key='_add_priority')
        _sel_key = _priority_keys[_priority_labels.index(_sel_priority)]
        _kpi_choices = PRIORITY_GROUPS[_sel_key]['kpis']
    with ac2:
        _sel_kpi = st.selectbox("KPI", _kpi_choices, key='_add_kpi_name')
    with ac3:
        _add_actual   = st.text_input("Actual Value", placeholder="e.g. 88.5% or $50,000", key='_add_actual')
        _add_comments = st.text_input("Comments (optional)", "", key='_add_comments')

    _bs, _bc, _ = st.columns([1, 1, 5])
    with _bs:
        if st.button("💾 Save", type="primary", key="_add_kpi_save"):
            if _add_actual.strip():
                _orig = kpis_df[kpis_df['kpi_name'] == _sel_kpi].to_dict('records') if not kpis_df.empty else []
                _orig = _orig[0] if _orig else {}
                _tgt  = str(_orig.get('target_value', '') or '')
                _vp, _st, _ = calculate_variance(
                    _add_actual, _tgt,
                    is_inverse=is_inverse_kpi(_sel_kpi)
                )
                try:
                    db.save_kpi({
                        'kpi_name':     _sel_kpi,
                        'owner':        str(_orig.get('owner', '') or ''),
                        'cadence':      str(_orig.get('cadence', '') or ''),
                        'quarter':      quarter, 'year': year,
                        'date':         date.today(),
                        'target_value': _tgt,
                        'actual_value': clean_actual(_add_actual),
                        'status':       _st or '',
                        'variance_pct': _vp,
                        'source':       'Manual',
                        'comments':     _add_comments.strip(),
                        'updated_by':   'Dashboard Add',
                    })
                    st.session_state['show_add_kpi'] = False
                    st.toast(f"✅ Saved: {_sel_kpi} = {_add_actual}", icon="✅")
                    st.rerun()
                except Exception as _e:
                    st.error(f"Error saving: {_e}")
            else:
                st.error("Please enter an actual value.")
    with _bc:
        if st.button("Cancel", key="_add_kpi_cancel"):
            st.session_state['show_add_kpi'] = False
            st.rerun()
    st.markdown("---")

# ── Load + compute ─────────────────────────────────────────────────────────────
db = get_db()
kpis_df = db.get_latest_kpis(quarter, year)

# Load most-recent data across all periods for fallback display
fallback_df = db.get_latest_kpis_all_periods()

if kpis_df.empty and fallback_df.empty:
    st.warning(
        f"No KPI data found for {quarter} {year}.\n\n"
        "Go to **Settings** to load targets or sync HubSpot."
    )
    st.stop()
elif kpis_df.empty:
    st.info(f"No {quarter} {year} data synced yet — showing most recent available values below.")

if not kpis_df.empty:
    kpis_df = kpis_df[~kpis_df['kpi_name'].isin(EXCLUDED_KPIS)].copy()

# Remove from fallback any KPIs already present in the current-quarter data
if not kpis_df.empty and not fallback_df.empty:
    current_names = set(kpis_df['kpi_name'].tolist())
    fallback_df = fallback_df[~fallback_df['kpi_name'].isin(current_names)].copy()
if not fallback_df.empty:
    fallback_df = fallback_df[~fallback_df['kpi_name'].isin(EXCLUDED_KPIS)].copy()


elapsed_days, total_days, days_left, pct_elapsed = quarter_progress(quarter, year)


def calc_variance_row(row):
    name = row['kpi_name']
    target = row['target_value']
    # If no target defined, show empty % to Goal and no status
    if target is None or str(target).strip() in ('', 'nan', 'None'):
        return pd.Series({'variance_pct': None, 'status': '', 'emoji': ''})

    # % to Goal is always simple actual / target (not pace-adjusted)
    simple_pct, base_status, base_emoji = calculate_variance(
        row['actual_value'], row['target_value'],
        is_inverse=is_inverse_kpi(name)
    )

    # For accumulation KPIs, override status using pace-to-date logic:
    # are we on track to hit the full-quarter target given elapsed time?
    if name in PACE_KPIS:
        _, status, emoji = calculate_pace_status(
            row['actual_value'], row['target_value'], pct_elapsed
        )
    else:
        status, emoji = base_status, base_emoji

    return pd.Series({'variance_pct': simple_pct, 'status': status, 'emoji': emoji})


if not kpis_df.empty:
    kpis_df[['variance_pct', 'status', 'emoji']] = kpis_df.apply(calc_variance_row, axis=1)

# ── Status filter ──────────────────────────────────────────────────────────────
status_filter = st.multiselect(
    "Filter by Status", options=['On Track', 'At Risk', 'Behind'],
    default=None, placeholder="All statuses"
)

filtered = kpis_df.copy()
if status_filter and not filtered.empty:
    filtered = filtered[filtered['status'].isin(status_filter)]


# ── Section renderer ───────────────────────────────────────────────────────────
def render_section(key: str, kpi_names: list, kpis_df: pd.DataFrame, fallback_df: pd.DataFrame = None):
    """Render an editable KPI table for a priority group."""
    table_key  = f'tbl_{key}'
    section_df = kpis_df[kpis_df['kpi_name'].isin(kpi_names)].copy() if not kpis_df.empty else pd.DataFrame()
    existing   = {row['kpi_name']: row for _, row in section_df.iterrows()}

    # Build fallback lookup (prior-period data for KPIs not in current quarter)
    fb_lookup: dict = {}
    if fallback_df is not None and not fallback_df.empty:
        fb_section = fallback_df[fallback_df['kpi_name'].isin(kpi_names)]
        fb_lookup  = {row['kpi_name']: row for _, row in fb_section.iterrows()}

    rows = []
    for name in kpi_names:
        mapped_name  = DISPLAY_NAME_MAP.get(name, name)
        display_name = f"  ↳  {mapped_name}" if name in SUB_KPIS else mapped_name
        if name in existing:
            kpi = existing[name]
            try:
                vp = kpi.get('variance_pct')
                pct = f"{float(vp):.1f}%" if vp is not None and str(vp) not in ('', 'nan', 'None') else ''
            except (TypeError, ValueError):
                pct = ''
            status_raw  = kpi.get('status', '') or ''
            emoji_raw   = kpi.get('emoji',  '') or STATUS_EMOJI.get(status_raw, '')
            status_disp = f"{emoji_raw} {status_raw}".strip() if status_raw else ''

            actual_display = fmt(kpi['actual_value'], name)
            if name in FORECAST_KPIS:
                forecast_num = extract_forecast(kpi.get('comments', '') or '')
                if forecast_num:
                    actual_display = fmt(forecast_num, name)
                    f_pct, f_status, f_emoji = calculate_variance(
                        forecast_num, kpi['target_value'],
                        is_inverse=is_inverse_kpi(name)
                    )
                    if f_pct is not None:
                        pct = f"{float(f_pct):.1f}%"
                    if f_status:
                        status_disp = f"{f_emoji or ''} {f_status}".strip()

            rows.append({
                '_kpi':      name,
                'KPI':       display_name,
                'Target':    fmt(kpi['target_value'], name),
                'Actual':    actual_display,
                '% to Goal': pct,
                'Status':    status_disp,
                'Updated':   fmt_date(kpi.get('date')),
                'Comments':  kpi.get('comments', '') or '',
            })
        elif name in fb_lookup:
            # Show most-recent data from a prior period with a "(Qx)" indicator
            kpi = fb_lookup[name]
            kpi_qtr  = kpi.get('quarter', '')
            date_str = fmt_date(kpi.get('date'))
            updated_str = f"{date_str} ({kpi_qtr})" if kpi_qtr and kpi_qtr != quarter else date_str
            try:
                simple_pct, fb_status, fb_emoji = calculate_variance(
                    kpi['actual_value'], kpi['target_value'],
                    is_inverse=is_inverse_kpi(name)
                )
                pct = f"{float(simple_pct):.1f}%" if simple_pct is not None else ''
                status_disp = f"{fb_emoji} {fb_status}".strip() if fb_status else ''
            except Exception:
                pct, status_disp = '', ''
            rows.append({
                '_kpi':      name,
                'KPI':       display_name,
                'Target':    fmt(kpi.get('target_value', ''), name),
                'Actual':    fmt(kpi.get('actual_value', ''), name),
                '% to Goal': pct,
                'Status':    status_disp,
                'Updated':   updated_str,
                'Comments':  kpi.get('comments', '') or '',
            })
        else:
            rows.append({
                '_kpi': name, 'KPI': display_name,
                'Target': '', 'Actual': '', '% to Goal': '',
                'Status': '', 'Updated': '', 'Comments': '',
            })

    # ── Real-time recalculation ─────────────────────────────────────────────
    # When a user commits a cell edit (Tab/Enter), Streamlit reruns and the
    # pending edits live in st.session_state[table_key]['edited_rows'].
    # We apply those here so % to Goal and Status update immediately.
    live_state  = st.session_state.get(table_key, {})
    live_edits  = live_state.get('edited_rows', {}) if isinstance(live_state, dict) else {}
    for row_idx, col_changes in live_edits.items():
        row_idx = int(row_idx)
        if row_idx >= len(rows):
            continue
        row = rows[row_idx]
        kpi_name       = row['_kpi']
        target_edited  = 'Target' in col_changes
        actual_edited  = 'Actual' in col_changes
        status_edited  = 'Status' in col_changes
        if not (target_edited or actual_edited):
            continue
        eff_target = col_changes.get('Target', row['Target'])
        eff_actual = col_changes.get('Actual', row['Actual'])
        if eff_target and eff_actual:
            simple_pct, _, _ = calculate_variance(
                eff_actual, eff_target, is_inverse=is_inverse_kpi(kpi_name)
            )
            if simple_pct is not None:
                rows[row_idx]['% to Goal'] = f"{simple_pct:.1f}%"
            if not status_edited:
                if kpi_name in PACE_KPIS:
                    _, status, emoji = calculate_pace_status(eff_actual, eff_target, pct_elapsed)
                else:
                    _, status, emoji = calculate_variance(
                        eff_actual, eff_target, is_inverse=is_inverse_kpi(kpi_name)
                    )
                rows[row_idx]['Status'] = f"{emoji} {status}".strip() if status else ''
        else:
            rows[row_idx]['% to Goal'] = ''
            if not status_edited:
                rows[row_idx]['Status'] = ''

    display_df = pd.DataFrame(rows)

    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            '_kpi':      None,
            'KPI':       st.column_config.TextColumn('KPI',       width='medium', disabled=True),
            'Target':    st.column_config.TextColumn('Target',    width='small'),
            'Actual':    st.column_config.TextColumn('Actual',    width='small'),
            '% to Goal': st.column_config.TextColumn('% to Goal', width='small',  disabled=True),
            'Status':    st.column_config.SelectboxColumn(
                             'Status', width='small',
                             options=STATUS_OPTIONS + [''],
                         ),
            'Updated':   st.column_config.TextColumn('Updated',   width='small',  disabled=True),
            'Comments':  st.column_config.TextColumn('Comments'),
        },
        num_rows='fixed',
        key=table_key,
    )

    st.caption(f"{len(display_df)} KPIs  ·  Tab or Enter to commit a change — auto-saves immediately")

    # ── Autosave: persist edits as soon as the user commits a cell ──────────
    # live_edits contains only the rows the user actually changed this rerun.
    if live_edits:
        saved, errors = 0, []
        for row_idx_str, col_changes in live_edits.items():
            row_idx = int(row_idx_str)
            if row_idx >= len(rows):
                continue
            orig_row = display_df.iloc[row_idx]
            kpi_name = str(orig_row['_kpi'])

            # Use col_changes keys directly — more reliable than comparing edited_df
            # values which may not reflect session-state edits in all Streamlit versions.
            actual_changed   = 'Actual'   in col_changes
            target_changed   = 'Target'   in col_changes
            status_changed   = 'Status'   in col_changes
            comments_changed = 'Comments' in col_changes
            if not (target_changed or actual_changed or status_changed or comments_changed):
                continue

            orig_kpi = existing.get(kpi_name)
            new_actual = (
                clean_actual(col_changes['Actual']) if actual_changed
                else str(orig_kpi['actual_value'] if orig_kpi is not None else '' or '')
            )
            target_val = (
                str(col_changes['Target']).strip() if target_changed
                else str(orig_kpi['target_value'] if orig_kpi is not None else '' or '')
            )
            new_comments = col_changes.get('Comments', str(orig_row['Comments'] or ''))

            new_status_disp = col_changes.get('Status', '') if status_changed else ''
            if status_changed and new_status_disp:
                raw_status = new_status_disp.split(' ', 1)[-1].strip()
                vp = None
            else:
                vp, raw_status, _ = calculate_variance(
                    new_actual, target_val,
                    is_inverse=is_inverse_kpi(kpi_name)
                )
            try:
                db.save_kpi({
                    'kpi_name':     kpi_name,
                    'owner':        orig_kpi['owner']   if orig_kpi is not None else '',
                    'cadence':      orig_kpi['cadence'] if orig_kpi is not None else '',
                    'quarter':      quarter, 'year': year,
                    'date':         date.today(),
                    'target_value': target_val,
                    'actual_value': new_actual,
                    'status':       raw_status or '',
                    'variance_pct': vp,
                    'source':       orig_kpi['source'] if orig_kpi is not None else 'Manual',
                    'comments':     new_comments,
                    'updated_by':   'Dashboard Edit',
                })
                saved += 1
            except Exception as e:
                errors.append(f"{kpi_name}: {e}")

        for err in errors:
            st.error(err)
        if saved > 0:
            if table_key in st.session_state:
                del st.session_state[table_key]
            st.toast(f"✅ Auto-saved {saved} change{'s' if saved > 1 else ''}", icon="✅")
            st.rerun()


# ── Quarter progress banner ─────────────────────────────────────────────────────
pct_str   = f"{pct_elapsed*100:.0f}%"
bar_fill  = int(pct_elapsed * 20)
bar       = "█" * bar_fill + "░" * (20 - bar_fill)
st.markdown(
    f"<div style='font-size:0.82rem;color:#555;margin-bottom:8px;'>"
    f"<b>{quarter} {year}</b> &nbsp;·&nbsp; "
    f"<code style='font-size:0.78rem;letter-spacing:0.5px;'>{bar}</code>"
    f" &nbsp;{pct_str} complete &nbsp;·&nbsp; "
    f"<b style='color:#E75944;'>{days_left} days left</b>"
    f"</div>",
    unsafe_allow_html=True,
)


# ── Executive Summary ─────────────────────────────────────────────────────────
def _kpi_val(df, name):
    """Get actual_value for a KPI name from the dataframe, return float or None."""
    if df.empty:
        return None
    row = df[df['kpi_name'] == name]
    if row.empty:
        return None
    raw = str(row.iloc[0]['actual_value']).replace('$', '').replace(',', '').replace('%', '').strip()
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _kpi_target(df, name):
    """Get target_value for a KPI name."""
    if df.empty:
        return None
    row = df[df['kpi_name'] == name]
    if row.empty:
        return None
    raw = str(row.iloc[0]['target_value']).replace('$', '').replace(',', '').replace('%', '').strip()
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _kpi_comments(df, name):
    """Get comments for a KPI name."""
    if df.empty:
        return ''
    row = df[df['kpi_name'] == name]
    if row.empty:
        return ''
    return str(row.iloc[0].get('comments', '') or '')


def render_exec_summary(df, quarter, year, pct_elapsed, days_left):
    """Render an auto-generated executive summary from the latest KPI data."""
    # Pull key metrics
    nl_arr = _kpi_val(df, 'New Logo ARR')
    nl_target = _kpi_target(df, 'New Logo ARR')
    exp_arr = _kpi_val(df, 'Expansion ARR')
    exp_target = _kpi_target(df, 'Expansion ARR')
    total_forecast = _kpi_val(df, 'Total New ARR Forecast')
    total_target = _kpi_target(df, 'Total New ARR Forecast')
    sqls = _kpi_val(df, 'SQL')
    sql_target = _kpi_target(df, 'SQL')
    pipeline = _kpi_val(df, 'New Logo Pipeline Created')
    pipeline_target = _kpi_target(df, 'New Logo Pipeline Created')
    wr_overall = _kpi_val(df, 'Win Rate (Overall)')
    wr_target = _kpi_target(df, 'Win Rate (Overall)')
    wr_sal = _kpi_val(df, 'Win Rate (SAL)')
    wr_aec = _kpi_val(df, 'Win Rate (AEC)')
    acv = _kpi_val(df, 'ACV (Overall)')
    acv_target = _kpi_target(df, 'ACV (Overall)')
    grr = _kpi_val(df, 'GRR')
    nrr = _kpi_val(df, 'NRR')
    exp_180 = _kpi_val(df, 'Expansion Pipeline (Next 180 Days)')

    # SQL comments contain inbound/outbound breakdown
    sql_comments = _kpi_comments(df, 'SQL')

    # Additional retention metrics
    logo_ret = _kpi_val(df, 'Logo Retention')
    logo_ret_target = _kpi_target(df, 'Logo Retention')
    grr_target = _kpi_target(df, 'GRR')
    nrr_target = _kpi_target(df, 'NRR')
    renewal_risk = _kpi_val(df, 'Renewal ARR risk (Next 180 days)')
    renewal_logo_risk = _kpi_val(df, 'Renewal Logo Risk (Next 180 days)')

    if nl_arr is None and total_forecast is None and grr is None:
        return  # No data to summarize

    # ── Build summary cards ───────────────────────────────────────────────
    st.markdown("### Executive Summary")

    # ROW 1: Growth (New Business)
    st.markdown(
        '<div style="font-size:0.78rem; font-weight:600; color:#888; text-transform:uppercase; '
        'letter-spacing:0.5px; margin-bottom:2px; margin-top:8px;">Growth</div>',
        unsafe_allow_html=True,
    )
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        if total_forecast is not None and total_target:
            pct = total_forecast / total_target * 100
            st.metric("ARR Forecast", f"${total_forecast:,.0f}", f"{pct:.0f}% of target")
    with m2:
        if nl_arr is not None:
            delta = f"{nl_arr/nl_target*100:.0f}% of target" if nl_target else ""
            st.metric("New Logo ARR", f"${nl_arr:,.0f}", delta)
    with m3:
        if pipeline is not None:
            delta = f"{pipeline/pipeline_target*100:.0f}% of target" if pipeline_target else ""
            st.metric("Pipeline Created", f"${pipeline:,.0f}", delta)
    with m4:
        if wr_overall is not None:
            delta = f"Target: {wr_target:.0f}%" if wr_target else ""
            st.metric("Win Rate", f"{wr_overall:.1f}%", delta,
                      delta_color="inverse" if wr_target and wr_overall < wr_target else "normal")
    with m5:
        if sqls is not None:
            delta = f"{sqls/sql_target*100:.0f}% of {int(sql_target)}" if sql_target else ""
            st.metric("SQLs", f"{int(sqls)}", delta)

    # ROW 2: Retention & Expansion
    st.markdown(
        '<div style="font-size:0.78rem; font-weight:600; color:#888; text-transform:uppercase; '
        'letter-spacing:0.5px; margin-bottom:2px; margin-top:12px;">Retention & Expansion</div>',
        unsafe_allow_html=True,
    )
    r1, r2, r3, r4, r5 = st.columns(5)
    with r1:
        if grr is not None:
            delta = f"Target: {grr_target:.0f}%" if grr_target else ""
            st.metric("GRR", f"{grr:.1f}%", delta,
                      delta_color="inverse" if grr_target and grr < grr_target else "normal")
    with r2:
        if nrr is not None:
            delta = f"Target: {nrr_target:.0f}%" if nrr_target else ""
            st.metric("NRR", f"{nrr:.1f}%", delta,
                      delta_color="inverse" if nrr_target and nrr < nrr_target else "normal")
    with r3:
        if logo_ret is not None:
            delta = f"Target: {logo_ret_target:.0f}%" if logo_ret_target else ""
            st.metric("Logo Retention", f"{logo_ret:.1f}%", delta,
                      delta_color="inverse" if logo_ret_target and logo_ret < logo_ret_target else "normal")
    with r4:
        if exp_arr is not None:
            delta = f"{exp_arr/exp_target*100:.0f}% of target" if exp_target else ""
            st.metric("Expansion ARR", f"${exp_arr:,.0f}", delta)
    with r5:
        if acv is not None:
            delta = f"Target: ${acv_target:,.0f}" if acv_target else ""
            st.metric("ACV (Median)", f"${acv:,.0f}", delta)

    # ── Plain-language narrative (bullet list, consistent formatting) ────
    bullets = []

    # Overall ARR picture
    if total_forecast is not None and total_target:
        total_pct = total_forecast / total_target * 100
        gap = total_target - total_forecast
        if total_pct >= 95:
            bullets.append(
                f"Total new ARR forecast is ${total_forecast:,.0f} — on track to hit the ${total_target:,.0f} target."
            )
        elif total_pct >= 80:
            bullets.append(
                f"Total new ARR forecast is ${total_forecast:,.0f}, about ${gap:,.0f} short of the ${total_target:,.0f} target. "
                f"{days_left} days left in the quarter."
            )
        else:
            bullets.append(
                f"Total new ARR forecast is ${total_forecast:,.0f} — ${gap:,.0f} below the ${total_target:,.0f} target. "
                f"Significant gap with only {days_left} days remaining."
            )

    # New logo + expansion
    if nl_arr is not None and nl_target:
        nl_gap = nl_target - nl_arr
        if nl_gap > 0:
            bullets.append(f"New logo ARR is ${nl_arr:,.0f} — ${nl_gap:,.0f} away from the ${nl_target:,.0f} goal.")
        else:
            bullets.append(f"New logo ARR is ${nl_arr:,.0f}, beating the ${nl_target:,.0f} target.")

    if exp_arr is not None and exp_target:
        exp_gap = exp_target - exp_arr
        if exp_gap > 0:
            bullets.append(f"Expansion ARR is ${exp_arr:,.0f} with ${exp_gap:,.0f} to go against ${exp_target:,.0f}.")
        else:
            bullets.append(f"Expansion ARR is ${exp_arr:,.0f}, ahead of the ${exp_target:,.0f} target.")

    # Pipeline
    if pipeline is not None and pipeline_target:
        pipe_pct = pipeline / pipeline_target * 100
        if pipe_pct >= 100:
            bullets.append(
                f"Pipeline created is ${pipeline:,.0f}, ahead of the ${pipeline_target:,.0f} target. "
                f"Top of funnel is not the issue."
            )
        elif pipe_pct >= 85:
            bullets.append(f"Pipeline created is ${pipeline:,.0f} ({pipe_pct:.0f}% of target). Healthy top of funnel.")

    # Win rate
    if wr_overall is not None and wr_target:
        if wr_overall < wr_target * 0.6:
            wr_line = (
                f"Win rate is {wr_overall:.1f}% vs. {wr_target:.0f}% target — "
                f"conversion is the main bottleneck."
            )
            if wr_sal is not None and wr_aec is not None:
                wr_line += f" AEC at {wr_aec:.1f}%, SAL at {wr_sal:.1f}%."
            bullets.append(wr_line)
        elif wr_overall < wr_target:
            bullets.append(f"Win rate is {wr_overall:.1f}% vs. {wr_target:.0f}% target — needs improvement.")

    # ACV
    if acv is not None and acv_target:
        if acv >= acv_target:
            bullets.append(f"Median deal size (ACV) is ${acv:,.0f}, above the ${acv_target:,.0f} target.")

    # SQLs
    if sqls is not None and sql_target:
        sql_pct = sqls / sql_target * 100
        if sql_pct < pct_elapsed * 100 * 0.85:
            sql_gap = int(sql_target - sqls)
            bullets.append(f"SQLs at {int(sqls)} vs. {int(sql_target)} target — need {sql_gap} more in {days_left} days.")

    # Retention
    ret_parts = []
    if grr is not None:
        grr_note = f" (target: {grr_target:.0f}%)" if grr_target else ""
        ret_parts.append(f"GRR {grr:.1f}%{grr_note}")
    if nrr is not None:
        nrr_note = f" (target: {nrr_target:.0f}%)" if nrr_target else ""
        ret_parts.append(f"NRR {nrr:.1f}%{nrr_note}")
    if logo_ret is not None:
        lr_note = f" (target: {logo_ret_target:.0f}%)" if logo_ret_target else ""
        ret_parts.append(f"Logo Retention {logo_ret:.1f}%{lr_note}")
    if ret_parts:
        bullets.append("Retention: " + ", ".join(ret_parts) + ".")
    if grr is not None and grr_target and grr < grr_target:
        gap = grr_target - grr
        bullets.append(f"GRR is {gap:.1f} points below target — retention improvement is critical to hit plan.")

    if bullets:
        bullet_html = "".join(f"<li>{b}</li>" for b in bullets)
        st.markdown(
            f'<ul style="font-size:0.92rem; line-height:1.7; margin-top:4px;">{bullet_html}</ul>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Not enough KPI data to generate a summary. Sync HubSpot data from Settings.")

    st.markdown("---")


if not kpis_df.empty:
    render_exec_summary(kpis_df, quarter, year, pct_elapsed, days_left)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_labels = ["📋 All KPIs"] + [g['label'] for g in PRIORITY_GROUPS.values()]
tabs = st.tabs(tab_labels)

with tabs[0]:  # All KPIs tab — show each priority group as a subsection
    for key, group in PRIORITY_GROUPS.items():
        st.subheader(group['label'])
        render_section(f'all_{key}', group['kpis'], filtered, fallback_df)
        st.markdown("")

for tab, (key, group) in zip(tabs[1:], PRIORITY_GROUPS.items()):
    with tab:
        render_section(key, group['kpis'], filtered, fallback_df)

st.markdown("---")

# ── Export ─────────────────────────────────────────────────────────────────────
if st.button("📥 Export to CSV"):
    rows = []
    for _, kpi in filtered.iterrows():
        name = kpi['kpi_name']
        rows.append({
            'KPI':          name,
            'Target':       fmt(kpi['target_value'], name),
            'Actual':       fmt(kpi['actual_value'], name),
            'Status':       kpi.get('status', ''),
            'Last Updated': fmt_date(kpi.get('date')),
            'Comments':     kpi.get('comments', '') or '',
        })
    csv = pd.DataFrame(rows).to_csv(index=False)
    st.download_button("Download CSV", data=csv,
                       file_name=f"cr_pulse_{quarter}_{year}.csv", mime="text/csv")
