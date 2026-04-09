#!/usr/bin/env python3
"""
Compute weekly funnel cohort rows from HubSpot JSON files and save to DB.

Usage:
    python scripts/process_weekly_cohorts.py [quarter] [year]
    python scripts/process_weekly_cohorts.py Q2 2026

Reads:
    hubspot_mqls_{q}_{year}.json   — MQL contacts
    hubspot_deals_{q}_{year}.json  — Deals

Saves to DB:
    weekly_cohorts table (SAL + AEC rows)

Run this after:
    python scripts/fetch_hubspot_mqls.py Q2 2026
    python scripts/fetch_hubspot_deals.py Q2 2026
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pages._sm_cohort_loader import load_weekly_cohorts_from_files
from database.db import get_db


def main():
    quarter = sys.argv[1].upper() if len(sys.argv) > 1 else 'Q2'
    year    = int(sys.argv[2])    if len(sys.argv) > 2 else 2026

    print(f"\nProcessing weekly cohorts for {quarter} {year}...")

    data = load_weekly_cohorts_from_files(quarter, year, ROOT)
    if data is None:
        print("ERROR: JSON source files not found. Run fetch scripts first.")
        sys.exit(1)

    db = get_db()
    db.create_tables()

    for vertical in ('SAL', 'AEC'):
        rows = data[vertical.lower()]
        db.save_weekly_cohorts(rows, quarter, year, vertical)
        print(f"  ✓ {vertical}: {len(rows)} weeks saved")

    print(f"\n✅ Weekly cohorts saved to DB for {quarter} {year}")


if __name__ == '__main__':
    main()
