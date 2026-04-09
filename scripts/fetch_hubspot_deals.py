#!/usr/bin/env python3
"""
Fetch HubSpot deal data for KPI dashboard processing.

Usage:
    python scripts/fetch_hubspot_deals.py [quarter] [year]
    python scripts/fetch_hubspot_deals.py Q2 2026

Requires HUBSPOT_API_KEY in the project .env file.

Implements the 4-group filter strategy from process_hubspot_data.py:
  Group 1 — Deals closing in target quarter
  Group 2 — Deals closing in next quarter (for forecast coverage)
  Group 3 — Deals created in target quarter (for SQLs/pipeline)
  Group 4 — Open Expansion deals closing within 180 days

Output: hubspot_deals_{q}_{year}.json  (same format as process_hubspot_data.py expects)
"""

import json
import os
import sys
import time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / '.env')

HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY', '')
SEARCH_URL = 'https://api.hubapi.com/crm/v3/objects/deals/search'

PROPERTIES = [
    'dealname',
    'dealstage',
    'pipeline',
    'amount',
    'dealtype',
    'closedate',
    'createdate',
    'demo_discovery_status',
    'sales_outbound_vs_inbound',
    'deal_source_bucket',             # Marketing Driven / Sales Driven / CSM Driven
    'hs_deal_stage_probability',
    'company_industry_dropdown',
    # Stage entry dates — used for funnel conversion rate calculations
    'hs_v2_date_entered_qualifiedtobuy',          # SAL: Solution Alignment (Sales Pipeline)
    'hs_v2_date_entered_decisionmakerboughtin',   # SAL: Demo / Fit (Sales Pipeline)
    'hs_v2_date_entered_1102698286',              # AEC: Discovery Call (ClientSavvy Pipeline)
    'hs_v2_date_entered_1102698287',              # AEC: Demo Performed (ClientSavvy Pipeline)
    'hs_v2_date_entered_1102698288',              # AEC: ROI Call Completed (ClientSavvy Pipeline)
]

NEW_LOGO_PIPELINES = ['default', '757781604']
EXPANSION_PIPELINE = '47062345'
ALL_PIPELINES = NEW_LOGO_PIPELINES + [EXPANSION_PIPELINE]

QUARTER_RANGES = {
    'Q1': ((1, 1), (3, 31)),
    'Q2': ((4, 1), (6, 30)),
    'Q3': ((7, 1), (9, 30)),
    'Q4': ((10, 1), (12, 31)),
}
NEXT_QUARTER = {'Q1': 'Q2', 'Q2': 'Q3', 'Q3': 'Q4', 'Q4': 'Q1'}


