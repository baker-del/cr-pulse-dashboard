#!/usr/bin/env python3
"""
Fetch Product KPIs from Google Sheets (KPIs 2026 tab)

Source sheet: https://docs.google.com/spreadsheets/d/1vytud5Q2p_Jn9nP-wfal5h_PgWR4TOHtMvA2vRJo4B8
Tab: KPIs 2026

KPIs fetched:
  - CFT - Monthly Active Users
  - CFT - Total Surveys Sent
  - CFT - 7-day Median Email Response Rate
  - CR - Monthly Active Users (mapped to CRS - Monthly Active Users)
  - CR - Total Surveys Sent
  - CR - Last 30 days RR excluding Express (mapped to 30-day Response Rate excluding Express)

Week dates are parsed from Row 2 (week start dates like "3 Jan", "10 Jan").
The latest non-empty column determines the actual value and updated date.
"""

import sys
from datetime import date, datetime
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db
from utils.kpi_calculator import calculate_variance, is_inverse_kpi


# ── Configuration ──────────────────────────────────────────────────────────────

SPREADSHEET_ID = "1vytud5Q2p_Jn9nP-wfal5h_PgWR4TOHtMvA2vRJo4B8"
SHEET_TAB_NAME = "KPIs 2026"
CREDENTIALS_FILE = Path(__file__).parent.parent / "google_credentials.json"

# Row indices (0-based) in the sheet
ROW_WEEK_START = 2   # Row 3: week start dates ("3 Jan", "10 Jan", ...)
ROW_KPI_START  = 5   # Row 6: first KPI row (CFT - Monthly Active Users)
DATA_START_COL = 1   # Column B: first data column

# ── KPI mappings: sheet row label → database KPI name ──────────────────────────

KPI_MAPPINGS = [
    {
        "sheet_label":  "CFT - Monthly Active Users",
        "db_name":      "CFT - Monthly Active Users",
        "owner":        "Product",
        "cadence":      "Weekly",
        "target":       "",
    },
    {
        "sheet_label":  "CFT - Total Surveys Sent",
        "db_name":      "CFT - Total Surveys Sent",
        "owner":        "Product",
        "cadence":      "Weekly",
        "target":       "",
    },
    {
        "sheet_label":  "CFT - 7-day median email respo",
        "db_name":      "CFT - 7-day Median Email Response Rate",
        "owner":        "Product",
        "cadence":      "Weekly",
        "target":       "",
    },
    {
        "sheet_label":  "CR - Monthly Active Users",
        "db_name":      "CRS - Monthly Active Users",
        "owner":        "Product",
        "cadence":      "Weekly",
        "target":       "",
    },
    {
        "sheet_label":  "CR - Total Surveys Sent",
        "db_name":      "CR - Total Surveys Sent",
        "owner":        "Product",
        "cadence":      "Weekly",
        "target":       "",
    },
    {
        "sheet_label":  "CR - Last 30 days RR - Excludi",
        "db_name":      "CR - Last 30 days RR excluding Express",
        "owner":        "Product",
        "cadence":      "Weekly",
        "target":       "",
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_all_values():
    """Fetch all values from the KPIs 2026 tab via service account."""
    creds = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    sheets = build("sheets", "v4", credentials=creds)
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_TAB_NAME}'!A1:BZ50",
    ).execute()
    return result.get("values", [])


def _find_row(all_values, label):
    """Find a row whose column A starts with the label (case-insensitive, partial match)."""
    label_lower = label.lower()
    for row in all_values:
        if row and label_lower in str(row[0]).lower():
            return row
    return None


def _parse_week_date(date_str, year=2026):
    """Parse a week start date like '3 Jan', '14 Feb', '28 Mar' into a date object."""
    date_str = date_str.strip().rstrip("*")
    for fmt in ("%d %b", "%d %B"):
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.replace(year=year).date()
        except ValueError:
            continue
    return None


def _latest_actual(row):
    """Return (value, column_index) of the rightmost non-empty data cell.

    Scans from right to left starting at DATA_START_COL.
    """
    data_cells = row[DATA_START_COL:]
    for i in range(len(data_cells) - 1, -1, -1):
        val = str(data_cells[i]).strip().rstrip("*")
        if val and val not in ("", "-", "N/A", "#N/A"):
            return val, DATA_START_COL + i
    return None, None


def _date_for_col(all_values, col_idx, year=2026):
    """Get the week start date for a given column index from row 2."""
    try:
        date_str = str(all_values[ROW_WEEK_START][col_idx]).strip()
        if date_str:
            return _parse_week_date(date_str, year)
    except (IndexError, ValueError):
        pass
    return date.today()


# ── Main fetch function ────────────────────────────────────────────────────────

def fetch_product_kpis(quarter="Q1", year=2026):
    """Fetch Product KPIs from Google Sheet and return as a list of dicts."""
    print(f"Connecting to Product KPI sheet ({SPREADSHEET_ID})...")
    all_values = _get_all_values()
    print(f"  Sheet loaded: {len(all_values)} rows")

    results = []
    for mapping in KPI_MAPPINGS:
        row = _find_row(all_values, mapping["sheet_label"])

        if row is None:
            print(f"  ⚠ Row not found for: '{mapping['sheet_label']}'")
            continue

        actual, col_idx = _latest_actual(row)
        if actual is None:
            print(f"  ⚠ No actual value for: '{mapping['db_name']}'")
            continue

        entry_date = _date_for_col(all_values, col_idx, year) or date.today()

        results.append({
            "db_name":    mapping["db_name"],
            "owner":      mapping["owner"],
            "cadence":    mapping["cadence"],
            "target":     mapping.get("target", ""),
            "actual":     actual,
            "entry_date": entry_date,
        })
        print(f"  ✓ {mapping['db_name']}: {actual}  (date: {entry_date})")

    return results


# ── Save to database ───────────────────────────────────────────────────────────

def save_product_kpis_to_db(results, quarter="Q1", year=2026):
    """Save fetched Product KPIs to the database."""
    db = get_db()
    saved = 0

    for r in results:
        variance_pct, status, _ = calculate_variance(
            r["actual"], r["target"],
            is_inverse=is_inverse_kpi(r["db_name"])
        )

        kpi_data = {
            "kpi_name":     r["db_name"],
            "owner":        r["owner"],
            "cadence":      r["cadence"],
            "quarter":      quarter,
            "year":         year,
            "date":         r["entry_date"],
            "target_value": r["target"],
            "actual_value": r["actual"],
            "status":       status or "",
            "variance_pct": variance_pct,
            "source":       "Google Sheets",
            "comments":     "",
            "updated_by":   "Product KPI Sync",
        }

        try:
            result = db.save_kpi_if_changed(kpi_data)
            if result:
                saved += 1
            else:
                print(f"  — {r['db_name']}: unchanged, skipped")
        except Exception as e:
            print(f"  ✗ Error saving {r['db_name']}: {e}")

    print(f"\n✅ Saved {saved} Product KPIs (unchanged values skipped)")
    return saved


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    quarter = sys.argv[1] if len(sys.argv) > 1 else "Q1"
    year    = int(sys.argv[2]) if len(sys.argv) > 2 else 2026

    print(f"\nFetching Product KPIs for {quarter} {year}...")
    results = fetch_product_kpis(quarter, year)

    if results:
        print(f"\n=== FETCHED {len(results)} KPIs ===")
        for r in results:
            print(f"  {r['db_name']:<45} actual={r['actual']}  date={r['entry_date']}")
        save_product_kpis_to_db(results, quarter, year)
    else:
        print("No KPIs fetched.")
