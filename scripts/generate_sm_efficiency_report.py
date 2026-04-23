#!/usr/bin/env python3
"""
S&M Efficiency Weekly Report Generator

Creates a Google Doc matching the S&M Efficiency PDF format, with pace-adjusted
targets and auto-generated key takeaways. Run each Wednesday before the team review.

Usage:
  python generate_sm_efficiency_report.py            # fetch fresh HubSpot data + generate
  python generate_sm_efficiency_report.py --skip-sync  # skip HubSpot fetch, use DB as-is
"""

import os
import sys
import json
import subprocess
import argparse
import time
import re
from datetime import date, datetime
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CREDS_PATH  = PROJECT_DIR.parent.parent / "credentials" / "gdrive_token.json"
DB_PATH     = PROJECT_DIR / "database" / "kpi_dashboard.db"
ENV_PATH    = PROJECT_DIR / ".env"

# Drive folder: S&M Efficiency
DRIVE_FOLDER = "1TJDJIZFcnhrrd419gkTdPfbgDuwljLmy"

# ── Quarter constants ────────────────────────────────────────────────────────────
QUARTER     = "Q2"
YEAR        = 2026
Q2_START    = date(2026, 4, 1)
Q2_END      = date(2026, 6, 30)
Q2_DAYS     = 91

# ── Metrics that compare vs FULL-quarter target (not pace-adjusted) ─────────────
RATE_METRICS = {
    "SM_ICP_MQL_Share",
    "SM_SAL_MQL_SAL", "SM_AEC_MQL_SAL",
    "SM_SAL_SAL_SQL", "SM_AEC_SAL_SQL",
    "SM_SAL_MQL_SQL", "SM_AEC_MQL_SQL",
    "SM_SAL_Disc_Demo", "SM_AEC_Disc_Demo",
    "SM_SAL_Win_Rate", "SM_AEC_Win_Rate",
}

# ── Report layout: (display_label, kpi_name, is_rate, footnote_marker) ──────────
MQL_SECTION = [
    ("ICP MQL Share (overall)",  "SM_ICP_MQL_Share",   True,  "*"),
    ("SAL ICP MQL Volume",       "SM_SAL_MQL_Volume",  False, ""),
    ("AEC ICP MQL Volume",       "SM_AEC_MQL_Volume",  False, ""),
]

SAL_SECTION = [
    ("MQL → SAL Acceptance",         "SM_SAL_MQL_SAL",     True,  "*"),
    ("SAL → SQL (Mkt-attributed)",    "SM_SAL_SAL_SQL",     True,  "*"),
    ("MQL → SQL",                     "SM_SAL_MQL_SQL",     True,  "*"),
    ("Marketing SQLs",                "SM_SAL_SQL_Volume",  False, ""),
    ("Total SQLs (all sources)",      "SM_SAL_SQL_Total",   False, ""),
    ("Solution Alignment → Demo",     "SM_SAL_Disc_Demo",   True,  "*"),
    ("Win Rate",                      "SM_SAL_Win_Rate",    True,  "*"),
    ("New Pipeline Created",          "SM_SAL_Pipeline_ARR",False, ""),
    ("Bookings (Closed Won ARR)",     "SM_SAL_Bookings",    False, ""),
]

AEC_SECTION = [
    ("MQL → SAL Acceptance",         "SM_AEC_MQL_SAL",     True,  "*"),
    ("SAL → SQL (Mkt-attributed)",    "SM_AEC_SAL_SQL",     True,  "*"),
    ("MQL → SQL",                     "SM_AEC_MQL_SQL",     True,  "*"),
    ("Marketing SQLs",                "SM_AEC_SQL_Volume",  False, ""),
    ("Total SQLs (all sources)",      "SM_AEC_SQL_Total",   False, ""),
    ("Win Rate",                      "SM_AEC_Win_Rate",    True,  "*"),
    ("New Pipeline Created",          "SM_AEC_Pipeline_ARR",False, ""),
    ("Bookings (Closed Won ARR)",     "SM_AEC_Bookings",    False, ""),
]

