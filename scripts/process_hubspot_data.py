#!/usr/bin/env python3
"""
Process HubSpot deal data and calculate KPIs

Pipeline IDs (confirmed from HubSpot):
  default        = Sales Pipeline          → New Logo ARR, SQLs (AEC/Accounting deals merged here Apr 2026)
  757781604      = ClientSavvy Sales Pipeline → RETIRED Apr 2026, all deals migrated to default
  47062345       = Expansion Pipeline      → Expansion ARR only
  691884922      = Services Pipeline       → Excluded
  10d22554-...   = CS Pipeline (Renewals)  → Excluded
  734782643      = Renewal Pipeline        → Excluded

Sales Pipeline stages (as of Apr 2026):
  qualifiedtobuy          = 1 - Discovery          (10%)
  decisionmakerboughtin   = 2 - Solution Alignment (20%)
  846553                  = 3 - Technical Review   (60%)
  266892603               = 4 - Onboarding Overview(80%)
  contractsent            = 5 - Vendor of Choice   (90%)
  266892604               = 6 - Contract Executed  (100%)
  closedwon               = Closed Won             (100%)
  closedlost              = Closed Lost            (0%)

ARR Forecast:
  Uses hs_deal_stage_probability (fetch with --properties) if available.
  Falls back to STAGE_PROBABILITY_MAP for known stage IDs.
  All open deals with close date in the quarter are included (excl. closed-lost).
  New Logo Forecast excludes dealtype=renewal.

─── HUBSPOT DATA FETCH REQUIREMENTS ───────────────────────────────────────────

  IMPORTANT: When fetching deals from HubSpot MCP tools, the search filters
  must be BROAD ENOUGH to capture all relevant deals. Deals may have been
  created months or years before they close, so filtering by createdate alone
  will miss closed-won deals.

  Required HubSpot search strategy for quarter Q of year Y:

  Properties to fetch:
    dealname, dealstage, pipeline, amount, dealtype, closedate, createdate,
    demo_discovery_status, sales_outbound_vs_inbound,
    hs_deal_stage_probability, company_industry_dropdown

  Filter groups (combined with OR logic):

    Group 1 — Deals CLOSING in the target quarter (catches ARR, forecast,
              win rates, qualified pipeline regardless of when created):
      - closedate >= Q_start  AND  closedate <= Q_end
      - pipeline IN [default, 47062345]

    Group 2 — Deals CLOSING in the NEXT quarter (catches forecast deals
              and pipeline coverage that spans quarter boundaries):
      - closedate >= Q_next_start  AND  closedate <= Q_next_end
      - pipeline IN [default, 47062345]

    Group 3 — Deals CREATED in the target quarter (catches SQLs, pipeline
              created even if close date is far in the future):
      - createdate >= Q_start  AND  createdate <= Q_end
      - pipeline IN [default]

    Group 4 — Open Expansion deals closing within 180 days (catches
              Expansion Pipeline KPI):
      - pipeline = 47062345
      - closedate >= today  AND  closedate <= today + 180 days

  Pagination: HubSpot returns max 200 results per page. Always check
  if offset < total and fetch additional pages if needed.

────────────────────────────────────────────────────────────────────────────────
"""

import json
import sys
import statistics
import yaml
from datetime import datetime, date, timezone
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db
from utils.kpi_calculator import calculate_variance, get_quarter_from_date


# ── Pipeline constants ─────────────────────────────────────────────────────────
NEW_LOGO_PIPELINES = ['default']                # Sales Pipeline only (ClientSavvy merged Apr 2026)
EXPANSION_PIPELINES = ['47062345']              # Expansion
SQL_PIPELINES = ['default']                     # Same as New Logo

# Win rate: only count deals created on or after this date to exclude historical cleanup deals
# (old CFT/renewal deals from 2023-2024 being marked closed-lost in Q1 2026)
WIN_RATE_MIN_CREATEDATE = datetime(2025, 1, 1, tzinfo=timezone.utc)

# Win rate: exclude deals closed in the first N business days of a quarter (end-of-prior-quarter cleanup)
WIN_RATE_QUARTER_GRACE_BDAYS = 3

# Closed-won deal stage IDs across all pipelines
CLOSED_WON_STAGES = [
    'closedwon',    # Sales Pipeline (default)
    '1102698292',   # ClientSavvy Sales Pipeline (confirmed)
    '96961410',     # Expansion pipeline closed won
    '1012929440',   # Services pipeline closed won (excluded from calcs, but listed for completeness)
    '16515',        # CS / Renewal pipeline closed won
]
CLOSED_LOST_STAGES = ['closedlost', '1102698293']

