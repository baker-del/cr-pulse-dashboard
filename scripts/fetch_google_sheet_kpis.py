#!/usr/bin/env python3
"""
Fetch Support & Engineering KPIs from Google Sheets

Auth modes (set SHEET_PUBLIC below):
  True  → Sheet is "Anyone with link can view" — no credentials needed
  False → Requires google_credentials.json service account file

To find the sheet GID: open the sheet, look at the URL after "gid="
"""

import io
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db
from utils.kpi_calculator import calculate_variance, is_inverse_kpi


# ── Configuration ──────────────────────────────────────────────────────────────

SPREADSHEET_ID = "1WctcSLELDztlPwZST3oZuweIKC6lI_j8YjOttufbs90"
SHEET_TAB_NAME = "KPI"   # Name of the tab inside the spreadsheet
SHEET_GID      = 0       # Tab GID (find in URL after "gid="). 0 = first tab.

# Set True if the sheet is "Anyone with link can view" — no credentials needed.
# Set False to use a service account (requires google_credentials.json).
SHEET_PUBLIC   = False

# Path to service account credentials JSON (only used when SHEET_PUBLIC = False)
CREDENTIALS_FILE = Path(__file__).parent.parent / "google_credentials.json"

# Column where date-based actuals begin (H = index 7, 0-based)
DATA_START_COL = 7  # column H

# ── KPI row mappings ───────────────────────────────────────────────────────────
# Maps the label as it appears in the Google Sheet → database KPI name
# Row label search is case-insensitive and partial-match friendly
# Optional "default_value": used when row is missing or all data cells are empty.

KPI_MAPPINGS = [
    # ── Response rates ─────────────────────────────────────────────────────────
    {
        "sheet_label":  "RR overall",                   # "Last 30 days - RR overall"
        "db_name":      "30-day Response Rate (Overall)",
        "owner":        "Engineering",
        "cadence":      "Monthly",
        "target":       "18%",
    },
    {
        "sheet_label":  "Excluding Express",            # "Last 30 days - Excluding Express"
        "db_name":      "30-day Response Rate excluding Express",
        "owner":        "Engineering",
        "cadence":      "Monthly",
        "target":       "18%",
    },

    # ── Email & survey ─────────────────────────────────────────────────────────
    {
        "sheet_label":  "Sent email",                   # "# Sent email & SMS"
        "db_name":      "Emails & SMS Sent",
        "owner":        "Engineering",
        "cadence":      "Weekly",
        "target":       "",                             # filled at runtime from B3
        "target_cell":  "B3",                          # read target from this cell + " (avg)"
    },
    {
        "sheet_label":  "MS Placement",                 # "MS Placement in inbox"
        "db_name":      "MS Placement in Box",
        "owner":        "Engineering",
        "cadence":      "Weekly",
        "target":       "97%",
    },
    {
        "sheet_label":  "Click rate",                   # "Click rate" row (before "Complete Survey" rows)
        "db_name":      "Survey Click Rate (30-day)",
        "owner":        "Engineering",
        "cadence":      "Monthly",
        "target":       "25%",
    },

    # ── Engineering / Incidents ────────────────────────────────────────────────
    {
        "sheet_label":  "AI coded",                     # "AI coded" = 99%
        "db_name":      "AI Coded %",
        "owner":        "Engineering",
        "cadence":      "Weekly",
        "target":       "95%",
    },
    {
        "sheet_label":  "P3 out of SLA",               # "P3 out of SLA (P3 Open > 30 days)" = 19
        "db_name":      "Tickets out of SLA",
        "owner":        "Engineering",
        "cadence":      "Weekly",
        "target":       "10",                           # goal <10 per sheet
    },
    {
        "sheet_label":  "Incidents",
        "db_name":      "Incidents",
        "owner":        "Engineering",
        "cadence":      "Weekly",
        "target":       "0",
        "default_value": "0",                          # default to 0 when not available
    },

    # ── Support ────────────────────────────────────────────────────────────────
    {
        "sheet_label":  "Customer tickets resolved by T1",  # "% Customer tickets resolved by T1" = 92.34%
        "db_name":      "Tickets Resolved in Tier 1 within SLA",
        "owner":        "Engineering",
        "cadence":      "Weekly",
        "target":       "90%",
    },
    {
        "sheet_label":  "Tickets Created in week",      # "Tickets Created in week"
        "db_name":      "Tickets Created (Week)",
        "owner":        "Engineering",
        "cadence":      "Weekly",
        "target":       "",
    },

    # ── Data OPS ───────────────────────────────────────────────────────────────
    {
        "sheet_label":  "Data OPS Tickets missing",     # "% Data OPS Tickets missing deadline" = 0
        "db_name":      "Data OPS Tickets missing deadline",
        "owner":        "Data OPS",
        "cadence":      "Weekly",
        "target":       "5%",
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_all_values() -> list[list[str]]:
    """Return all cell values as list-of-lists, using public CSV or service account."""
    if SHEET_PUBLIC:
        url = (
            f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
            f"/export?format=csv&gid={SHEET_GID}"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code == 403:
            raise PermissionError(
                "Sheet returned 403. Make sure sharing is set to "
                "'Anyone with the link can view'."
            )
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), header=None, dtype=str).fillna('')
        return df.values.tolist()
    else:
        # Service account auth
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"google_credentials.json not found at {CREDENTIALS_FILE}.\n"
                "Either set SHEET_PUBLIC=True or add the credentials file."
            )
        creds  = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=scopes)
        client = gspread.authorize(creds)
        spread = client.open_by_key(SPREADSHEET_ID)
        try:
            ws = spread.worksheet(SHEET_TAB_NAME)
        except gspread.WorksheetNotFound:
            ws = spread.get_worksheet(0)
            print(f"  ⚠ Tab '{SHEET_TAB_NAME}' not found, using first sheet instead.")
        return ws.get_all_values()


