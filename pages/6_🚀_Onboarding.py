"""
CR Pulse — Customer Onboarding Board
Reads from hubspot_onboarding.json (synced locally via fetch_hubspot_onboarding.py).
Board view by close month: last 90 days + next 90 days.
"""

import json
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT            = Path(__file__).parent.parent
DATA_FILE       = ROOT / "hubspot_onboarding.json"
OVERRIDES_FILE  = ROOT / "database" / "onboarding_overrides.json"

CAT_ORDER = ["Not Started", "Onboarding In Progress", "Onboarding Complete", "Survey Launched"]


def load_overrides() -> dict:
    if OVERRIDES_FILE.exists():
        with open(OVERRIDES_FILE) as f:
            return json.load(f)
    return {}


def save_overrides(overrides: dict):
    OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OVERRIDES_FILE, "w") as f:
        json.dump(overrides, f, indent=2)

STAGE_COLORS = {
    "Onboarding Overview": {"color": "#5B21B6", "bg": "#F5F3FF", "border": "#A78BFA"},
    "Vendor of Choice":    {"color": "#92400E", "bg": "#FFFBEB", "border": "#F59E0B"},
    "Verbal / Out for Sig":{"color": "#92400E", "bg": "#FFFBEB", "border": "#F59E0B"},
    "Contract Executed":   {"color": "#1E40AF", "bg": "#EFF6FF", "border": "#3B82F6"},
    "Closed Won":          {"color": "#065F46", "bg": "#F0FDF4", "border": "#10B981"},
}

CLOSED_WON_LABEL = "Closed Won"


@st.cache_data(ttl=300)
def load_data(mtime: float):
    if not DATA_FILE.exists():
        return None, [], []
    with open(DATA_FILE) as f:
        raw = json.load(f)
    return raw.get("fetched_at", ""), raw.get("deals", []), raw.get("onboarding_status", [])


def _months_in_window(start: date, end: date):
    months, cur = [], start.replace(day=1)
    while cur <= end:
        months.append(cur)
        cur = (
            cur.replace(month=cur.month + 1)
            if cur.month < 12
            else cur.replace(year=cur.year + 1, month=1)
        )
    return months


def _card_html(deal):
    label  = deal.get("stage_label", deal.get("stage", ""))
    cfg    = STAGE_COLORS.get(label, {"color": "#374151", "bg": "#F9FAFB", "border": "#9CA3AF"})
    arr    = deal.get("arr", 0)
    arr_str = f"${arr:,.0f}" if arr else "—"
    exp_badge = (
        '<span style="font-size:9px;background:#E0E7FF;color:#3730A3;'
        'border-radius:3px;padding:1px 5px;margin-left:4px;">EXP</span>'
        if deal.get("pipeline") == "Expansion" else ""
    )
    vertical = (deal.get("vertical") or "—")[:25]
    ae       = deal.get("ae", "—")
    dealtype = deal.get("dealtype", "—")
    doc      = deal.get("onboard_doc", "")
    doc_html = (
        f'<div style="margin-top:6px;">'
        f'<a href="{doc}" target="_blank" style="color:{cfg["color"]};font-size:11px;'
        f'text-decoration:none;">📄 Onboarding Doc</a></div>'
        if doc else ""
    )
    return (
        f'<div style="background:{cfg["bg"]};border-left:4px solid {cfg["border"]};'
        f'padding:10px 12px;border-radius:6px;margin-bottom:10px;'
        f'box-shadow:0 1px 2px rgba(0,0,0,0.06);">'
        f'<div style="font-size:10px;font-weight:700;color:{cfg["color"]};'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">'
        f'{label}{exp_badge}</div>'
        f'<div style="font-weight:700;color:#111827;font-size:13px;line-height:1.3;'
        f'margin-bottom:5px;">{deal["name"]}</div>'
        f'<div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:4px;">{arr_str}</div>'
        f'<div style="font-size:11px;color:#6B7280;line-height:1.5;">'
        f'{vertical}<br>{dealtype} · {ae}</div>'
        f'{doc_html}</div>'
    )