# ── Stage probability map ──────────────────────────────────────────────────────
# Used for ARR forecast when hs_deal_stage_probability is not in the fetched data.
# Values are 0.0–1.0 (close probability). Closed-lost stages → 0.0 (excluded).
STAGE_PROBABILITY_MAP = {
    # Sales Pipeline (default) — stages as of Apr 2026
    'closedwon':              1.00,   # Closed Won
    'closedlost':             0.00,   # Closed Lost
    'qualifiedtobuy':         0.10,   # 1 - Discovery
    'decisionmakerboughtin':  0.20,   # 2 - Solution Alignment
    '846553':                 0.60,   # 3 - Technical Review
    '266892603':              0.80,   # 4 - Onboarding Overview
    'contractsent':           0.90,   # 5 - Vendor of Choice
    '266892604':              1.00,   # 6 - Contract Executed
    # ClientSavvy Sales Pipeline (757781604) — RETIRED Apr 2026, kept for historical deals
    '1102698292':             1.00,   # Closed Won
    '1102698293':             0.00,   # Closed Lost
    '1102698286':             0.20,   # Stage 1
    '1102698287':             0.30,   # Stage 2
    '1102698288':             0.40,   # Stage 3
    '1102698289':             0.50,   # Stage 4
    '1102698290':             0.60,   # Stage 5
    '1102698291':             0.80,   # Stage 6
    # Expansion Pipeline (47062345)
    '96961410':               1.00,   # Closed Won
}
_DEFAULT_STAGE_PROB = 0.25   # fallback for any unrecognised stage


def _get_stage_probability(props: dict) -> float:
    """Return close probability (0.0–1.0) using hs_deal_stage_probability if present,
    otherwise fall back to STAGE_PROBABILITY_MAP."""
    raw = props.get('hs_deal_stage_probability', '')
    if raw and str(raw).strip() not in ('', 'None', 'null'):
        try:
            return float(raw)
        except (ValueError, TypeError):
            pass
    stage = props.get('dealstage', '')
    return STAGE_PROBABILITY_MAP.get(stage, _DEFAULT_STAGE_PROB)


def _is_closed_won(stage: str) -> bool:
    return stage in CLOSED_WON_STAGES or 'closedwon' in stage.lower()


def _is_closed_lost(stage: str) -> bool:
    return stage in CLOSED_LOST_STAGES or 'closedlost' in stage.lower()


def _in_quarter(dt: datetime, q_start: datetime, q_end: datetime) -> bool:
    return dt is not None and q_start <= dt <= q_end