# ── Colors ───────────────────────────────────────────────────────────────────────
CR_GREEN     = {"red": 15/255,  "green": 125/255, "blue": 100/255}
WHITE        = {"red": 1.0,    "green": 1.0,     "blue": 1.0}
NEAR_BLACK   = {"red": 0.12,   "green": 0.12,    "blue": 0.12}
GRAY_LIGHT   = {"red": 0.97,   "green": 0.97,    "blue": 0.97}
BG_ON_TRACK  = {"red": 0.878,  "green": 0.969,   "blue": 0.898}
BG_AT_RISK   = {"red": 1.0,    "green": 0.949,   "blue": 0.800}
BG_BEHIND    = {"red": 1.0,    "green": 0.878,   "blue": 0.878}
BG_NONE      = {"red": 1.0,    "green": 1.0,     "blue": 1.0}


# ── Helper: parse numeric value from DB string ────────────────────────────────
def parse_val(s: str | None) -> float | None:
    if not s:
        return None
    s = s.strip().replace("$", "").replace(",", "").replace(" ", "")
    if s.endswith("%"):
        try:
            return float(s[:-1])
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def fmt_actual(kpi_name: str, val: float | None) -> str:
    if val is None:
        return "—"
    if kpi_name in RATE_METRICS:
        return f"{val:.1f}%"
    if "Pipeline" in kpi_name or "Bookings" in kpi_name or "ARR" in kpi_name:
        return f"${val:,.0f}"
    return f"{val:,.0f}"


def fmt_target(kpi_name: str, target: float | None) -> str:
    if target is None:
        return "—"
    if kpi_name in RATE_METRICS:
        return f"{target:.1f}%"
    if "Pipeline" in kpi_name or "Bookings" in kpi_name or "ARR" in kpi_name:
        return f"${target:,.0f}"
    return f"{target:,.0f}"


# ── Pace logic ────────────────────────────────────────────────────────────────
def days_elapsed() -> int:
    today = date.today()
    if today < Q2_START:
        return 0
    if today > Q2_END:
        return Q2_DAYS
    return (today - Q2_START).days + 1


def pace_pct() -> float:
    return days_elapsed() / Q2_DAYS


def pace_target_val(full_target: float, kpi_name: str) -> float:
    if kpi_name in RATE_METRICS:
        return full_target  # rate metrics: compare against full target
    return full_target * pace_pct()


def pct_to_target(actual: float, target: float) -> float:
    if target == 0:
        return 0.0
    return (actual / target) * 100


def status_label(pct: float) -> str:
    if pct >= 80:
        return "✓ On Track"
    if pct >= 60:
        return "~ At Risk"
    return "✗ Behind"


def status_bg(pct: float) -> dict:
    if pct >= 80:
        return BG_ON_TRACK
    if pct >= 60:
        return BG_AT_RISK
    return BG_BEHIND


