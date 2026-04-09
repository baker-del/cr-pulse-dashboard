"""
Shared weekly cohort loader for S&M Efficiency.
Used by both the Streamlit page (falls back to DB) and process_weekly_cohorts.py.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SAL_INDUSTRIES     = {'staffing', 'accounting', 'hr services', 'legal', 'rpo'}
AEC_INDUSTRIES     = {'architecture & planning', 'construction', 'commercial construction', 'engineering'}
NEW_LOGO_PIPELINES = {'default', '757781604'}

QUARTER_BOUNDS = {
    'Q1': ((1, 1),  (3, 31)),
    'Q2': ((4, 1),  (6, 30)),
    'Q3': ((7, 1),  (9, 30)),
    'Q4': ((10, 1), (12, 31)),
}


def _classify(raw):
    v = (raw or '').lower().strip()
    if v in SAL_INDUSTRIES: return 'SAL'
    if v in AEC_INDUSTRIES: return 'AEC'
    return 'Other'


def _parse_dt(s):
    if not s: return None
    for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S'):
        try: return datetime.strptime(s[:26].rstrip('Z'), fmt.rstrip('Z')).replace(tzinfo=timezone.utc)
        except: pass
    try: return datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc)
    except: return None


def _q_bounds(quarter, year):
    (sm, sd), (em, ed) = QUARTER_BOUNDS[quarter]
    start = datetime(year, sm, sd, tzinfo=timezone.utc)
    end   = datetime(year, em, ed, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _week_start(dt):
    return (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def _week_label(ws, q_start):
    effective = max(ws, q_start)
    return effective.strftime('%b %-d')


def load_weekly_cohorts_from_files(quarter: str, year: int, root: Path) -> dict | None:
    """
    Reads hubspot_mqls_*.json and hubspot_deals_*.json from root directory,
    computes weekly SAL/AEC cohort rows, and returns the same dict structure
    used by the page: {'sal': [...], 'aec': [...], 'file_date': str}.
    Returns None if either file is missing.
    """
    mql_file  = root / f'hubspot_mqls_{quarter.lower()}_{year}.json'
    deal_file = root / f'hubspot_deals_{quarter.lower()}_{year}.json'

    if not mql_file.exists() or not deal_file.exists():
        return None

    contacts  = json.loads(mql_file.read_text())
    deals     = json.loads(deal_file.read_text())
    q_start, q_end = _q_bounds(quarter, year)

    # ── MQL + SAL weekly buckets ──────────────────────────────────────────────
    mql_weeks = defaultdict(lambda: {
        'sal': 0, 'aec': 0, 'total': 0,
        'sal_sal': 0, 'aec_sal': 0,
        'sources': Counter(),
    })

    for c in contacts:
        p      = c.get('properties', {})
        ind    = _classify(p.get('industry_dropdown', ''))
        src    = (p.get('lead_source', '') or 'Unknown').replace('_', ' ').title()
        mql_dt = _parse_dt(p.get('hs_v2_date_entered_marketingqualifiedlead', ''))
        sal_dt = _parse_dt(p.get('hs_v2_date_entered_opportunity', ''))
        if not mql_dt or mql_dt < q_start or mql_dt > q_end:
            continue
        ws = _week_start(mql_dt)
        mql_weeks[ws]['total'] += 1
        mql_weeks[ws]['sources'][src] += 1
        if ind == 'SAL':
            mql_weeks[ws]['sal'] += 1
            if sal_dt: mql_weeks[ws]['sal_sal'] += 1
        elif ind == 'AEC':
            mql_weeks[ws]['aec'] += 1
            if sal_dt: mql_weeks[ws]['aec_sal'] += 1

    # ── Deal weekly buckets ───────────────────────────────────────────────────
    deal_weeks = defaultdict(lambda: {
        'sal_sql_mkt': 0,   'aec_sql_mkt': 0,
        'sal_sql_sales': 0, 'aec_sql_sales': 0,
        'sal_sql_csm': 0,   'aec_sql_csm': 0,
        'sal_sql_total': 0, 'aec_sql_total': 0,
        'sal_pipeline': 0.0,'aec_pipeline': 0.0,
    })

    for deal in deals:
        p         = deal.get('properties', {})
        pipeline  = p.get('pipeline', '')
        create_dt = _parse_dt(p.get('createdate', ''))
        if not create_dt or pipeline not in NEW_LOGO_PIPELINES:
            continue
        if create_dt < q_start or create_dt > q_end:
            continue
        ws     = _week_start(create_dt)
        ind    = _classify(p.get('company_industry_dropdown', ''))
        amt    = float(p.get('amount', 0) or 0)
        disc   = p.get('demo_discovery_status', '') or ''
        bucket = (p.get('deal_source_bucket', '') or '').strip()

        if disc == 'Completed':
            if ind == 'SAL':
                deal_weeks[ws]['sal_sql_total'] += 1
                if bucket in ('Marketing Driven', ''):  deal_weeks[ws]['sal_sql_mkt']   += 1
                elif bucket == 'Sales Driven':           deal_weeks[ws]['sal_sql_sales'] += 1
                elif bucket == 'CSM Driven':             deal_weeks[ws]['sal_sql_csm']   += 1
            elif ind == 'AEC':
                deal_weeks[ws]['aec_sql_total'] += 1
                if bucket in ('Marketing Driven', ''):  deal_weeks[ws]['aec_sql_mkt']   += 1
                elif bucket == 'Sales Driven':           deal_weeks[ws]['aec_sql_sales'] += 1
                elif bucket == 'CSM Driven':             deal_weeks[ws]['aec_sql_csm']   += 1

        if ind == 'SAL':   deal_weeks[ws]['sal_pipeline'] += amt
        elif ind == 'AEC': deal_weeks[ws]['aec_pipeline'] += amt

    # ── Build sorted week list ────────────────────────────────────────────────
    all_weeks = sorted(set(list(mql_weeks.keys()) + list(deal_weeks.keys())))
    all_weeks = [ws for ws in all_weeks if ws <= q_end]

    def build_rows(vertical):
        v = vertical.lower()
        rows = []
        cum_mqls = cum_sals = cum_sqls_mkt = 0
        for ws in all_weeks:
            m         = mql_weeks[ws]
            d         = deal_weeks[ws]
            total     = m['total']
            icp_n     = m[v]
            sal_n     = m[f'{v}_sal']
            icp_pct   = round(icp_n / total * 100, 1) if total > 0 else 0
            mql_sal   = round(sal_n / icp_n * 100, 1)  if icp_n > 0 else 0
            sql_mkt   = d[f'{v}_sql_mkt']
            sql_sales = d[f'{v}_sql_sales']
            sql_csm   = d[f'{v}_sql_csm']
            sql_total = d[f'{v}_sql_total']
            sal_sql   = round(sql_mkt / sal_n * 100, 1) if sal_n > 0 else 0
            pipeline  = d[f'{v}_pipeline']

            cum_mqls     += icp_n
            cum_sals     += sal_n
            cum_sqls_mkt += sql_mkt
            cum_mql_sal   = round(cum_sals     / cum_mqls      * 100, 1) if cum_mqls  > 0 else 0
            cum_sal_sql   = round(cum_sqls_mkt / cum_sals      * 100, 1) if cum_sals  > 0 else 0
            cum_mql_sql   = round(cum_sqls_mkt / cum_mqls      * 100, 1) if cum_mqls  > 0 else 0

            top_src = ', '.join(f"{s} ({n})" for s, n in m['sources'].most_common(2))

            rows.append({
                'week_start':   ws,
                'week_label':   _week_label(ws, q_start),
                'lead_sources': top_src or '—',
                'total_mqls':   total,
                'icp_mqls':     icp_n,
                'icp_pct':      icp_pct,
                'sal_n':        sal_n,
                'mql_sal_pct':  mql_sal,
                'sql_mkt':      sql_mkt,
                'sql_sales':    sql_sales,
                'sql_csm':      sql_csm,
                'sql_total':    sql_total,
                'sal_sql_pct':  sal_sql,
                'pipeline':     pipeline,
                'cum_mqls':     cum_mqls,
                'cum_sals':     cum_sals,
                'cum_sqls_mkt': cum_sqls_mkt,
                'cum_mql_sal':  cum_mql_sal,
                'cum_sal_sql':  cum_sal_sql,
                'cum_mql_sql':  cum_mql_sql,
            })
        return rows

    file_dt = datetime.fromtimestamp(mql_file.stat().st_mtime).strftime('%b %-d, %Y %-I:%M %p')
    return {
        'sal':       build_rows('SAL'),
        'aec':       build_rows('AEC'),
        'file_date': file_dt,
    }