def _parse_dt(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None


def _classify_industry(props: dict) -> str:
    """Classify a deal as SAL, AEC, or Other.

    Primary: company_industry_dropdown field (exact HubSpot dropdown values).
    Fallback: deal name keywords (for deals where the field is not yet populated).

    SAL = Accounting | Staffing and Recruiting | Legal
    AEC = Architecture & Planning | Civil Engineering | Engineering | Construction
    """
    # ── Primary: HubSpot Company_Industry_Dropdown field (exact values) ───
    # HubSpot stores "Staffing" (not "Staffing and Recruiting") — include both for safety
    SAL_INDUSTRIES = {'accounting', 'staffing and recruiting', 'staffing', 'legal'}
    AEC_INDUSTRIES = {'architecture & planning', 'civil engineering', 'engineering', 'construction'}

    ind = (props.get('company_industry_dropdown', '') or '').lower().strip()
    if ind:
        if ind in SAL_INDUSTRIES:
            return 'SAL'
        if ind in AEC_INDUSTRIES:
            return 'AEC'

    # ── Fallback: deal name keywords ───────────────────────────────────────
    # NOTE: company_industry_dropdown must be added to HubSpot fetch properties
    # for accurate classification. Name-based fallback is approximate.
    name = (props.get('dealname', '') or '').lower()

    # Legal
    if any(k in name for k in ['law', ' llp', 'llp ', 'attorney', 'legal', 'wpg',
                                'esquire', ' pllc', 'solicitor']):
        return 'SAL'
    # Staffing / HR / Recruiting
    if any(k in name for k in ['staffing', 'recruit', 'personnel', 'mla', 'costaff',
                                'talent', 'workforce', ' hr ', 'human resource']):
        return 'SAL'
    # Accounting / Finance / Tax
    if any(k in name for k in ['cpa', 'cpas', 'accountant', 'accounting', '.tax', 'tax ',
                                'financial', 'advisors', 'advisory', 'ledger', 'audit',
                                'bookkeep', 'assurance', 'valuation']):
        return 'SAL'
    # Architecture / Planning
    if any(k in name for k in ['architect', 'planning', 'interiors', 'dahlin', 'vmdo', 'smps',
                                'landscape', 'urban design']):
        return 'AEC'
    # Engineering
    if any(k in name for k in ['engineering', 'engineer', 'timmons', 'intertec', 'civil',
                                'structural', 'geotechnical', 'mechanical', 'surveying',
                                'surveyors', 'environmental consulting']):
        return 'AEC'
    # Construction
    if any(k in name for k in ['construction', 'contractor', 'contracting', 'builder',
                                'builders', 'big-d', 'big d', 'boldt', 'fendler', 'pcl']):
        return 'AEC'
    return 'Other'


# ── Main processing function ───────────────────────────────────────────────────

def process_hubspot_deals(deals_data, quarter="Q1", year=2026):
    """Process HubSpot deals and calculate KPIs"""

    # Quarter date ranges (timezone-aware)
    quarter_ranges = {
        'Q1': (datetime(year, 1, 1, tzinfo=timezone.utc), datetime(year, 3, 31, 23, 59, 59, tzinfo=timezone.utc)),
        'Q2': (datetime(year, 4, 1, tzinfo=timezone.utc), datetime(year, 6, 30, 23, 59, 59, tzinfo=timezone.utc)),
        'Q3': (datetime(year, 7, 1, tzinfo=timezone.utc), datetime(year, 9, 30, 23, 59, 59, tzinfo=timezone.utc)),
        'Q4': (datetime(year, 10, 1, tzinfo=timezone.utc), datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
    }
    q_start, q_end = quarter_ranges[quarter]

    # Next-180-days window for Expansion Pipeline KPI
    from datetime import timedelta
    today_utc = datetime.now(tz=timezone.utc)
    next_180_end = today_utc + timedelta(days=180)

    # Win rate grace: skip first N business days of the quarter
    _bdays, _d = 0, q_start
    while _bdays < WIN_RATE_QUARTER_GRACE_BDAYS:
        _d += timedelta(days=1)
        if _d.weekday() < 5:  # Mon–Fri
            _bdays += 1
    win_rate_start = _d

    # Counters
    new_logo_arr = 0
    new_logo_deals = []
    expansion_arr = 0
    expansion_deals = []
    new_logo_forecast = 0.0   # probability-weighted forecast
    expansion_forecast = 0.0  # probability-weighted forecast
    sqls_total = 0
    sqls_inbound = 0
    sqls_outbound = 0
    pipeline_created = 0
    sal_pipeline = 0   # New Logo pipeline created this quarter, SAL industry
    aec_pipeline = 0   # New Logo pipeline created this quarter, AEC industry
    qual_pipeline = 0      # Open New Logo deals closing this quarter (Qualified Pipeline Coverage)
    qual_sal_pipeline = 0
    qual_aec_pipeline = 0
    expansion_next_180 = 0  # Open Expansion deals closing in next 180 days
    sal_won = 0
    sal_lost = 0
    aec_won = 0
    aec_lost = 0
    overall_won = 0
    overall_lost = 0
    new_logo_amounts = []   # closed won amounts for ACV (median)
    sal_amounts = []
    aec_amounts = []
    sal_arr = 0             # SAL closed won ARR this quarter
    aec_arr = 0             # AEC closed won ARR this quarter
    sqls_sal = 0            # Marketing-attributed SQLs — SAL industry
    sqls_aec = 0            # Marketing-attributed SQLs — AEC industry
    sqls_sal_total = 0      # All SQLs — SAL (any source bucket)
    sqls_aec_total = 0      # All SQLs — AEC (any source bucket)
    sqls_sal_sales = 0      # Sales Driven SQLs — SAL
    sqls_aec_sales = 0      # Sales Driven SQLs — AEC
    sqls_sal_csm   = 0      # CSM Driven SQLs — SAL
    sqls_aec_csm   = 0      # CSM Driven SQLs — AEC
    # Stage funnel counters (for conversion rate calculations)
    sal_sol_align = 0       # SAL deals that entered Solution Alignment (Sales Pipeline)
    sal_demo_fit = 0        # SAL deals that entered Demo/Fit (Sales Pipeline)
    aec_disc_call = 0       # AEC deals that entered Discovery Call (ClientSavvy Pipeline)
    aec_demo_perf = 0       # AEC deals that entered Demo Performed (ClientSavvy Pipeline)
    aec_roi_call = 0        # AEC deals that entered ROI Call Completed (ClientSavvy Pipeline)

    # Exclude known test deals
    EXCLUDED_DEALS = {
        'affiliated engineers - as testing',
        'test - tdd',
    }

    for deal in deals_data:
        props = deal['properties']

        dealstage  = props.get('dealstage', '')
        pipeline   = props.get('pipeline', '')
        dealname   = props.get('dealname', '')

        # Skip test deals
        if dealname.lower().strip() in EXCLUDED_DEALS:
            continue
        amount     = float(props.get('amount', 0) or 0)
        dealtype   = (props.get('dealtype') or '').lower()

        # New properties we're now fetching
        discovery    = props.get('demo_discovery_status', '')
        lead_type    = props.get('sales_outbound_vs_inbound', '')
        source_bucket = (props.get('deal_source_bucket', '') or '').strip()

        close_dt  = _parse_dt(props.get('closedate', ''))
        create_dt = _parse_dt(props.get('createdate', ''))

        closed_won  = _is_closed_won(dealstage)
        closed_lost = _is_closed_lost(dealstage)
        q1_close    = _in_quarter(close_dt, q_start, q_end)
        q1_create   = _in_quarter(create_dt, q_start, q_end)

        # Classify industry once per deal (used by ARR, ACV, Win Rates, and Pipeline)
        # Uses company_industry_dropdown (wildcard) with deal name as fallback.
        industry = _classify_industry(props) if pipeline in NEW_LOGO_PIPELINES else 'Other'

        # ── NEW LOGO ARR + ACV tracking ────────────────────────────────────
        # Closed Won this quarter, in Sales or ClientSavvy Sales pipeline only
        if closed_won and q1_close and pipeline in NEW_LOGO_PIPELINES:
            new_logo_arr += amount
            new_logo_deals.append(dealname)
            if amount > 0:
                new_logo_amounts.append(amount)
                if industry == 'SAL':
                    sal_amounts.append(amount)
                    sal_arr += amount
                elif industry == 'AEC':
                    aec_amounts.append(amount)
                    aec_arr += amount

        # ── EXPANSION ARR ─────────────────────────────────────────────────
        # Closed Won this quarter, in Expansion pipeline
        if closed_won and q1_close and pipeline in EXPANSION_PIPELINES:
            expansion_arr += amount
            expansion_deals.append(dealname)

        # ── NEW LOGO ARR FORECAST ──────────────────────────────────────────
        # All deals (any stage except closed-lost) in New Logo pipelines
        # with close date this quarter, excluding renewal-type deals.
        # Weighted by hs_deal_stage_probability (falls back to STAGE_PROBABILITY_MAP).
        # dealtype check uses 'in' to catch "Renewal Business", "renewal", etc.
        if q1_close and pipeline in NEW_LOGO_PIPELINES and 'renewal' not in dealtype:
            prob = _get_stage_probability(props)
            if prob > 0:
                new_logo_forecast += amount * prob

        # ── EXPANSION ARR FORECAST ─────────────────────────────────────────
        # All deals (any stage except closed-lost) in Expansion pipeline
        # with close date this quarter. Weighted by hs_deal_stage_probability
        # (falls back to STAGE_PROBABILITY_MAP).
        if q1_close and pipeline in EXPANSION_PIPELINES:
            prob = _get_stage_probability(props)
            if prob > 0:
                expansion_forecast += amount * prob

        # ── SQLs ──────────────────────────────────────────────────────────
        # Created this quarter, in Sales or ClientSavvy Sales pipeline,
        # discovery_status = "Completed" (labeled "Completed (Qualified)")
        # deal_source_bucket: assume marketing unless explicitly "Sales Driven"
        #   "Sales Driven" → sales-attributed
        #   "CSM Driven"   → CSM-attributed
        #   anything else (blank, "Marketing Driven", unknown) → marketing
        is_sales_sql     = source_bucket == 'Sales Driven'
        is_csm_sql       = source_bucket == 'CSM Driven'
        is_marketing_sql = not is_sales_sql and not is_csm_sql
        if q1_create and pipeline in SQL_PIPELINES and discovery == 'Completed':
            sqls_total += 1
            if lead_type in ('Outbound', 'Outbound*'):
                sqls_outbound += 1
            else:
                sqls_inbound += 1
            if industry == 'SAL':
                sqls_sal_total += 1
                if is_marketing_sql: sqls_sal += 1
                elif is_sales_sql:   sqls_sal_sales += 1
                elif is_csm_sql:     sqls_sal_csm += 1
            elif industry == 'AEC':
                sqls_aec_total += 1
                if is_marketing_sql: sqls_aec += 1
                elif is_sales_sql:   sqls_aec_sales += 1
                elif is_csm_sql:     sqls_aec_csm += 1

        # ── PIPELINE CREATED ──────────────────────────────────────────────
        # New deals created this quarter in New Logo pipelines
        if q1_create and pipeline in NEW_LOGO_PIPELINES:
            pipeline_created += amount
            if industry == 'SAL':
                sal_pipeline += amount
            elif industry == 'AEC':
                aec_pipeline += amount

        # ── QUALIFIED PIPELINE COVERAGE ───────────────────────────────────
        # Open (not closed) New Logo deals with close date in current quarter
        if (not closed_won and not closed_lost
                and q1_close and pipeline in NEW_LOGO_PIPELINES):
            qual_pipeline += amount
            if industry == 'SAL':
                qual_sal_pipeline += amount
            elif industry == 'AEC':
                qual_aec_pipeline += amount

        # ── EXPANSION PIPELINE (NEXT 180 DAYS) ────────────────────────────
        # Open Expansion deals with close date in the next 180 days
        if (not closed_won and not closed_lost
                and pipeline in EXPANSION_PIPELINES
                and close_dt is not None
                and today_utc <= close_dt <= next_180_end):
            expansion_next_180 += amount

        # ── FUNNEL CONVERSION RATES ───────────────────────────────────────────
        # SAL: Sales Pipeline — Solution Alignment → Demo/Fit
        if pipeline == 'default' and industry == 'SAL':
            if props.get('hs_v2_date_entered_qualifiedtobuy'):
                sal_sol_align += 1
            if props.get('hs_v2_date_entered_decisionmakerboughtin'):
                sal_demo_fit += 1
        # AEC: ClientSavvy Pipeline — Discovery Call → Demo Performed → ROI Call
        if pipeline == '757781604' and industry == 'AEC':
            if props.get('hs_v2_date_entered_1102698286'):
                aec_disc_call += 1
            if props.get('hs_v2_date_entered_1102698287'):
                aec_demo_perf += 1
            if props.get('hs_v2_date_entered_1102698288'):
                aec_roi_call += 1

        # ── WIN RATES ─────────────────────────────────────────────────────
        # Deals closed this quarter in New Logo pipelines
        # Only count deals created >= WIN_RATE_MIN_CREATEDATE to exclude
        # historical cleanup deals (old 2023/2024 agreements closed-lost in 2026)
        # SAL = Staffing/Accounting/Legal; AEC = Architecture/Engineering/Construction
        recent_deal = create_dt is not None and create_dt >= WIN_RATE_MIN_CREATEDATE
        valid_close = close_dt is not None and close_dt >= win_rate_start
        if q1_close and pipeline in NEW_LOGO_PIPELINES and (closed_won or closed_lost) and recent_deal and valid_close:
            overall_won  += int(closed_won)
            overall_lost += int(closed_lost)
            if industry == 'SAL':
                sal_won  += int(closed_won)
                sal_lost += int(closed_lost)
            elif industry == 'AEC':
                aec_won  += int(closed_won)
                aec_lost += int(closed_lost)

    # SQL forecast — use trailing-30-day pace (captures recent momentum)
    # then project remaining days at that rate, added to current total
    q_total_days = (q_end - q_start).days + 1
    q_elapsed_days = max((today_utc - q_start).days, 1)  # at least 1 to avoid div/0
    q_remaining_days = max(q_total_days - q_elapsed_days, 0)

    if q_elapsed_days >= q_total_days:
        sql_forecast = sqls_total  # quarter is over, forecast = actual
    else:
        # Count SQLs created in trailing 30 days (or since quarter start if <30 days in)
        trailing_window = min(30, q_elapsed_days)
        trailing_start = today_utc - timedelta(days=trailing_window)
        sqls_trailing = 0
        for deal in deals_data:
            dp = deal['properties']
            if dp.get('pipeline', '') not in SQL_PIPELINES:
                continue
            if dp.get('demo_discovery_status', '') != 'Completed':
                continue
            cdt = _parse_dt(dp.get('createdate', ''))
            if cdt and trailing_start <= cdt <= today_utc:
                sqls_trailing += 1

        trailing_daily = sqls_trailing / trailing_window
        sql_forecast = sqls_total + round(trailing_daily * q_remaining_days)

    # Win rates
    overall_total = overall_won + overall_lost
    sal_total     = sal_won + sal_lost
    aec_total     = aec_won + aec_lost
    overall_wr = round(overall_won / overall_total * 100, 2) if overall_total > 0 else 0
    sal_wr     = round(sal_won     / sal_total     * 100, 2) if sal_total     > 0 else 0
    aec_wr     = round(aec_won     / aec_total     * 100, 2) if aec_total     > 0 else 0

    # Funnel conversion rates
    sal_disc_demo_pct = round(sal_demo_fit / sal_sol_align * 100, 1) if sal_sol_align > 0 else 0
    aec_disc_demo_pct = round(aec_demo_perf / aec_disc_call * 100, 1) if aec_disc_call > 0 else 0
    aec_demo_roi_pct  = round(aec_roi_call  / aec_demo_perf * 100, 1) if aec_demo_perf > 0 else 0

    # ACV — median deal amount for closed won new logo deals
    acv_overall = round(statistics.median(new_logo_amounts), 2) if new_logo_amounts else 0
    acv_sal     = round(statistics.median(sal_amounts), 2)      if sal_amounts      else 0
    acv_aec     = round(statistics.median(aec_amounts), 2)      if aec_amounts      else 0

    return {
        'new_logo_arr': {
            'value': round(new_logo_arr, 2),
            'count': len(new_logo_deals),
            'deals': new_logo_deals[:5]
        },
        'expansion_arr': {
            'value': round(expansion_arr, 2),
            'count': len(expansion_deals),
            'deals': expansion_deals[:5]
        },
        'new_logo_arr_forecast': {
            'value': round(new_logo_forecast, 2),
        },
        'expansion_arr_forecast': {
            'value': round(expansion_forecast, 2),
        },
        'sqls': {
            'total':      sqls_total,
            'inbound':    sqls_inbound,
            'outbound':   sqls_outbound,
            'sal':        sqls_sal,
            'aec':        sqls_aec,
            'sal_total':  sqls_sal_total,
            'aec_total':  sqls_aec_total,
            'sal_sales':  sqls_sal_sales,
            'aec_sales':  sqls_aec_sales,
            'sal_csm':    sqls_sal_csm,
            'aec_csm':    sqls_aec_csm,
            'forecast': sql_forecast,
            'days_elapsed': min(q_elapsed_days, q_total_days),
            'days_total':   q_total_days,
        },
        'bookings': {
            'sal': round(sal_arr, 2),
            'aec': round(aec_arr, 2),
        },
        'funnel_conversion': {
            'sal_disc_demo':  {'pct': sal_disc_demo_pct, 'num': sal_demo_fit,  'den': sal_sol_align},
            'aec_disc_demo':  {'pct': aec_disc_demo_pct, 'num': aec_demo_perf, 'den': aec_disc_call},
            'aec_demo_roi':   {'pct': aec_demo_roi_pct,  'num': aec_roi_call,  'den': aec_demo_perf},
        },
        'pipeline_created': {
            'total': round(pipeline_created, 2),
            'sal':   round(sal_pipeline, 2),
            'aec':   round(aec_pipeline, 2),
        },
        'qual_pipeline': {
            'total': round(qual_pipeline, 2),
            'sal':   round(qual_sal_pipeline, 2),
            'aec':   round(qual_aec_pipeline, 2),
        },
        'expansion_next_180': round(expansion_next_180, 2),
        'win_rates': {
            'overall': {'rate': overall_wr, 'won': overall_won, 'lost': overall_lost, 'total': overall_total},
            'sal':     {'rate': sal_wr,     'won': sal_won,     'lost': sal_lost,     'total': sal_total},
            'aec':     {'rate': aec_wr,     'won': aec_won,     'lost': aec_lost,     'total': aec_total},
        },
        'acv': {
            'overall': {'value': acv_overall, 'count': len(new_logo_amounts)},
            'sal':     {'value': acv_sal,     'count': len(sal_amounts)},
            'aec':     {'value': acv_aec,     'count': len(aec_amounts)},
        }
    }


# ── Save to database ───────────────────────────────────────────────────────────

def _auto_snapshot_previous_quarter(db, current_quarter, current_year):
    """Snapshot the previous quarter if it hasn't been locked yet."""
    prev_map = {
        'Q1': ('Q4', current_year - 1),
        'Q2': ('Q1', current_year),
        'Q3': ('Q2', current_year),
        'Q4': ('Q3', current_year),
    }
    prev_q, prev_y = prev_map[current_quarter]

    if db.is_quarter_locked(prev_q, prev_y):
        return  # Already snapshotted

    # Only snapshot if there's data for the previous quarter
    try:
        count = db.snapshot_quarter(prev_q, prev_y)
        print(f"\n  Auto-snapshotted {prev_q} {prev_y} ({count} KPIs locked for historical tracking)")
    except ValueError:
        pass  # No data for previous quarter — nothing to snapshot


def save_kpis_to_db(kpis, quarter="Q1", year=2026):
    """Save calculated KPIs to database"""

    db = get_db()
    today = date.today()

    # Check if this quarter is locked
    if db.is_quarter_locked(quarter, year):
        print(f"\n  {quarter} {year} is locked (snapshotted). Skipping all updates.")
        return 0

    # Auto-snapshot previous quarter if not already done
    _auto_snapshot_previous_quarter(db, quarter, year)

    # Load targets from config/targets.yaml — single source of truth
    _targets_path = Path(__file__).parent.parent / 'config' / 'targets.yaml'
    with open(_targets_path) as _f:
        _all_targets = yaml.safe_load(_f)
    targets = _all_targets.get(quarter, {}).get('hubspot_kpis', {})

    kpi_entries = []

    def entry(name, owner, cadence, actual, target, source, comments):
        variance_pct, status, emoji = calculate_variance(actual, target)
        return {
            'kpi_name':    name,
            'owner':       owner,
            'cadence':     cadence,
            'quarter':     quarter,
            'year':        year,
            'date':        today,
            'target_value': str(target),
            'actual_value': str(actual),
            'status':      status,
            'variance_pct': variance_pct,
            'source':      source,
            'comments':    comments,
            'updated_by':  'HubSpot Sync',
        }

    nl_forecast_str   = f"${kpis['new_logo_arr_forecast']['value']:,.0f}"
    exp_forecast_str  = f"${kpis['expansion_arr_forecast']['value']:,.0f}"
    total_arr_actual  = round(
        kpis['new_logo_arr_forecast']['value'] + kpis['expansion_arr_forecast']['value'], 2
    )

    kpi_entries += [
        entry('Total New ARR Forecast', 'Sales', 'Monthly',
              total_arr_actual, targets['Total New ARR Forecast'],
              'HubSpot',
              f"NL Forecast: {nl_forecast_str} + Exp Forecast: {exp_forecast_str}"),

        entry('New Logo ARR', 'Sales', 'Monthly',
              kpis['new_logo_arr']['value'], targets['New Logo ARR'],
              'HubSpot',
              f"Forecast: {nl_forecast_str} | "
              f"{kpis['new_logo_arr']['count']} closed deals: {', '.join(kpis['new_logo_arr']['deals'])}"),

        entry('Expansion ARR', 'CS', 'Monthly',
              kpis['expansion_arr']['value'], targets['Expansion ARR'],
              'HubSpot',
              f"Forecast: {exp_forecast_str} | "
              f"{kpis['expansion_arr']['count']} expansion deals: {', '.join(kpis['expansion_arr']['deals'])}"),

        entry('SQL', 'Sales', 'Monthly',
              kpis['sqls']['total'], targets['SQL'],
              'HubSpot',
              f"Inbound: {kpis['sqls']['inbound']}, Outbound: {kpis['sqls']['outbound']} | "
              f"Forecast: {kpis['sqls']['forecast']} SQLs "
              f"({kpis['sqls']['days_elapsed']}/{kpis['sqls']['days_total']} days)"),

        entry('New Logo Pipeline Created', 'Sales', 'Weekly',
              kpis['pipeline_created']['total'], targets['New Logo Pipeline Created'],
              'HubSpot', f"New deals created in {quarter}"),

        entry('SAL New Created', 'Sales', 'Weekly',
              kpis['pipeline_created']['sal'], '',
              'HubSpot', f"New SAL pipeline created in {quarter} (staffing/accounting/legal)"),

        entry('AEC New Created', 'Sales', 'Weekly',
              kpis['pipeline_created']['aec'], '',
              'HubSpot', f"New AEC pipeline created in {quarter} (architecture/engineering/construction)"),

        entry('Current Qtr Qualified Pipeline', 'Sales', 'Weekly',
              kpis['qual_pipeline']['total'], targets['Current Qtr Qualified Pipeline'],
              'HubSpot', f"Open New Logo deals closing in {quarter}"),

        entry('SAL Pipeline', 'Sales', 'Weekly',
              kpis['qual_pipeline']['sal'], '',
              'HubSpot', f"Open SAL deals closing in {quarter}"),

        entry('AEC Pipeline', 'Sales', 'Weekly',
              kpis['qual_pipeline']['aec'], '',
              'HubSpot', f"Open AEC deals closing in {quarter}"),

        entry('Expansion Pipeline (Next 180 Days)', 'CS', 'Monthly',
              kpis['expansion_next_180'], targets['Expansion Pipeline (Next 180 Days)'],
              'HubSpot', f"Open Expansion deals closing within 180 days"),

        entry('Win Rate (Overall)', 'Sales', 'Monthly',
              f"{kpis['win_rates']['overall']['rate']}%", targets['Win Rate (Overall)'],
              'HubSpot', f"Won: {kpis['win_rates']['overall']['won']}, Lost: {kpis['win_rates']['overall']['lost']}"),

        entry('Win Rate (SAL)', 'Sales', 'Monthly',
              f"{kpis['win_rates']['sal']['rate']}%", targets['Win Rate (SAL)'],
              'HubSpot', f"Won: {kpis['win_rates']['sal']['won']}, Lost: {kpis['win_rates']['sal']['lost']}"),

        entry('Win Rate (AEC)', 'Sales', 'Monthly',
              f"{kpis['win_rates']['aec']['rate']}%", targets['Win Rate (AEC)'],
              'HubSpot', f"Won: {kpis['win_rates']['aec']['won']}, Lost: {kpis['win_rates']['aec']['lost']}"),

        entry('ACV (Overall)', 'Sales', 'Monthly',
              kpis['acv']['overall']['value'], targets['ACV (Overall)'],
              'HubSpot', f"Median deal size ({kpis['acv']['overall']['count']} deals)"),

        entry('ACV (SAL)', 'Sales', 'Monthly',
              kpis['acv']['sal']['value'], targets['ACV (SAL)'],
              'HubSpot', f"Median deal size SAL ({kpis['acv']['sal']['count']} deals)"),

        entry('ACV (AEC)', 'Sales', 'Monthly',
              kpis['acv']['aec']['value'], targets['ACV (AEC)'],
              'HubSpot', f"Median deal size AEC ({kpis['acv']['aec']['count']} deals)"),

        # ── S&M Efficiency KPIs (auto-populated from HubSpot) ─────────────
        entry('SM_SAL_Win_Rate', 'S&M Initiative', 'Monthly',
              f"{kpis['win_rates']['sal']['rate']}%", '20%',
              'HubSpot', f"Won: {kpis['win_rates']['sal']['won']}, Lost: {kpis['win_rates']['sal']['lost']}"),

        entry('SM_AEC_Win_Rate', 'S&M Initiative', 'Monthly',
              f"{kpis['win_rates']['aec']['rate']}%", '25%',
              'HubSpot', f"Won: {kpis['win_rates']['aec']['won']}, Lost: {kpis['win_rates']['aec']['lost']}"),

        entry('SM_SAL_Pipeline_ARR', 'S&M Initiative', 'Weekly',
              kpis['pipeline_created']['sal'], '600000',
              'HubSpot', f"SAL new pipeline created in {quarter}"),

        entry('SM_AEC_Pipeline_ARR', 'S&M Initiative', 'Weekly',
              kpis['pipeline_created']['aec'], '1600000',
              'HubSpot', f"AEC new pipeline created in {quarter}"),

        entry('SM_SAL_Bookings', 'S&M Initiative', 'Monthly',
              kpis['bookings']['sal'], '180000',
              'HubSpot', f"SAL closed won new logo ARR in {quarter}"),

        entry('SM_AEC_Bookings', 'S&M Initiative', 'Monthly',
              kpis['bookings']['aec'], '292000',
              'HubSpot', f"AEC closed won new logo ARR in {quarter}"),

        entry('SM_SAL_SQL_Volume', 'S&M Initiative', 'Weekly',
              kpis['sqls']['sal'], '67',
              'HubSpot', f"SAL marketing-attributed SQLs in {quarter}"),

        entry('SM_AEC_SQL_Volume', 'S&M Initiative', 'Weekly',
              kpis['sqls']['aec'], '57',
              'HubSpot', f"AEC marketing-attributed SQLs in {quarter}"),

        entry('SM_SAL_SQL_Total', 'S&M Initiative', 'Weekly',
              kpis['sqls']['sal_total'], '',
              'HubSpot', f"SAL total SQLs (all sources) in {quarter}"),

        entry('SM_AEC_SQL_Total', 'S&M Initiative', 'Weekly',
              kpis['sqls']['aec_total'], '',
              'HubSpot', f"AEC total SQLs (all sources) in {quarter}"),

        entry('SM_SAL_SQL_SalesDriven', 'S&M Initiative', 'Weekly',
              kpis['sqls']['sal_sales'], '',
              'HubSpot', f"SAL sales-driven SQLs in {quarter}"),

        entry('SM_AEC_SQL_SalesDriven', 'S&M Initiative', 'Weekly',
              kpis['sqls']['aec_sales'], '',
              'HubSpot', f"AEC sales-driven SQLs in {quarter}"),

        entry('SM_SAL_SQL_CSMDriven', 'S&M Initiative', 'Weekly',
              kpis['sqls']['sal_csm'], '',
              'HubSpot', f"SAL CSM-driven SQLs in {quarter}"),

        entry('SM_AEC_SQL_CSMDriven', 'S&M Initiative', 'Weekly',
              kpis['sqls']['aec_csm'], '',
              'HubSpot', f"AEC CSM-driven SQLs in {quarter}"),

        entry('SM_SAL_Disc_Demo', 'S&M Initiative', 'Monthly',
              f"{kpis['funnel_conversion']['sal_disc_demo']['pct']}%", '45%',
              'HubSpot',
              f"SAL Solution Alignment→Demo/Fit: {kpis['funnel_conversion']['sal_disc_demo']['num']}/{kpis['funnel_conversion']['sal_disc_demo']['den']} deals"),

        entry('SM_AEC_Disc_Demo', 'S&M Initiative', 'Monthly',
              f"{kpis['funnel_conversion']['aec_disc_demo']['pct']}%", '45%',
              'HubSpot',
              f"AEC Discovery Call→Demo Performed: {kpis['funnel_conversion']['aec_disc_demo']['num']}/{kpis['funnel_conversion']['aec_disc_demo']['den']} deals"),

        entry('SM_AEC_Demo_ROI', 'S&M Initiative', 'Monthly',
              f"{kpis['funnel_conversion']['aec_demo_roi']['pct']}%", '70%',
              'HubSpot',
              f"AEC Demo Performed→ROI Call: {kpis['funnel_conversion']['aec_demo_roi']['num']}/{kpis['funnel_conversion']['aec_demo_roi']['den']} deals"),
    ]

    saved_count   = 0
    skipped_count = 0
    for kpi_data in kpi_entries:
        try:
            result = db.save_kpi_if_changed(kpi_data)
            if result:
                saved_count += 1
            else:
                skipped_count += 1
                print(f"  — {kpi_data['kpi_name']}: unchanged, skipped")
        except Exception as e:
            print(f"  ✗ Error saving {kpi_data['kpi_name']}: {e}")

    print(f"\n✅ Saved {saved_count} KPIs to database ({skipped_count} unchanged, skipped)")
    return saved_count


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python process_hubspot_data.py <deals_data.json> [quarter] [year]")
        sys.exit(1)

    deals_file = sys.argv[1]
    quarter    = sys.argv[2] if len(sys.argv) > 2 else 'Q1'
    year       = int(sys.argv[3]) if len(sys.argv) > 3 else 2026

    with open(deals_file, 'r') as f:
        deals_data = json.load(f)

    print(f"Processing {len(deals_data)} deals for {quarter} {year}...")

    kpis = process_hubspot_deals(deals_data, quarter, year)

    print("\n=== CALCULATED KPIs ===")
    print(f"New Logo ARR:      ${kpis['new_logo_arr']['value']:>12,.2f}  ({kpis['new_logo_arr']['count']} deals)")
    if kpis['new_logo_arr']['deals']:
        for d in kpis['new_logo_arr']['deals']:
            print(f"                     {d}")
    print(f"NL ARR Forecast:   ${kpis['new_logo_arr_forecast']['value']:>12,.2f}  (probability-weighted)")
    print(f"Expansion ARR:     ${kpis['expansion_arr']['value']:>12,.2f}  ({kpis['expansion_arr']['count']} deals)")
    if kpis['expansion_arr']['deals']:
        for d in kpis['expansion_arr']['deals']:
            print(f"                     {d}")
    print(f"Exp ARR Forecast:  ${kpis['expansion_arr_forecast']['value']:>12,.2f}  (probability-weighted)")
    print(f"SQLs (Total):      {kpis['sqls']['total']:>13}  (Inbound: {kpis['sqls']['inbound']}, Outbound: {kpis['sqls']['outbound']})")
    print(f"SQLs Forecast:     {kpis['sqls']['forecast']:>13}  ({kpis['sqls']['days_elapsed']}/{kpis['sqls']['days_total']} days elapsed)")
    print(f"Pipeline Created:  ${kpis['pipeline_created']['total']:>12,.2f}")
    print(f"Win Rate (Overall): {kpis['win_rates']['overall']['rate']:>11.1f}%  ({kpis['win_rates']['overall']['won']}/{kpis['win_rates']['overall']['total']})")
    print(f"Win Rate (SAL):     {kpis['win_rates']['sal']['rate']:>11.1f}%  ({kpis['win_rates']['sal']['won']}/{kpis['win_rates']['sal']['total']})")
    print(f"Win Rate (AEC):     {kpis['win_rates']['aec']['rate']:>11.1f}%  ({kpis['win_rates']['aec']['won']}/{kpis['win_rates']['aec']['total']})")
    print(f"ACV (Overall):     ${kpis['acv']['overall']['value']:>12,.0f}  ({kpis['acv']['overall']['count']} deals)")
    print(f"ACV (SAL):         ${kpis['acv']['sal']['value']:>12,.0f}  ({kpis['acv']['sal']['count']} deals)")
    print(f"ACV (AEC):         ${kpis['acv']['aec']['value']:>12,.0f}  ({kpis['acv']['aec']['count']} deals)")

    save_kpis_to_db(kpis, quarter, year)
