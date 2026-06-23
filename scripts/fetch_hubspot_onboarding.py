#!/usr/bin/env python3
"""
Fetch HubSpot deals for the Customer Onboarding board.

Pulls two pipelines:
  - Sales Pipeline (default): all advanced stages (Onboarding Overview → Closed Won)
  - Expansion Pipeline (47062345): Verbal+ stages, amount > $4K only

Window: last 90 days + next 90 days from run date.

Usage:
    python scripts/fetch_hubspot_onboarding.py
Output:
    hubspot_onboarding.json  (read by pages/6_Onboarding.py)
"""

import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY", "")
SEARCH_URL = "https://api.hubapi.com/crm/v3/objects/deals/search"
OWNERS_URL = "https://api.hubapi.com/crm/v3/owners"

SALES_PIPELINE     = "default"
EXPANSION_PIPELINE = "47062345"
EXPANSION_MIN_ARR  = 4000

SALES_STAGES = {
    "266892603": "Onboarding Overview",
    "contractsent": "Vendor of Choice",
    "266892604": "Contract Executed",
    "closedwon":  "Closed Won",
    "1102698292": "Closed Won",
}

EXPANSION_STAGES = {
    "159501408": "Verbal / Out for Sig",
    "96961408":  "Contract Executed",
    "96961410":  "Closed Won",
}

PROPERTIES = [
    "dealname", "dealstage", "pipeline", "amount", "dealtype",
    "closedate", "company_industry_dropdown", "hubspot_owner_id",
    "onboarding_doc_link", "hs_onboarding_doc_link",
    "onboarding_document_link", "kickoff_doc_link", "kickoff_doc_url",
]


def headers():
    return {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}


def fetch_owners():
    resp = requests.get(OWNERS_URL, headers=headers(), params={"limit": 100}, timeout=15)
    if resp.status_code != 200:
        print(f"  ⚠ Owners fetch failed: {resp.status_code}")
        return {}
    return {
        str(o["id"]): f"{o.get('firstName', '')} {o.get('lastName', '')}".strip()
        for o in resp.json().get("results", [])
    }


def search_deals(pipeline_id, stage_ids, past, future):
    payload = {
        "filterGroups": [{"filters": [
            {"propertyName": "closedate", "operator": "GTE", "value": past},
            {"propertyName": "closedate", "operator": "LTE", "value": future},
            {"propertyName": "pipeline",  "operator": "EQ",  "value": pipeline_id},
            {"propertyName": "dealstage", "operator": "IN",  "values": list(stage_ids)},
        ]}],
        "properties": PROPERTIES,
        "limit": 200,
    }
    raw = []
    after = None
    page = 0
    while True:
        if after:
            payload["after"] = after
        resp = requests.post(SEARCH_URL, headers=headers(), json=payload, timeout=15)
        if resp.status_code != 200:
            print(f"  ✗ Search failed: {resp.status_code} — {resp.text[:200]}")
            break
        data = resp.json()
        raw.extend(data.get("results", []))
        page += 1
        paging = data.get("paging", {})
        if "next" not in paging:
            break
        after = paging["next"]["after"]
        time.sleep(0.1)
    print(f"  → {pipeline_id}: {len(raw)} raw deals ({page} page{'s' if page != 1 else ''})")
    return raw


def parse_deal(d, pipeline_label, stage_map, owners, min_arr=0):
    p     = d["properties"]
    stage = p.get("dealstage", "")
    cd    = (p.get("closedate") or "")[:10]
    if not cd:
        return None
    arr = float(p.get("amount") or 0)
    if arr <= min_arr:
        return None
    owner_id = str(p.get("hubspot_owner_id") or "")
    dt = p.get("dealtype") or ""
    onboard_doc = (
        p.get("onboarding_doc_link") or p.get("hs_onboarding_doc_link")
        or p.get("onboarding_document_link") or p.get("kickoff_doc_link")
        or p.get("kickoff_doc_url") or ""
    )
    closedate = datetime.strptime(cd, "%Y-%m-%d").date()
    return {
        "id":          d["id"],
        "name":        p.get("dealname") or "Unnamed",
        "arr":         arr,
        "stage":       stage,
        "stage_label": stage_map.get(stage, stage),
        "pipeline":    pipeline_label,
        "closedate":   cd,
        "month_key":   closedate.strftime("%Y-%m"),
        "month_label": closedate.strftime("%b %Y"),
        "dealtype":    (
            "New Biz"  if "new"   in dt.lower() else
            "Renewal"  if "renew" in dt.lower() else
            dt or "—"
        ),
        "vertical":    (p.get("company_industry_dropdown") or "—"),
        "ae":          owners.get(owner_id, "—"),
        "onboard_doc": onboard_doc or "",
    }


def main():
    if not HUBSPOT_API_KEY:
        print("ERROR: HUBSPOT_API_KEY not set in .env")
        sys.exit(1)

    today  = date.today()
    past   = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    future = (today + timedelta(days=90)).strftime("%Y-%m-%d")

    print(f"\nFetching onboarding deals — window: {past} → {future}")
    print("Fetching owners...")
    owners = fetch_owners()
    print(f"  {len(owners)} owners loaded")

    print("Fetching Sales Pipeline deals...")
    raw_sales = search_deals(SALES_PIPELINE, list(SALES_STAGES.keys()), past, future)

    print("Fetching Expansion Pipeline deals...")
    raw_exp = search_deals(EXPANSION_PIPELINE, list(EXPANSION_STAGES.keys()), past, future)

    seen, deals = set(), []

    for d in raw_sales:
        parsed = parse_deal(d, "New Logo", SALES_STAGES, owners)
        if parsed and d["id"] not in seen:
            seen.add(d["id"])
            deals.append(parsed)

    for d in raw_exp:
        parsed = parse_deal(d, "Expansion", EXPANSION_STAGES, owners, min_arr=EXPANSION_MIN_ARR)
        if parsed and d["id"] not in seen:
            seen.add(d["id"])
            deals.append(parsed)

    deals.sort(key=lambda x: x["closedate"])

    print(f"\n✅ {len(deals)} onboarding deals")
    for d in deals:
        print(f"  [{d['month_label']:8}] [{d['pipeline']:9}] {d['name'][:45]:45} ${d['arr']:>9,.0f}  {d['stage_label']}")

    output = {
        "fetched_at":    datetime.now().isoformat(),
        "window_start":  past,
        "window_end":    future,
        "deals":         deals,
    }

    out_path = ROOT / "hubspot_onboarding.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved → {out_path.name}")
    print("Next: git add hubspot_onboarding.json && git commit && git push")


if __name__ == "__main__":
    main()