def main():
    today        = date.today()
    window_start = today - timedelta(days=90)
    window_end   = today + timedelta(days=90)

    st.title("🚀 Customer Onboarding")

    mtime = DATA_FILE.stat().st_mtime if DATA_FILE.exists() else 0.0
    fetched_at, deals, status_rows = load_data(mtime)

    if fetched_at:
        try:
            ts = datetime.fromisoformat(fetched_at).strftime("%b %d, %Y %I:%M %p")
        except Exception:
            ts = fetched_at
        st.caption(f"Last synced: {ts} · Sales + Expansion pipelines · {window_start.strftime('%b %d')} – {window_end.strftime('%b %d, %Y')}")
    else:
        st.caption("Run `python scripts/fetch_hubspot_onboarding.py` to populate data.")

    if not deals:
        st.info("No data yet. Run the sync script locally and push.")
        return

    # ── KPI row ───────────────────────────────────────────────────────────────
    closed    = [d for d in deals if d.get("stage_label") == CLOSED_WON_LABEL]
    pipeline  = [d for d in deals if d.get("stage_label") != CLOSED_WON_LABEL]
    expansion = [d for d in deals if d.get("pipeline") == "Expansion"]
    total_arr = sum(d.get("arr", 0) for d in deals)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Deals", len(deals))
    m2.metric("Closed Won",  len(closed))
    m3.metric("In Pipeline", len(pipeline))
    m4.metric("Expansion",   len(expansion))
    m5.metric("Total ARR",   f"${total_arr:,.0f}")

    # ── Summary table: rows=stage group, columns=month ────────────────────────
    STAGE_GROUPS = [
        {
            "label":  "Onboarding Overview / Vendor of Choice",
            "stages": {"Onboarding Overview", "Vendor of Choice"},
            "color":  "#92400E", "bg": "#FFFBEB",
        },
        {
            "label":  "Verbal / Out for Sig + Contract Executed",
            "stages": {"Verbal / Out for Sig", "Contract Executed"},
            "color":  "#1E40AF", "bg": "#EFF6FF",
        },
        {
            "label":  "Closed Won",
            "stages": {"Closed Won"},
            "color":  "#065F46", "bg": "#F0FDF4",
        },
    ]

    # Build pivot: month_key → stage_label → [names]
    pivot = defaultdict(lambda: defaultdict(list))
    month_keys_seen = []
    for d in deals:
        mk    = d["month_key"]
        label = d.get("stage_label", "—")
        # Clean name: strip after " - " and truncate
        raw_name = d["name"]
        short    = raw_name.split(" - ")[0].replace("(WPG)", "").strip()
        if len(short) > 28:
            short = short[:27] + "…"
        arr      = d.get("arr", 0)
        arr_str  = f"${arr/1000:.0f}K" if arr >= 1000 else f"${arr:.0f}"
        pivot[mk][label].append(f"{short} ({arr_str})")
        if mk not in month_keys_seen:
            month_keys_seen.append(mk)
    month_keys_seen = sorted(month_keys_seen)

    def group_names(mk, group):
        names = []
        for s in group["stages"]:
            names.extend(pivot[mk][s])
        return names

    # Header: Month + one col per stage group + Total
    th = '<th style="text-align:left;padding:7px 12px;font-size:12px;border-bottom:2px solid #E5E7EB;min-width:90px;">Month</th>'
    for g in STAGE_GROUPS:
        th += (
            f'<th style="text-align:left;padding:7px 12px;font-size:12px;'
            f'border-bottom:2px solid #E5E7EB;color:{g["color"]};">{g["label"]}</th>'
        )
    th += '<th style="text-align:center;padding:7px 12px;font-size:12px;border-bottom:2px solid #E5E7EB;font-weight:700;">Total</th>'

    # Data rows — one per month
    rows_html = ""
    for mk in month_keys_seen:
        is_now  = mk == today.strftime("%Y-%m")
        is_past = mk < today.strftime("%Y-%m")
        mlabel  = datetime.strptime(mk, "%Y-%m").strftime("%b %Y")
        row_bg  = "#F0FDF4" if is_now else ("#FAFAFA" if is_past else "#FFFFFF")
        row_n   = sum(len(group_names(mk, g)) for g in STAGE_GROUPS)
        cells   = (
            f'<td style="padding:7px 12px;font-size:12px;font-weight:600;'
            f'white-space:nowrap;border-bottom:1px solid #F3F4F6;vertical-align:top;">'
            f'{"📍 " if is_now else ""}{mlabel}</td>'
        )
        for g in STAGE_GROUPS:
            names   = group_names(mk, g)
            cell_bg = g["bg"] if names else "transparent"
            if names:
                lines = "".join(
                    f'<div style="padding:1px 0;border-bottom:1px solid rgba(0,0,0,0.05);'
                    f'white-space:nowrap;">{n}</div>'
                    for n in names
                )
            else:
                lines = '<span style="color:#D1D5DB;">—</span>'
            cells += (
                f'<td style="text-align:left;padding:7px 12px;font-size:11px;'
                f'border-bottom:1px solid #F3F4F6;background:{cell_bg};vertical-align:top;">'
                f'{lines}</td>'
            )
        cells += (
            f'<td style="text-align:center;padding:7px 12px;font-size:12px;font-weight:700;'
            f'border-bottom:1px solid #F3F4F6;vertical-align:top;"><b>{row_n}</b></td>'
        )
        rows_html += f'<tr style="background:{row_bg};">{cells}</tr>'

    # Totals footer — counts only
    foot_cells = '<td style="padding:7px 12px;font-size:12px;font-weight:700;border-top:2px solid #E5E7EB;">Total</td>'
    for g in STAGE_GROUPS:
        col_n = sum(len(group_names(mk, g)) for mk in month_keys_seen)
        foot_cells += (
            f'<td style="text-align:center;padding:7px 12px;font-size:12px;font-weight:700;'
            f'border-top:2px solid #E5E7EB;"><b>{col_n}</b></td>'
        )
    foot_cells += (
        f'<td style="text-align:center;padding:7px 12px;font-size:12px;font-weight:700;'
        f'border-top:2px solid #E5E7EB;"><b>{len(deals)}</b></td>'
    )

    table_html = (
        '<div style="overflow-x:auto;margin:16px 0 4px 0;">'
        '<table style="border-collapse:collapse;width:100%;background:#FFFFFF;'
        'border-radius:8px;border:1px solid #E5E7EB;font-family:Inter,sans-serif;">'
        f'<thead><tr style="background:#F9FAFB;">{th}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'<tfoot><tr style="background:#F9FAFB;">{foot_cells}</tr></tfoot>'
        '</table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Onboarding Status Table ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 2026 Customer Onboarding Status")

    if status_rows:
        # Apply manual overrides on top of HubSpot-derived status
        overrides = load_overrides()
        for r in status_rows:
            deal_id = r["id"]
            if deal_id in overrides:
                r["effective_status"] = overrides[deal_id]["status"]
                r["is_manual"] = True
            else:
                r["effective_status"] = r.get("category", "Not Started")
                r["is_manual"] = False

        # ── Velocity summary ───────────────────────────────────────────────────
        counts = {c: 0 for c in CAT_ORDER}
        for r in status_rows:
            cat = r["effective_status"]
            if cat in counts:
                counts[cat] += 1

        overdue = [r for r in status_rows if r["effective_status"] == "Not Started"
                   and r.get("days_elapsed", 0) >= 30]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Not Started", counts["Not Started"],
                  delta=f"{len(overdue)} overdue >30d" if overdue else None,
                  delta_color="inverse")
        c2.metric("Onboarding In Progress", counts["Onboarding In Progress"])
        c3.metric("Onboarding Complete", counts["Onboarding Complete"])
        c4.metric("Survey Launched", counts["Survey Launched"])

        # ── Build DataFrame for data_editor ───────────────────────────────────
        sorted_rows = sorted(status_rows, key=lambda r: (
            CAT_ORDER.index(r["effective_status"]) if r["effective_status"] in CAT_ORDER else 99,
            -r.get("days_elapsed", 0),
        ))

        rows_for_df = []
        deal_ids = []
        for r in sorted_rows:
            days = r.get("days_elapsed", 0)
            days_label = f"{days}d to launch" if r["effective_status"] == "Survey Launched" else f"{days}d"
            rows_for_df.append({
                "Customer":      r["name"],
                "ARR":           r["arr"],
                "Closed Won":    r["closedate"],
                "Days":          days_label,
                "CSM":           r.get("csm", "—"),
                "HubSpot Stage": r.get("stage_label", "—"),
                "Status":        r["effective_status"],
                "View":          r.get("deal_url", ""),
            })
            deal_ids.append(r["id"])

        df = pd.DataFrame(rows_for_df)
        original_statuses = df["Status"].tolist()

        edited_df = st.data_editor(
            df,
            column_config={
                "Customer": st.column_config.TextColumn("Customer", disabled=True, width="large"),
                "ARR": st.column_config.NumberColumn("ARR", format="$%.0f", disabled=True),
                "Closed Won": st.column_config.TextColumn("Closed Won", disabled=True),
                "Days": st.column_config.TextColumn("Days", disabled=True),
                "CSM": st.column_config.TextColumn("CSM", disabled=True, width="small"),
                "HubSpot Stage": st.column_config.TextColumn("HubSpot Stage", disabled=True),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=CAT_ORDER,
                    required=True,
                    width="medium",
                ),
                "View": st.column_config.LinkColumn("↗", display_text="View", disabled=True, width="small"),
            },
            hide_index=True,
            use_container_width=True,
            key="onboarding_status_editor",
        )

        # Detect changes → persist overrides
        new_statuses = edited_df["Status"].tolist()
        if new_statuses != original_statuses:
            for i, (orig, new) in enumerate(zip(original_statuses, new_statuses)):
                if orig != new:
                    overrides[deal_ids[i]] = {
                        "status": new,
                        "updated_at": datetime.now().isoformat(),
                    }
            save_overrides(overrides)
            st.rerun()

        manual_count = sum(1 for r in status_rows if r.get("is_manual"))
        st.caption(
            f"Status dropdown saves locally. {manual_count} manual override{'s' if manual_count != 1 else ''} active. "
            "Days = from Closed Won to today (or to survey launch for launched customers)."
        )
    else:
        st.info("Re-run `python scripts/fetch_hubspot_onboarding.py` to populate onboarding status.")

    # ── Board ──────────────────────────────────────────────────────────────────
    by_month  = defaultdict(list)
    for d in deals:
        by_month[d["month_key"]].append(d)

    months    = _months_in_window(window_start, window_end)
    today_key = today.strftime("%Y-%m")

    past_months   = [m for m in months if m.strftime("%Y-%m") < today_key]
    future_months = [m for m in months if m.strftime("%Y-%m") >= today_key]

    past_with_deals = [m for m in past_months if by_month.get(m.strftime("%Y-%m"))]
    if past_with_deals:
        st.markdown("---")
        st.markdown("#### Closed — Past 90 Days")
        cols = st.columns(len(past_with_deals))
        for i, month in enumerate(past_with_deals):
            key = month.strftime("%Y-%m")
            md  = by_month[key]
            arr = sum(d.get("arr", 0) for d in md)
            with cols[i]:
                st.markdown(f"**{month.strftime('%b %Y')}** &nbsp; {len(md)} · ${arr:,.0f}")
                st.markdown("".join(_card_html(d) for d in md), unsafe_allow_html=True)

    if future_months:
        st.markdown("---")
        st.markdown("#### Active & Upcoming — Next 90 Days")
        cols = st.columns(len(future_months))
        for i, month in enumerate(future_months):
            key = month.strftime("%Y-%m")
            md  = by_month.get(key, [])
            arr = sum(d.get("arr", 0) for d in md)
            arr_str = f" · ${arr:,.0f}" if arr else ""
            with cols[i]:
                st.markdown(
                    f"**{month.strftime('%b %Y')}**{'  📍' if key == today_key else ''}"
                    f" &nbsp; {len(md)}{arr_str}"
                )
                if md:
                    st.markdown("".join(_card_html(d) for d in md), unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div style="color:#9CA3AF;font-size:12px;padding:4px 0;">No deals</div>',
                        unsafe_allow_html=True,
                    )


main()