# ── Step 1: HubSpot sync ──────────────────────────────────────────────────────
def run_hubspot_sync():
    print("→ Fetching fresh HubSpot data...")
    q_lower = QUARTER.lower()
    cmds = [
        [sys.executable, str(SCRIPT_DIR / "fetch_hubspot_deals.py"), QUARTER, str(YEAR)],
        [sys.executable, str(SCRIPT_DIR / "fetch_hubspot_mqls.py"),  QUARTER, str(YEAR)],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=str(PROJECT_DIR), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  WARNING: {cmd[1]} failed: {result.stderr[:200]}")
        else:
            print(f"  ✓ {Path(cmd[1]).name}")

    process_cmds = [
        [sys.executable, str(SCRIPT_DIR / "process_hubspot_data.py"),
         f"hubspot_deals_{q_lower}_{YEAR}.json", QUARTER, str(YEAR)],
        [sys.executable, str(SCRIPT_DIR / "process_hubspot_mqls.py"),
         f"hubspot_mqls_{q_lower}_{YEAR}.json",  QUARTER, str(YEAR)],
    ]
    for cmd in process_cmds:
        result = subprocess.run(cmd, cwd=str(PROJECT_DIR), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  WARNING: {cmd[1]} failed: {result.stderr[:200]}")
        else:
            print(f"  ✓ {Path(cmd[1]).name}")
    print()


# ── Step 2: Read KPIs from DB ─────────────────────────────────────────────────
def load_kpis() -> dict[str, dict]:
    """Return {kpi_name: {actual, target}} using latest row for each SM_ metric."""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Latest actual per SM_ metric for this quarter
    rows = conn.execute("""
        SELECT kpi_name, actual_value, target_value
        FROM kpis
        WHERE quarter = ? AND year = ? AND kpi_name LIKE 'SM_%'
        ORDER BY created_at DESC
    """, (QUARTER, YEAR)).fetchall()

    data: dict[str, dict] = {}
    for row in rows:
        name = row["kpi_name"]
        if name not in data:
            data[name] = {
                "actual":  parse_val(row["actual_value"]),
                "target":  parse_val(row["target_value"]),
            }

    # Also check targets table for any missing targets
    target_col = f"q{QUARTER[1].lower()}_target"
    target_rows = conn.execute(f"""
        SELECT kpi_name, {target_col} as tgt
        FROM targets
        WHERE kpi_name LIKE 'SM_%'
    """).fetchall()
    for row in target_rows:
        name = row["kpi_name"]
        if name not in data:
            data[name] = {"actual": None, "target": parse_val(row["tgt"])}
        elif data[name]["target"] is None:
            data[name]["target"] = parse_val(row["tgt"])

    conn.close()
    return data


# ── Step 3: Build row data ─────────────────────────────────────────────────────
def build_section(section_def: list, kpis: dict) -> list[dict]:
    rows = []
    for label, kpi_name, is_rate, footnote in section_def:
        kpi = kpis.get(kpi_name, {})
        actual = kpi.get("actual")
        full_target = kpi.get("target")

        if full_target is not None:
            ptgt = pace_target_val(full_target, kpi_name)
            pct  = pct_to_target(actual or 0, ptgt) if ptgt else None
        else:
            ptgt = None
            pct  = None

        rows.append({
            "label":      label + footnote,
            "kpi_name":   kpi_name,
            "actual_str": fmt_actual(kpi_name, actual),
            "pace_str":   fmt_target(kpi_name, ptgt) + (" *" if is_rate and footnote == "*" else ""),
            "pct_str":    f"{pct:.0f}%" if pct is not None else "—",
            "status_str": status_label(pct) if pct is not None else "—",
            "status_bg":  status_bg(pct) if pct is not None else BG_NONE,
            "pct":        pct,
            "actual":     actual,
            "full_target": full_target,
            "is_rate":    is_rate,
        })
    return rows


# ── Step 4: Auto-generate key takeaways ───────────────────────────────────────
def generate_takeaways(mql_rows: list, sal_rows: list, aec_rows: list) -> list[str]:
    takeaways = []
    by_label = {}
    for row in mql_rows + sal_rows + aec_rows:
        by_label[row["kpi_name"]] = row

    def get(kpi): return by_label.get(kpi, {})

    # SAL pipeline
    sal_pipe = get("SM_SAL_Pipeline_ARR")
    if sal_pipe.get("pct") and sal_pipe["pct"] >= 150:
        takeaways.append(
            f"SAL pipeline ahead of pace. {sal_pipe['actual_str']} created vs. "
            f"{sal_pipe['pace_str'].rstrip(' *')} pace target ({sal_pipe['pct_str']}). "
            "Funnel conversion is the constraint — MQL→SAL acceptance needs attention."
        )

    # AEC funnel health
    aec_pipe = get("SM_AEC_Pipeline_ARR")
    aec_mql  = get("SM_AEC_MQL_Volume")
    if aec_pipe.get("pct") and aec_pipe["pct"] < 60:
        root = "insufficient MQL volume" if (aec_mql.get("pct") or 100) < 70 else "conversion drop-off"
        takeaways.append(
            f"AEC is behind at every stage. Pipeline at {aec_pipe['pct_str']} of pace. "
            f"Root cause appears to be {root}, not the other way around."
        )

    # Bookings early in quarter
    sal_book = get("SM_SAL_Bookings")
    if sal_book.get("actual") is not None and sal_book["actual"] < 30000:
        takeaways.append(
            f"Bookings are early-stage. Q2 closings typically land May–June. "
            f"{sal_book['actual_str']} SAL closed so far — not yet a signal."
        )

    # ICP share
    icp = get("SM_ICP_MQL_Share")
    if icp.get("actual") and icp["actual"] < 80:
        gap = 90 - icp["actual"]
        takeaways.append(
            f"ICP MQL share needs attention. {icp['actual_str']} vs. 90% target — "
            f"{gap:.1f}pt gap. Non-ICP MQLs dilute the full funnel and waste BDR capacity."
        )

    # MQL→SAL acceptance rate
    sal_accept = get("SM_SAL_MQL_SAL")
    if sal_accept.get("actual") and sal_accept["actual"] < 30:
        takeaways.append(
            f"SAL MQL→SAL acceptance ({sal_accept['actual_str']}) is the primary conversion bottleneck. "
            f"Target is 55%. This cascades to every downstream SAL metric."
        )

    # Win rate
    sal_wr = get("SM_SAL_Win_Rate")
    aec_wr = get("SM_AEC_Win_Rate")
    wr_issues = []
    if sal_wr.get("actual") and sal_wr["actual"] < sal_wr.get("full_target", 20) * 0.7:
        wr_issues.append(f"SAL {sal_wr['actual_str']}")
    if aec_wr.get("actual") and aec_wr["actual"] < aec_wr.get("full_target", 25) * 0.7:
        wr_issues.append(f"AEC {aec_wr['actual_str']}")
    if wr_issues:
        takeaways.append(
            f"Win rate below threshold: {', '.join(wr_issues)}. "
            "Review deal review cadence and sales stage discipline."
        )

    if not takeaways:
        takeaways.append("Metrics are broadly on pace. Continue monitoring conversion rates weekly.")

    return takeaways


# ── Step 5: Google Docs creation ──────────────────────────────────────────────
def get_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials.from_authorized_user_file(str(CREDS_PATH))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(str(CREDS_PATH), "w") as f:
            f.write(creds.to_json())
    return creds


def _batch(docs, doc_id, reqs, chunk=40, delay=0.4):
    for i in range(0, len(reqs), chunk):
        docs.documents().batchUpdate(documentId=doc_id, body={"requests": reqs[i:i+chunk]}).execute()
        time.sleep(delay)


def _get_paragraphs(doc: dict) -> list[tuple[str, int, int]]:
    """Return (text, startIndex, endIndex) for every paragraph in the doc body (not inside tables)."""
    result = []
    for elem in doc.get("body", {}).get("content", []):
        if "paragraph" in elem:
            text = "".join(
                e.get("textRun", {}).get("content", "")
                for e in elem["paragraph"].get("elements", [])
            )
            result.append((text.rstrip("\n"), elem["startIndex"], elem["endIndex"]))
    return result


def _get_tables(doc: dict) -> list[dict]:
    return [e for e in doc.get("body", {}).get("content", []) if "table" in e]


def _insert_and_populate_table(docs, doc_id, marker: str, data_rows: list[list[str]]) -> dict:
    """
    Find the paragraph containing `marker`, delete its text, insert a real table there,
    populate all cells (bottom-to-top to avoid index drift), and return the table element.
    """
    # Find marker
    doc = docs.documents().get(documentId=doc_id).execute()
    paras = _get_paragraphs(doc)
    mp = next((p for p in paras if p[0] == marker), None)
    if mp is None:
        raise RuntimeError(f"Marker '{marker}' not found in document")

    m_start, m_end = mp[1], mp[2]

    # Delete marker text (leave the paragraph's trailing \n intact)
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
        {"deleteContentRange": {"range": {"startIndex": m_start, "endIndex": m_start + len(marker)}}}
    ]}).execute()
    time.sleep(0.3)

    # Insert table at the now-empty paragraph's position
    num_rows = len(data_rows)
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
        {"insertTable": {"rows": num_rows, "columns": 5, "location": {"index": m_start}}}
    ]}).execute()
    time.sleep(0.8)

    # Re-read and find the new table (nearest to m_start)
    doc = docs.documents().get(documentId=doc_id).execute()
    tables = _get_tables(doc)
    table_elem = min(tables, key=lambda t: abs(t["startIndex"] - m_start))

    # Collect (cell_start_index, text) pairs for all cells
    cell_ops: list[tuple[int, str]] = []
    tbl_rows = table_elem["table"]["tableRows"]
    for ri, trow in enumerate(tbl_rows):
        for ci, tcell in enumerate(trow["tableCells"]):
            val = data_rows[ri][ci] if ri < len(data_rows) and ci < len(data_rows[ri]) else ""
            if val:
                cell_ops.append((tcell["startIndex"] + 1, val))

    # Insert text bottom-to-top (descending index) so earlier cells aren't shifted
    cell_ops.sort(key=lambda x: x[0], reverse=True)
    insert_reqs = [
        {"insertText": {"location": {"index": idx}, "text": txt}}
        for idx, txt in cell_ops
    ]
    _batch(docs, doc_id, insert_reqs, chunk=30, delay=0.4)

    # Re-read to get updated cell indices for formatting
    doc = docs.documents().get(documentId=doc_id).execute()
    tables = _get_tables(doc)
    return min(tables, key=lambda t: abs(t["startIndex"] - m_start))