def _quarter_bounds(quarter: str, year: int):
    (sm, sd), (em, ed) = QUARTER_RANGES[quarter]
    start = datetime(year, sm, sd, 0, 0, 0, tzinfo=timezone.utc)
    end   = datetime(year, em, ed, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _ts(dt: datetime) -> str:
    """ISO timestamp HubSpot filter expects (milliseconds epoch as string)."""
    return str(int(dt.timestamp() * 1000))


def _build_filter_groups(quarter: str, year: int):
    q_start, q_end = _quarter_bounds(quarter, year)

    nq = NEXT_QUARTER[quarter]
    nq_year = year + 1 if nq == 'Q1' else year
    nq_start, nq_end = _quarter_bounds(nq, nq_year)

    today_utc = datetime.now(tz=timezone.utc)
    next_180  = today_utc + timedelta(days=180)

    pipeline_filter = {
        'propertyName': 'pipeline',
        'operator': 'IN',
        'values': ALL_PIPELINES,
    }
    new_logo_pipeline_filter = {
        'propertyName': 'pipeline',
        'operator': 'IN',
        'values': NEW_LOGO_PIPELINES,
    }
    expansion_pipeline_filter = {
        'propertyName': 'pipeline',
        'operator': 'EQ',
        'value': EXPANSION_PIPELINE,
    }

    # Group 1 — closing in target quarter
    group1 = {'filters': [
        {'propertyName': 'closedate', 'operator': 'GTE', 'value': _ts(q_start)},
        {'propertyName': 'closedate', 'operator': 'LTE', 'value': _ts(q_end)},
        pipeline_filter,
    ]}

    # Group 2 — closing in next quarter (forecast coverage)
    group2 = {'filters': [
        {'propertyName': 'closedate', 'operator': 'GTE', 'value': _ts(nq_start)},
        {'propertyName': 'closedate', 'operator': 'LTE', 'value': _ts(nq_end)},
        pipeline_filter,
    ]}

    # Group 3 — created in target quarter (SQLs + pipeline created)
    group3 = {'filters': [
        {'propertyName': 'createdate', 'operator': 'GTE', 'value': _ts(q_start)},
        {'propertyName': 'createdate', 'operator': 'LTE', 'value': _ts(q_end)},
        new_logo_pipeline_filter,
    ]}

    # Group 4 — open Expansion deals closing within 180 days
    group4 = {'filters': [
        expansion_pipeline_filter,
        {'propertyName': 'closedate', 'operator': 'GTE', 'value': _ts(today_utc)},
        {'propertyName': 'closedate', 'operator': 'LTE', 'value': _ts(next_180)},
    ]}

    return [group1, group2, group3, group4]


def fetch_all_deals(quarter: str, year: int) -> list:
    if not HUBSPOT_API_KEY:
        print("ERROR: HUBSPOT_API_KEY not found in .env")
        print("Add this to your .env file:  HUBSPOT_API_KEY=pat-na1-xxxxxxxx")
        sys.exit(1)

    # Private app tokens start with "pat-"; HAPI keys are plain UUIDs
    is_private_app = HUBSPOT_API_KEY.startswith('pat-')
    headers = {'Content-Type': 'application/json'}
    if is_private_app:
        headers['Authorization'] = f'Bearer {HUBSPOT_API_KEY}'

    filter_groups = _build_filter_groups(quarter, year)
    all_deals = {}   # keyed by id to deduplicate across groups
    page_size = 200

    for g_idx, group in enumerate(filter_groups, 1):
        offset = 0
        page   = 1
        print(f"  Group {g_idx}: fetching...", end='', flush=True)

        while True:
            payload = {
                'filterGroups': [group],
                'properties': PROPERTIES,
                'limit': page_size,
                'after': offset if offset else None,
            }
            # Remove 'after': None — HubSpot rejects it
            if payload['after'] is None:
                del payload['after']

            url = SEARCH_URL if is_private_app else f'{SEARCH_URL}?hapikey={HUBSPOT_API_KEY}'
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            results = data.get('results', [])
            for deal in results:
                all_deals[deal['id']] = {
                    'id':         deal['id'],
                    'properties': {p: deal['properties'].get(p, '') for p in PROPERTIES},
                }

            paging = data.get('paging', {})
            next_page = paging.get('next', {})
            after_cursor = next_page.get('after')

            print(f" {len(results)} deals (page {page})", end='', flush=True)

            if not after_cursor or len(results) < page_size:
                break

            offset = after_cursor
            page  += 1
            time.sleep(0.1)   # be gentle with rate limits

        print()

    return list(all_deals.values())


def main():
    quarter = sys.argv[1].upper() if len(sys.argv) > 1 else 'Q2'
    year    = int(sys.argv[2])    if len(sys.argv) > 2 else 2026

    print(f"\nFetching HubSpot deals for {quarter} {year}...")
    print(f"Strategy: 4-group OR filter (closing in {quarter}, closing in next Q, created in {quarter}, expansion 180d)\n")

    deals = fetch_all_deals(quarter, year)

    out_file = ROOT / f'hubspot_deals_{quarter.lower()}_{year}.json'
    with open(out_file, 'w') as f:
        json.dump(deals, f, indent=2)

    print(f"\n✅ Fetched {len(deals)} unique deals → {out_file.name}")
    print(f"\nNext step:")
    print(f"  python scripts/process_hubspot_data.py {out_file.name} {quarter} {year}")


if __name__ == '__main__':
    main()
