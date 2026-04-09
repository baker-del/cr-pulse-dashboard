#!/usr/bin/env python3
"""
Fetch HubSpot MQL contact data for KPI dashboard.

Usage:
    python scripts/fetch_hubspot_mqls.py [quarter] [year]
    python scripts/fetch_hubspot_mqls.py Q2 2026

MQL Definition:
  Contacts whose 'Date entered Marketing Qualified Lead (Lifecycle Stage Pipeline)'
  (hs_v2_date_entered_marketingqualifiedlead) falls within the target quarter,
  excluding members of "Contacts to be excluded from MQL report" segment.

Industry: CR_Industry Dropdown (industry_dropdown) on the contact.
SAL ICP = Staffing, Legal, Accounting, HR Services, RPO
AEC ICP = Architecture & Planning, Construction, Commercial Construction, Engineering

Output: hubspot_mqls_{q}_{year}.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / '.env')

HUBSPOT_API_KEY     = os.environ.get('HUBSPOT_API_KEY', '')
CONTACTS_SEARCH_URL = 'https://api.hubapi.com/crm/v3/objects/contacts/search'
LISTS_SEARCH_URL    = 'https://api.hubapi.com/contacts/v1/lists/all/contacts/all'
LISTS_URL           = 'https://api.hubapi.com/contacts/v1/lists'

# Optional: hardcode the HubSpot list ID for the exclusion segment to avoid
# the name-lookup API call every run.  Set HUBSPOT_EXCLUSION_LIST_ID in .env.
EXCLUSION_LIST_ID   = os.environ.get('HUBSPOT_EXCLUSION_LIST_ID', '')
EXCLUSION_LIST_NAME = 'Contacts to be excluded from MQL report'

CONTACT_PROPERTIES = [
    'email', 'firstname', 'lastname', 'company',
    'industry_dropdown',                          # CR_Industry Dropdown
    'lifecyclestage', 'createdate',
    'hs_v2_date_entered_marketingqualifiedlead',  # Date entered MQL stage
    'hs_v2_date_entered_opportunity',             # Date entered SAL (Sales Accepted Lead) stage
    'lead_source',
]

QUARTER_RANGES = {
    'Q1': ((1, 1),  (3, 31)),
    'Q2': ((4, 1),  (6, 30)),
    'Q3': ((7, 1),  (9, 30)),
    'Q4': ((10, 1), (12, 31)),
}

# industry_dropdown values — normalised to lowercase for matching
SAL_INDUSTRIES = {
    'staffing',
    'legal',
    'accounting',
    'hr services',
    'rpo',
}
AEC_INDUSTRIES = {
    'architecture & planning',
    'construction',
    'commercial construction',
    'engineering',
}


def _quarter_bounds(quarter: str, year: int):
    (sm, sd), (em, ed) = QUARTER_RANGES[quarter]
    start = datetime(year, sm, sd, 0, 0, 0, tzinfo=timezone.utc)
    end   = datetime(year, em, ed, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _ts(dt: datetime) -> str:
    return str(int(dt.timestamp() * 1000))


def classify_industry(raw: str) -> str:
    ind = (raw or '').lower().strip()
    if ind in SAL_INDUSTRIES:
        return 'SAL'
    if ind in AEC_INDUSTRIES:
        return 'AEC'
    return 'Other'


def _lookup_exclusion_list_id(headers: dict) -> str:
    """Find the HubSpot list ID for the exclusion segment by name."""
    try:
        offset = 0
        while True:
            resp = requests.get(
                LISTS_URL,
                headers=headers,
                params={'count': 250, 'offset': offset},
                timeout=30,
            )
            resp.raise_for_status()
            data  = resp.json()
            lists = data.get('lists', [])
            for lst in lists:
                if lst.get('name', '') == EXCLUSION_LIST_NAME:
                    lid = str(lst['listId'])
                    print(f"  Found exclusion list: '{EXCLUSION_LIST_NAME}' → ID {lid}")
                    return lid
            if not data.get('has-more'):
                break
            offset += len(lists)
        print(f"  ⚠️  Exclusion list '{EXCLUSION_LIST_NAME}' not found — skipping exclusion filter")
    except Exception as e:
        print(f"  ⚠️  Could not look up exclusion list: {e}")
    return ''


def _load_exclusion_ids(headers: dict, list_id: str) -> set:
    """Fetch all contact IDs from the exclusion segment list."""
    excluded = set()
    offset = 0
    print(f"  Loading exclusion list {list_id}...", end='', flush=True)
    while True:
        resp = requests.get(
            f'https://api.hubapi.com/contacts/v1/lists/{list_id}/contacts/all',
            headers=headers,
            params={'count': 100, 'vidOffset': offset, 'property': 'vid'},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for c in data.get('contacts', []):
            excluded.add(str(c['vid']))
        if not data.get('has-more'):
            break
        offset = data.get('vid-offset')
        time.sleep(0.05)
    print(f" {len(excluded)} contacts")
    return excluded


def _build_filter_group(ts_start: str, ts_end: str) -> dict:
    return {'filters': [
        {
            'propertyName': 'hs_v2_date_entered_marketingqualifiedlead',
            'operator': 'GTE',
            'value': ts_start,
        },
        {
            'propertyName': 'hs_v2_date_entered_marketingqualifiedlead',
            'operator': 'LTE',
            'value': ts_end,
        },
    ]}


def _fetch_page(headers, filter_group, page_size=100, after=None):
    payload = {
        'filterGroups': [filter_group],
        'properties':   CONTACT_PROPERTIES,
        'limit':        page_size,
    }
    if after:
        payload['after'] = after
    resp = requests.post(CONTACTS_SEARCH_URL, headers=headers,
                         json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_mqls(quarter: str, year: int) -> list:
    if not HUBSPOT_API_KEY:
        print("ERROR: HUBSPOT_API_KEY not found in .env")
        sys.exit(1)

    headers = {
        'Content-Type':  'application/json',
        'Authorization': f'Bearer {HUBSPOT_API_KEY}',
    }

    # Load exclusion list
    excl_list_id = EXCLUSION_LIST_ID or _lookup_exclusion_list_id(headers)
    excluded_ids = _load_exclusion_ids(headers, excl_list_id) if excl_list_id else set()

    q_start, q_end = _quarter_bounds(quarter, year)
    ts_start, ts_end = _ts(q_start), _ts(q_end)
    filter_group = _build_filter_group(ts_start, ts_end)

    print(f"  Fetching MQLs for {quarter} {year}...")

    contacts = {}
    after = None
    page  = 1

    while True:
        data    = _fetch_page(headers, filter_group, after=after)
        results = data.get('results', [])
        for c in results:
            if c['id'] not in excluded_ids:
                contacts[c['id']] = {
                    'id':         c['id'],
                    'properties': {p: c['properties'].get(p) or ''
                                   for p in CONTACT_PROPERTIES},
                }
        print(f"    page {page}: {len(results)} fetched, {len(contacts)} kept so far")

        after = data.get('paging', {}).get('next', {}).get('after')
        if not after or len(results) < 100:
            break
        page += 1
        time.sleep(0.1)

    return list(contacts.values())


def summarise(contacts: list) -> dict:
    total     = len(contacts)
    sal_mql   = sum(1 for c in contacts
                    if classify_industry(c['properties'].get('industry_dropdown', '')) == 'SAL')
    aec_mql   = sum(1 for c in contacts
                    if classify_industry(c['properties'].get('industry_dropdown', '')) == 'AEC')
    other     = total - sal_mql - aec_mql
    icp_pct   = round((sal_mql + aec_mql) / total * 100, 1) if total > 0 else 0
    # SAL (Sales Accepted Lead) counts — contacts who entered the SAL stage
    sal_sal   = sum(1 for c in contacts
                    if classify_industry(c['properties'].get('industry_dropdown', '')) == 'SAL'
                    and c['properties'].get('hs_v2_date_entered_opportunity', ''))
    aec_sal   = sum(1 for c in contacts
                    if classify_industry(c['properties'].get('industry_dropdown', '')) == 'AEC'
                    and c['properties'].get('hs_v2_date_entered_opportunity', ''))
    return {
        'total': total, 'sal': sal_mql, 'aec': aec_mql, 'other': other, 'icp_pct': icp_pct,
        'sal_sal': sal_sal, 'aec_sal': aec_sal,
    }


def main():
    quarter = sys.argv[1].upper() if len(sys.argv) > 1 else 'Q2'
    year    = int(sys.argv[2])    if len(sys.argv) > 2 else 2026

    print(f"\nFetching HubSpot MQLs for {quarter} {year}...")
    contacts = fetch_mqls(quarter, year)

    out_file = ROOT / f'hubspot_mqls_{quarter.lower()}_{year}.json'
    with open(out_file, 'w') as f:
        json.dump(contacts, f, indent=2)

    s = summarise(contacts)

    # Show industry_dropdown distribution for verification
    from collections import Counter
    dist = Counter(
        c['properties'].get('industry_dropdown', '(blank)') or '(blank)'
        for c in contacts
    )
    print(f"\n=== MQL SUMMARY {quarter} {year} ===")
    print(f"  Total MQLs : {s['total']:>5}")
    print(f"  SAL ICP    : {s['sal']:>5}")
    print(f"  AEC ICP    : {s['aec']:>5}")
    print(f"  Other      : {s['other']:>5}")
    print(f"  ICP %      : {s['icp_pct']:>5}%")
    print(f"\n  Industry breakdown:")
    for ind, count in dist.most_common():
        tag = f"[{classify_industry(ind)}]"
        print(f"    {ind:<35} {count:>4}  {tag}")
    print(f"\n✅ Saved → {out_file.name}")
    print(f"\nNext step:")
    print(f"  python scripts/process_hubspot_mqls.py {out_file.name} {quarter} {year}")


if __name__ == '__main__':
    main()