def _format_table(docs, doc_id, table_elem: dict, data_rows: list[dict]):
    """Apply header background, alternating rows, and status-colored text."""
    STATUS_COLOR = {
        "✓ On Track": CR_GREEN,
        "~ At Risk":  {"red": 0.87, "green": 0.55, "blue": 0.0},
        "✗ Behind":   {"red": 0.80, "green": 0.10, "blue": 0.10},
    }
    tbl_start = table_elem["startIndex"]
    reqs = []

    for ri, trow in enumerate(table_elem["table"]["tableRows"]):
        is_header = (ri == 0)
        bg = CR_GREEN if is_header else (GRAY_LIGHT if ri % 2 == 0 else WHITE)

        for ci, tcell in enumerate(trow["tableCells"]):
            # Cell background
            reqs.append({"updateTableCellStyle": {
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": tbl_start},
                        "rowIndex": ri, "columnIndex": ci,
                    },
                    "rowSpan": 1, "columnSpan": 1,
                },
                "tableCellStyle": {
                    "backgroundColor": {"color": {"rgbColor": bg}},
                    "paddingTop":    {"magnitude": 4, "unit": "PT"},
                    "paddingBottom": {"magnitude": 4, "unit": "PT"},
                    "paddingLeft":   {"magnitude": 6, "unit": "PT"},
                    "paddingRight":  {"magnitude": 6, "unit": "PT"},
                },
                "fields": "backgroundColor,paddingTop,paddingBottom,paddingLeft,paddingRight",
            }})

            # Text formatting within the cell
            for para_elem in tcell.get("content", []):
                if "paragraph" not in para_elem:
                    continue
                p_start = para_elem["startIndex"]
                p_end   = para_elem["endIndex"] - 1  # exclude trailing \n
                if p_end <= p_start:
                    continue

                text_color = WHITE if is_header else NEAR_BLACK

                # Status column (col 4) in data rows: use status color
                if not is_header and ci == 4 and (ri - 1) < len(data_rows):
                    sc = STATUS_COLOR.get(data_rows[ri - 1]["status_str"])
                    if sc:
                        text_color = sc

                reqs.append({"updateTextStyle": {
                    "range": {"startIndex": p_start, "endIndex": p_end},
                    "textStyle": {
                        "weightedFontFamily": {"fontFamily": "Arial", "weight": 700 if (is_header or ci == 4) else 400},
                        "fontSize": {"magnitude": 10, "unit": "PT"},
                        "bold": is_header or (not is_header and ci == 4),
                        "foregroundColor": {"color": {"rgbColor": text_color}},
                    },
                    "fields": "weightedFontFamily,fontSize,bold,foregroundColor",
                }})

    _batch(docs, doc_id, reqs, chunk=30, delay=0.5)


