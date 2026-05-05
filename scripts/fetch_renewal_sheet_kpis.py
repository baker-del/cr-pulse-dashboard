"""
Fetch KPIs from the ClearlyRated Renewal Analysis Google Sheet
and save them to the database.

Auth modes (set SHEET_PUBLIC below):
  True  → Sheet is "Anyone with the link can view" — no credentials needed
  False → Requires google_credentials.json service account file

To find the GID: open the sheet, look at the URL after "gid="

Usage:
    python scripts/fetch_renewal_sheet_kpis.py [quarter] [year]
    e.g. python scripts/fetch_renewal_sheet_kpis.py Q1 2026
"""

import io
import os
import sys
from pathlib import Path
from datetime import date

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db
from utils.kpi_calculator import calculate_variance, is_inverse_kpi

SPREADSHEET_ID = os.getenv("RENEWAL_SPREADSHEET_ID", "").strip()
WORKSHEET_NAME = "Retention Analysis"   # actual tab name
SHEET_GID      = 1991609223
SHEET_PUBLIC   = False

CREDENTIALS_FILE = Path(__file__).parent.parent / "google_credentials.json"
TARGETS_FILE     = Path(__file__).parent.parent / "config" / "targets.yaml"


def _load_retention_targets(quarter: str) -> dict:
    """Load GRR/NRR targets from targets.yaml for the given quarter."""
    try:
        with open(TARGETS_FILE) as f:
            cfg = yaml.safe_load(f)
        return cfg.get(quarter, {}).get("retention_kpis", {})
    except Exception:
        return {}


# Sheet layout (first tab — Retention Risk Analysis-Feb2026):
#   H2  = Implied Logo Retention (%)   H3  = Implied GRR (%)
#   D24 = # high-risk accounts (very high, next 6 months)
#   D35 = High Risk Account ARR (Next 6 Months) + ARR at Risk - All Product Issues
#   Risk reasons rows 41-52 (counts):
#     D42 = Low surveys, D47 = Product, D48 = Support, D49 = Response rate

# (cell_address, kpi_name, owner, cadence) — targets loaded dynamically from targets.yaml
CELL_KPI_MAP_BASE = [
    ("H2",  "Logo Retention",                        "CS", "Monthly"),
    ("H3",  "GRR",                                   "CS", "Monthly"),
    ("D35", "High Risk Account ARR (Next 6 Months)", "CS", "Monthly"),
    ("D35", "ARR at Risk - All Product Issues",      "CS", "Monthly"),
    ("D24", "High Risk Accounts (Next 6 Months)",    "CS", "Monthly"),
    ("D42", "Account Risk - Low Surveys Sent",       "CS", "Monthly"),
    ("D47", "Account Risk - Product Issues",         "CS", "Monthly"),
    ("D48", "Account Risk - Support Issues",         "CS", "Monthly"),
    ("D49", "Account Risk - Response Rate Issues",   "CS", "Monthly"),
]

# Fallback targets if not in targets.yaml
DEFAULT_TARGETS = {
    "Logo Retention": "95%",
    "GRR":            "90%",
}

ARR_RISK_KPI_NAME = "ARR at Risk - All Product Issues"  # kept for reference


def _col_idx(col_str: str) -> int:
    """Convert column letter(s) like 'H' or 'AB' to 0-based index."""
    idx = 0
    for c in col_str.upper():
        idx = idx * 26 + (ord(c) - ord('A') + 1)
    return idx - 1


def _cell_idx(addr: str):
    """Return (row_idx, col_idx) 0-based from address like 'H2'."""
    col_str = ''.join(c for c in addr if c.isalpha())
    row_str = ''.join(c for c in addr if c.isdigit())
    return int(row_str) - 1, _col_idx(col_str)


def _get_sheet_df() -> pd.DataFrame:
    """Return the sheet as a DataFrame."""
    if SHEET_PUBLIC:
        url = (
            f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
            f"/export?format=csv&gid={SHEET_GID}"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code == 403:
            raise PermissionError(
                "Sheet returned 403. Set sharing to 'Anyone with the link can view'."
            )
        resp.raise_for_status()
        return pd.read_csv(io.StringIO(resp.text), header=None, dtype=str).fillna('')
    else:
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
        creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=scopes)
        gc    = gspread.authorize(creds)
        ws    = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        data  = ws.get_all_values()
        return pd.DataFrame(data, dtype=str).fillna('')


def _cell_value(df: pd.DataFrame, addr: str) -> str:
    r, c = _cell_idx(addr)
    try:
        return str(df.iloc[r, c]).strip()
    except (IndexError, KeyError):
        return ''


