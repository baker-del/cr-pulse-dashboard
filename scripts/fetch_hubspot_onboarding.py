#!/usr/bin/env python3
"""
Fetch HubSpot deals for the Customer Onboarding board.

Pulls two pipelines:
  - Sales Pipeline (default): all advanced stages (Onboarding Overview → Closed Won)
  - Expansion Pipeline (47062345): Verbal+ stages, amount > $4K only

Window: last 90 days + next 90 days from run date.

Also fetches the Onboarding pipeline (887428778) and cross-references all 2026
YTD closed-won deals to build the onboarding status table.

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
PORTAL_ID = "2787478"
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


ONBOARDING_PIPELINE = "887428778"

ONBOARDING_STAGE_MAP = {
    "1334736025": "Handoff to Onboarding",
    "1334736026": "Client Kickoff",
    "1334736027": "Onboarding Plan Completed",
    "1334736028": "Set Up Systems",
    "1334736029": "Set Up Integrations",
    "1334895633": "Training & Enablement",
    "1334895634": "Survey Launch Readiness",
    "1334736030": "Survey Launch",
    "1334736031": "Failure to Launch",
}

ONBOARDING_CATEGORY_MAP = {
    "1334736025": "Not Started",            # Handoff to Onboarding — deal exists but kickoff not done
    "1334736026": "Onboarding In Progress", # Client Kickoff
    "1334736027": "Onboarding In Progress", # Onboarding Plan Completed
    "1334736028": "Onboarding In Progress", # Set Up Systems
    "1334736029": "Onboarding In Progress", # Set Up Integrations
    "1334895633": "Onboarding In Progress", # Training & Enablement
    "1334895634": "Onboarding Complete",    # Survey Launch Readiness — fully onboarded, survey pending
    "1334736030": "Survey Launched",        # Survey Launch
    "1334736031": "Not Started",            # Failure to Launch — stuck, treat as blocked
}

CLOSED_WON_PIPELINES = {
    "default":   ["closedwon"],
    "757781604": ["1102698292"],
}
PIPELINE_LABEL = {"default": "New Logo", "47062345": "Expansion", "757781604": "ClientSavvy"}


def fetch_onboarding_status(owners: dict, today: date) -> list:
    """Cross-reference 2026 YTD closed-won deals against the onboarding pipeline."""

    # 1. Pull all deals in the onboarding pipeline
    ob_payload = {
        "filterGroups": [{"filters": [
            {"propertyName": "pipeline", "operator": "EQ", "value": ONBOARDING_PIPELINE},
        ]}],
        "properties": ["dealname", "dealstage", "amount", "closedate", "createdate", "hubspot_owner_id"],
        "limit": 200,
    }
    resp = requests.post(SEARCH_URL, headers=headers(), json=ob_payload, timeout=15)
    ob_raw = resp.json().get("results", [])
    print(f"  → Onboarding pipeline: {len(ob_raw)} deals")

    def _norm(name: str) -> str:
        return name.lower().replace(" (clone)", "").replace("-", " ").replace("  ", " ").strip()

    ob_lookup: dict = {}
    for r in ob_raw:
        p = r["properties"]
        stage_id = p.get("dealstage", "")
        ob_cd = (p.get("closedate") or "")[:10]
        nm = _norm(p.get("dealname", ""))
        owner_id = str(p.get("hubspot_owner_id") or "")
        ob_lookup[nm] = {
            "stage_id":    stage_id,
            "stage_label": ONBOARDING_STAGE_MAP.get(stage_id, stage_id),
            "category":    ONBOARDING_CATEGORY_MAP.get(stage_id, "Unknown"),
            "ob_closedate": ob_cd,
            "ob_deal_id":  r["id"],
            "csm":         owners.get(owner_id, "—"),
        }

    def _find_ob(sale_name: str):
        nm = _norm(sale_name)
        if nm in ob_lookup:
            return ob_lookup[nm]
        for key, val in ob_lookup.items():
            if nm[:25] in key or key[:25] in nm:
                return val
        return None

    # 2. Pull all 2026 closed-won deals (New Logo + significant Expansion)
    ytd_start = "2026-01-01"
    today_str = today.strftime("%Y-%m-%d")

    all_sales: list = []
    for pid, stages in CLOSED_WON_PIPELINES.items():
        payload = {
            "filterGroups": [{"filters": [
                {"propertyName": "closedate", "operator": "GTE", "value": ytd_start},
                {"propertyName": "closedate", "operator": "LTE", "value": today_str},
                {"propertyName": "pipeline",  "operator": "EQ",  "value": pid},
                {"propertyName": "dealstage", "operator": "IN",  "values": stages},
            ]}],
            "properties": [
                "dealname", "dealstage", "pipeline", "amount", "closedate",
                "hubspot_owner_id", "company_industry_dropdown",
            ],
            "limit": 200,
        }
        after = None
        while True:
            if after:
                payload["after"] = after
            resp = requests.post(SEARCH_URL, headers=headers(), json=payload, timeout=15)
            data = resp.json()
            for r in data.get("results", []):
                p = r["properties"]
                nm = p.get("dealname", "")
                arr = float(p.get("amount") or 0)
                is_price_increase = "price increase" in nm.lower()
                is_nl = pid in ("default", "757781604")
                if is_nl or (not is_price_increase and arr >= 4000):
                    all_sales.append({
                        "id":        r["id"],
                        "name":      nm,
                        "arr":       arr,
                        "pipeline":  PIPELINE_LABEL.get(pid, pid),
                        "closedate": (p.get("closedate") or "")[:10],
                        "vertical":  p.get("company_industry_dropdown") or "—",
                        "owner":     owners.get(str(p.get("hubspot_owner_id") or ""), "—"),
                        "deal_url":  f"https://app.hubspot.com/contacts/{PORTAL_ID}/deal/{r['id']}",
                    })
            paging = data.get("paging", {})
            if "next" not in paging:
                break
            after = paging["next"]["after"]
            time.sleep(0.05)

    all_sales.sort(key=lambda x: x["closedate"])
    print(f"  → YTD closed-won (NL + significant Exp): {len(all_sales)} deals")

    # Stage order for velocity context (higher = further along)
    STAGE_ORDER = {
        "1334736025": 1, "1334736026": 2, "1334736027": 3,
        "1334736028": 4, "1334736029": 5, "1334895633": 6,
        "1334895634": 7, "1334736030": 8, "1334736031": 0,
    }

    # 3. Cross-reference
    status_rows = []
    for d in all_sales:
        cd = datetime.strptime(d["closedate"], "%Y-%m-%d").date()
        ob = _find_ob(d["name"])
        if ob:
            stage_id = ob["stage_id"]
            stage_label = ob["stage_label"]
            category = ob["category"]
            ob_cd_str = ob.get("ob_closedate", "")
            csm = ob.get("csm", "—")
            if stage_id == "1334736030" and ob_cd_str:
                launch_dt = datetime.strptime(ob_cd_str, "%Y-%m-%d").date()
                days_elapsed = max((launch_dt - cd).days, 0)
            else:
                days_elapsed = (today - cd).days
            stage_order = STAGE_ORDER.get(stage_id, 0)
        else:
            stage_label = "—"
            category = "Not Started"
            days_elapsed = (today - cd).days
            stage_order = 0
            csm = "—"

        status_rows.append({
            "id":           d["id"],
            "name":         d["name"],
            "arr":          d["arr"],
            "pipeline":     d["pipeline"],
            "closedate":    d["closedate"],
            "days_elapsed": days_elapsed,
            "stage_label":  stage_label,
            "stage_order":  stage_order,
            "category":     category,
            "deal_url":     d["deal_url"],
            "vertical":     d["vertical"],
            "csm":          csm,
        })

    return status_rows


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

    print("\nFetching onboarding status cross-reference...")
    onboarding_status = fetch_onboarding_status(owners, today)
    print(f"✅ {len(onboarding_status)} customers in onboarding status table")
    for r in onboarding_status:
        print(f"  {r['closedate']} | {r['days_elapsed']:>4}d | {r['category']:<20} | {r['stage_label']:<30} | {r['name'][:50]}")

    output = {
        "fetched_at":       datetime.now().isoformat(),
        "window_start":     past,
        "window_end":       future,
        "deals":            deals,
        "onboarding_status": onboarding_status,
    }

    out_path = ROOT / "hubspot_onboarding.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved → {out_path.name}")
    print("Next: git add hubspot_onboarding.json && git commit && git push")


if __name__ == "__main__":
    main()