def create_google_doc(title: str, mql_rows: list, sal_rows: list,
                      aec_rows: list, takeaways: list) -> str:
    from googleapiclient.discovery import build

    creds = get_creds()
    docs  = build("docs",  "v1", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    today    = date.today()
    elapsed  = days_elapsed()
    pct_done = int(pace_pct() * 100)
    subtitle = f"Week of {today.strftime('%b %-d')}  ·  {elapsed} of {Q2_DAYS} days elapsed ({pct_done}%)"
    preamble = (
        f"Volume and pipeline metrics are compared against pace-adjusted targets "
        f"(full-quarter target \u00d7 {pct_done}%). Conversion rate metrics (win rate, funnel %) "
        "always compare against the full-quarter target."
    )
    footnote = "* Rate metrics compare against full-quarter target, not pace-adjusted."

    MQL_MARKER = "~~MQL_TABLE~~"
    SAL_MARKER = "~~SAL_TABLE~~"
    AEC_MARKER = "~~AEC_TABLE~~"

    # ── 1. Create doc, insert text skeleton ──────────────────────────────────
    doc = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    drive.files().update(
        fileId=doc_id, addParents=DRIVE_FOLDER, removeParents="root", fields="id"
    ).execute()

    skeleton = (
        f"{title}\n"
        f"{subtitle}\n"
        f"{preamble}\n"
        "\n"
        "MQL Quality\n"
        f"{MQL_MARKER}\n"
        f"{footnote}\n"
        "\n"
        "SAL Funnel\n"
        f"{SAL_MARKER}\n"
        f"{footnote}\n"
        "\n"
        "AEC Funnel\n"
        f"{AEC_MARKER}\n"
        f"{footnote}\n"
        "\n"
        "Key Takeaways\n"
        + "".join(f"{t}\n" for t in takeaways)
    )
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
        {"insertText": {"location": {"index": 1}, "text": skeleton}}
    ]}).execute()
    time.sleep(0.5)

    # ── 2. Insert tables bottom-to-top (AEC → SAL → MQL) ─────────────────────
    HEADERS = ["Metric", "Actual", "Pace Target", "% to Pace", "Status"]

    def make_matrix(rows):
        return [HEADERS] + [
            [r["label"], r["actual_str"], r["pace_str"], r["pct_str"], r["status_str"]]
            for r in rows
        ]

    print("  → Inserting AEC table...")
    aec_tbl = _insert_and_populate_table(docs, doc_id, AEC_MARKER, make_matrix(aec_rows))
    print("  → Inserting SAL table...")
    sal_tbl = _insert_and_populate_table(docs, doc_id, SAL_MARKER, make_matrix(sal_rows))
    print("  → Inserting MQL table...")
    mql_tbl = _insert_and_populate_table(docs, doc_id, MQL_MARKER, make_matrix(mql_rows))

    # ── 3. Format tables (re-read for fresh indices after all insertions) ────────
    print("  → Formatting tables...")
    doc_fresh = docs.documents().get(documentId=doc_id).execute()
    fresh_tables = _get_tables(doc_fresh)  # document order: MQL, SAL, AEC
    if len(fresh_tables) == 3:
        _format_table(docs, doc_id, fresh_tables[0], mql_rows)
        _format_table(docs, doc_id, fresh_tables[1], sal_rows)
        _format_table(docs, doc_id, fresh_tables[2], aec_rows)
    else:
        print(f"  WARNING: expected 3 tables, got {len(fresh_tables)} — skipping table formatting")

    # ── 4. Format text (re-read for fresh indices) ────────────────────────────
    print("  → Formatting text...")
    doc   = docs.documents().get(documentId=doc_id).execute()
    paras = _get_paragraphs(doc)
    body_end = doc["body"]["content"][-1]["endIndex"]

    def find_para(needle):
        return next((p for p in paras if p[0].startswith(needle[:30])), None)

    def rng(p):
        return {"startIndex": p[1], "endIndex": p[2] - 1}  # exclude \n

    fmt = []

    # Global Arial
    fmt.append({"updateTextStyle": {
        "range": {"startIndex": 1, "endIndex": body_end - 1},
        "textStyle": {"weightedFontFamily": {"fontFamily": "Arial", "weight": 400}},
        "fields": "weightedFontFamily",
    }})

    # Title
    tp = find_para(title[:30])
    if tp:
        fmt.append({"updateTextStyle": {
            "range": rng(tp),
            "textStyle": {
                "weightedFontFamily": {"fontFamily": "Arial", "weight": 700},
                "fontSize": {"magnitude": 24, "unit": "PT"},
                "bold": True,
                "foregroundColor": {"color": {"rgbColor": CR_GREEN}},
            },
            "fields": "weightedFontFamily,fontSize,bold,foregroundColor",
        }})
        fmt.append({"updateParagraphStyle": {
            "range": rng(tp),
            "paragraphStyle": {"spaceBelow": {"magnitude": 2, "unit": "PT"}},
            "fields": "spaceBelow",
        }})

    # Subtitle
    sp = find_para("Week of")
    if sp:
        fmt.append({"updateTextStyle": {
            "range": rng(sp),
            "textStyle": {
                "italic": True,
                "fontSize": {"magnitude": 11, "unit": "PT"},
                "foregroundColor": {"color": {"rgbColor": {"red": 0.45, "green": 0.45, "blue": 0.45}}},
            },
            "fields": "italic,fontSize,foregroundColor",
        }})

    # Section headers
    for hdr in ["MQL Quality", "SAL Funnel", "AEC Funnel", "Key Takeaways"]:
        hp = find_para(hdr)
        if hp:
            fmt.append({"updateTextStyle": {
                "range": rng(hp),
                "textStyle": {
                    "weightedFontFamily": {"fontFamily": "Arial", "weight": 700},
                    "fontSize": {"magnitude": 14, "unit": "PT"},
                    "bold": True,
                    "foregroundColor": {"color": {"rgbColor": CR_GREEN}},
                },
                "fields": "weightedFontFamily,fontSize,bold,foregroundColor",
            }})
            fmt.append({"updateParagraphStyle": {
                "range": rng(hp),
                "paragraphStyle": {
                    "spaceAbove": {"magnitude": 14, "unit": "PT"},
                    "spaceBelow": {"magnitude": 4, "unit": "PT"},
                },
                "fields": "spaceAbove,spaceBelow",
            }})

    # Preamble + footnotes
    for p in paras:
        if p[0].startswith("Volume and pipeline") or p[0].startswith("* Rate metrics"):
            fmt.append({"updateTextStyle": {
                "range": rng(p),
                "textStyle": {
                    "italic": True,
                    "fontSize": {"magnitude": 9, "unit": "PT"},
                    "foregroundColor": {"color": {"rgbColor": {"red": 0.5, "green": 0.5, "blue": 0.5}}},
                },
                "fields": "italic,fontSize,foregroundColor",
            }})

    # Bullet text size (bullets are plain text at this point, matched by content)
    takeaway_set = set(takeaways)
    bullet_paras = [p for p in paras if p[0].strip() in takeaway_set]
    for p in bullet_paras:
        fmt.append({"updateTextStyle": {
            "range": rng(p),
            "textStyle": {"fontSize": {"magnitude": 11, "unit": "PT"}},
            "fields": "fontSize",
        }})

    _batch(docs, doc_id, fmt, chunk=50, delay=0.4)

    # Apply proper Google Doc list bullets to takeaway paragraphs
    if bullet_paras:
        bullet_reqs = [{"createParagraphBullets": {
            "range": {"startIndex": p[1], "endIndex": p[2]},
            "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
        }} for p in bullet_paras]
        _batch(docs, doc_id, bullet_reqs, chunk=20, delay=0.4)

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return url


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate S&M Efficiency Weekly Report")
    parser.add_argument("--skip-sync", action="store_true", help="Skip HubSpot fetch")
    args = parser.parse_args()

    today = date.today()
    title = f"S&M Efficiency — {QUARTER} {YEAR}  |  Week of {today.strftime('%b %-d')}"

    if not args.skip_sync:
        run_hubspot_sync()

    print("→ Loading KPI data from database...")
    kpis = load_kpis()
    print(f"  ✓ {len(kpis)} SM metrics loaded\n")

    elapsed = days_elapsed()
    pct_done = int(pace_pct() * 100)
    print(f"→ Q2 pace: {elapsed}/{Q2_DAYS} days elapsed ({pct_done}%)\n")

    mql_rows = build_section(MQL_SECTION, kpis)
    sal_rows = build_section(SAL_SECTION, kpis)
    aec_rows = build_section(AEC_SECTION, kpis)

    takeaways = generate_takeaways(mql_rows, sal_rows, aec_rows)

    print("→ Creating Google Doc...")
    url = create_google_doc(title, mql_rows, sal_rows, aec_rows, takeaways)

    print(f"\n✓ Report ready: {url}\n")

    # Write URL to a local file for cron job pickup
    out_file = PROJECT_DIR / "reports" / f"sm_efficiency_{today.isoformat()}.txt"
    out_file.parent.mkdir(exist_ok=True)
    out_file.write_text(url)

    return url


if __name__ == "__main__":
    main()