def fetch_values(quarter: str = "Q1", year: int = 2026) -> int:
    mode = "public CSV" if SHEET_PUBLIC else "service account"
    print(f"Connecting to renewal sheet ({SPREADSHEET_ID}) via {mode}...")
    df    = _get_sheet_df()
    print(f"  Sheet loaded: {len(df)} rows × {len(df.columns)} cols")

    db    = get_db()
    today = date.today()
    saved = 0

    retention_targets = _load_retention_targets(quarter)

    cell_kpi_map = [
        (addr, name, owner, retention_targets.get(name, DEFAULT_TARGETS.get(name, "")), cadence)
        for addr, name, owner, cadence in CELL_KPI_MAP_BASE
    ]

    for cell_addr, kpi_name, owner, target, cadence in cell_kpi_map:
        raw = _cell_value(df, cell_addr)
        if not raw:
            print(f"  SKIP  {kpi_name}: cell {cell_addr} is empty")
            continue

        actual = raw
        vp, status, _ = calculate_variance(
            actual, target,
            is_inverse=is_inverse_kpi(kpi_name),
        )

        result = db.save_kpi_if_changed({
            'kpi_name':     kpi_name,
            'owner':        owner,
            'cadence':      cadence,
            'quarter':      quarter,
            'year':         year,
            'date':         today,
            'target_value': target,
            'actual_value': actual,
            'status':       status or '',
            'variance_pct': vp,
            'source':       'Google Sheets',
            'comments':     '',
            'updated_by':   'Auto-Sync',
        })
        if result:
            print(f"  Saved {kpi_name}: {actual}")
            saved += 1
        else:
            print(f"  — {kpi_name}: unchanged, skipped")

    # ── Renewal ARR risk = (1 - H3) where H3 = GRR ────────────────────────────
    h3_raw = _cell_value(df, "H3")
    if h3_raw:
        try:
            h3_val = float(h3_raw.replace('%', '').replace(',', '').strip())
            if h3_val > 1:
                h3_val = h3_val / 100.0
            arr_risk_pct = (1.0 - h3_val) * 100
            actual_arr_risk = f"{arr_risk_pct:.1f}%"
            vp, status, _ = calculate_variance(actual_arr_risk, "<10%", is_inverse=True)
            result = db.save_kpi_if_changed({
                'kpi_name':     'Renewal ARR risk (Next 180 days)',
                'owner':        'CS',
                'cadence':      'Monthly',
                'quarter':      quarter,
                'year':         year,
                'date':         today,
                'target_value': '<10%',
                'actual_value': actual_arr_risk,
                'status':       status or '',
                'variance_pct': vp,
                'source':       'Google Sheets',
                'comments':     f'1 - GRR (H3 = {h3_raw})',
                'updated_by':   'Auto-Sync',
            })
            if result:
                print(f"  Saved Renewal ARR risk (Next 180 days): {actual_arr_risk}")
                saved += 1
            else:
                print(f"  — Renewal ARR risk (Next 180 days): unchanged, skipped")
        except (ValueError, TypeError) as exc:
            print(f"  SKIP  Renewal ARR risk: could not parse H3 '{h3_raw}': {exc}")
    else:
        print("  SKIP  Renewal ARR risk: H3 (GRR) is empty")

    # ── Renewal Logo Risk = (1 - H2) where H2 = Logo Retention ────────────────
    h2_raw = _cell_value(df, "H2")
    if h2_raw:
        try:
            h2_val = float(h2_raw.replace('%', '').replace(',', '').strip())
            if h2_val > 1:
                h2_val = h2_val / 100.0
            logo_risk_pct = (1.0 - h2_val) * 100
            actual_logo_risk = f"{logo_risk_pct:.1f}%"
            vp, status, _ = calculate_variance(actual_logo_risk, "10%", is_inverse=True)
            result = db.save_kpi_if_changed({
                'kpi_name':     'Renewal Logo Risk (Next 180 days)',
                'owner':        'CS',
                'cadence':      'Monthly',
                'quarter':      quarter,
                'year':         year,
                'date':         today,
                'target_value': '10%',
                'actual_value': actual_logo_risk,
                'status':       status or '',
                'variance_pct': vp,
                'source':       'Google Sheets',
                'comments':     f'1 - Logo Retention (H2 = {h2_raw})',
                'updated_by':   'Auto-Sync',
            })
            if result:
                print(f"  Saved Renewal Logo Risk (Next 180 days): {actual_logo_risk}")
                saved += 1
            else:
                print(f"  — Renewal Logo Risk (Next 180 days): unchanged, skipped")
        except (ValueError, TypeError) as exc:
            print(f"  SKIP  Renewal Logo Risk: could not parse H2 '{h2_raw}': {exc}")
    else:
        print("  SKIP  Renewal Logo Risk: H2 (Logo Retention) is empty")

    print(f"\nDone: {saved} KPIs saved from renewal analysis sheet.")
    return saved


if __name__ == '__main__':
    q = sys.argv[1] if len(sys.argv) > 1 else "Q1"
    y = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    fetch_values(q, y)