def _find_row(all_values: list, label: str) -> list | None:
    """Find a row whose first non-empty cell contains the label (case-insensitive)."""
    label_lower = label.lower()
    for row in all_values:
        for cell in row[:DATA_START_COL]:  # only search metadata columns
            if cell and label_lower in str(cell).lower():
                return row
    return None


def _latest_actual(row: list) -> tuple[str | None, int | None]:
    """Return (value, absolute_col_index) of the rightmost non-empty data cell.

    absolute_col_index is the 0-based column index in the full row (H onwards).
    Returns (None, None) if no data found.
    """
    data_cells = row[DATA_START_COL:]
    for i in range(len(data_cells) - 1, -1, -1):
        val = data_cells[i]
        if val and str(val).strip() not in ('', '-', 'N/A', '#N/A'):
            return str(val).strip(), DATA_START_COL + i
    return None, None


def _date_for_col(all_values: list, col_idx: int) -> date:
    """Read the date from row 1 (H1:L1) at the given column index.

    Dates are in yyyy/mm/dd format. Falls back to today if missing or unparseable.
    """
    try:
        date_str = str(all_values[0][col_idx]).strip()
        if date_str:
            return datetime.strptime(date_str, "%Y/%m/%d").date()
    except (IndexError, ValueError):
        pass
    return date.today()


def _cell_value(all_values: list, addr: str) -> str:
    """Read a specific cell by address like 'B3'."""
    col_str = ''.join(c for c in addr if c.isalpha())
    row_str = ''.join(c for c in addr if c.isdigit())
    col_idx = 0
    for c in col_str.upper():
        col_idx = col_idx * 26 + (ord(c) - ord('A') + 1)
    col_idx -= 1
    row_idx = int(row_str) - 1
    try:
        return str(all_values[row_idx][col_idx]).strip()
    except (IndexError, KeyError):
        return ''


# ── Main fetch function ────────────────────────────────────────────────────────

def fetch_google_sheet_kpis(quarter="Q1", year=2026):
    """Fetch KPIs from Google Sheet and return as a list of dicts."""
    mode = "public CSV" if SHEET_PUBLIC else "service account"
    print(f"Connecting to Google Sheet ({SPREADSHEET_ID}) via {mode}...")
    all_values = _get_all_values()
    print(f"  Sheet loaded: {len(all_values)} rows")

    results = []
    for mapping in KPI_MAPPINGS:
        row = _find_row(all_values, mapping["sheet_label"])

        # Resolve actual value and the date of the latest data column
        if row is None:
            actual     = mapping.get("default_value")
            entry_date = date.today()
            if actual is None:
                print(f"  ⚠ Row not found for: '{mapping['sheet_label']}'")
                continue
            print(f"  ⚠ Row not found for '{mapping['db_name']}', using default: {actual}")
        else:
            actual, col_idx = _latest_actual(row)
            if actual is None:
                actual = mapping.get("default_value")
                if actual is None:
                    print(f"  ⚠ No actual value for: '{mapping['db_name']}'")
                    continue
                print(f"  ⚠ No data for '{mapping['db_name']}', using default: {actual}")
                entry_date = date.today()
            else:
                entry_date = _date_for_col(all_values, col_idx)

        # Resolve target — may be a fixed string or read from a cell
        target = mapping.get("target", "")
        target_cell = mapping.get("target_cell")
        if target_cell:
            cell_val = _cell_value(all_values, target_cell)
            if cell_val:
                target = f"{cell_val} (avg)"

        results.append({
            "db_name":    mapping["db_name"],
            "owner":      mapping["owner"],
            "cadence":    mapping["cadence"],
            "target":     target,
            "actual":     actual,
            "entry_date": entry_date,
        })
        print(f"  ✓ {mapping['db_name']}: {actual}  (date: {entry_date})")

    return results


# ── Save to database ───────────────────────────────────────────────────────────

def save_sheet_kpis_to_db(results, quarter="Q1", year=2026):
    """Save fetched KPIs to the database."""
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
            "updated_by":   "Google Sheets Sync",
        }

        try:
            result = db.save_kpi_if_changed(kpi_data)
            if result:
                saved += 1
            else:
                print(f"  — {r['db_name']}: unchanged, skipped")
        except Exception as e:
            print(f"  ✗ Error saving {r['db_name']}: {e}")

    print(f"\n✅ Saved {saved} KPIs from Google Sheets (unchanged values skipped)")
    return saved


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    quarter = sys.argv[1] if len(sys.argv) > 1 else "Q1"
    year    = int(sys.argv[2]) if len(sys.argv) > 2 else 2026

    print(f"\nFetching Google Sheet KPIs for {quarter} {year}...")
    results = fetch_google_sheet_kpis(quarter, year)

    if results:
        print(f"\n=== FETCHED {len(results)} KPIs ===")
        for r in results:
            print(f"  {r['db_name']:<45} actual={r['actual']}  date={r['entry_date']}")
        save_sheet_kpis_to_db(results, quarter, year)
    else:
        print("No KPIs fetched.")
