"""
CR Pulse — Customer Onboarding Board
Reads from hubspot_onboarding.json (synced locally via fetch_hubspot_onboarding.py).
Board view by close month: last 90 days + next 90 days.
"""

import json
import streamlit as st
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT       = Path(__file__).parent.parent
DATA_FILE  = ROOT / "hubspot_onboarding.json"

STAGE_COLORS = {
    "Onboarding Overview": {"color": "#5B21B6", "bg": "#F5F3FF", "border": "#A78BFA"},
    "Vendor of Choice":    {"color": "#92400E", "bg": "#FFFBEB", "border": "#F59E0B"},
    "Verbal / Out for Sig":{"color": "#92400E", "bg": "#FFFBEB", "border": "#F59E0B"},
    "Contract Executed":   {"color": "#1E40AF", "bg": "#EFF6FF", "border": "#3B82F6"},
    "Closed Won":          {"color": "#065F46", "bg": "#F0FDF4", "border": "#10B981"},
}

CLOSED_WON_LABEL = "Closed Won"


@st.cache_data(ttl=300)
def load_data():
    if not DATA_FILE.exists():
        return None, []
    with open(DATA_FILE) as f:
        raw = json.load(f)
    return raw.get("fetched_at", ""), raw.get("deals", [])


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

    fetched_at, deals = load_data()

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

    # Build pivot: month_key → stage_label → {n, arr}
    pivot = defaultdict(lambda: defaultdict(lambda: {"n": 0, "arr": 0}))
    month_keys_seen = []
    for d in deals:
        mk    = d["month_key"]
        label = d.get("stage_label", "—")
        pivot[mk][label]["n"]   += 1
        pivot[mk][label]["arr"] += d.get("arr", 0)
        if mk not in month_keys_seen:
            month_keys_seen.append(mk)
    month_keys_seen = sorted(month_keys_seen)

    def group_val(mk, group):
        n   = sum(pivot[mk][s]["n"]   for s in group["stages"])
        arr = sum(pivot[mk][s]["arr"] for s in group["stages"])
        return n, arr

    # Header row: blank label col + one col per month + Total
    th = '<th style="text-align:left;padding:7px 12px;font-size:12px;border-bottom:2px solid #E5E7EB;min-width:220px;">Stage Group</th>'
    for mk in month_keys_seen:
        is_now  = mk == today.strftime("%Y-%m")
        is_past = mk < today.strftime("%Y-%m")
        mlabel  = datetime.strptime(mk, "%Y-%m").strftime("%b %Y")
        col_style = (
            "background:#F0FDF4;color:#065F46;font-weight:700;" if is_now else
            "color:#6B7280;" if is_past else "color:#111827;"
        )
        th += (
            f'<th style="text-align:center;padding:7px 12px;font-size:12px;'
            f'border-bottom:2px solid #E5E7EB;white-space:nowrap;{col_style}">'
            f'{"📍 " if is_now else ""}{mlabel}</th>'
        )
    th += '<th style="text-align:center;padding:7px 12px;font-size:12px;border-bottom:2px solid #E5E7EB;font-weight:700;">Total</th>'

    # Data rows
    rows_html = ""
    for g in STAGE_GROUPS:
        row_total_n   = sum(group_val(mk, g)[0] for mk in month_keys_seen)
        row_total_arr = sum(group_val(mk, g)[1] for mk in month_keys_seen)
        cells = (
            f'<td style="padding:7px 12px;font-size:12px;font-weight:600;'
            f'color:{g["color"]};border-bottom:1px solid #F3F4F6;">{g["label"]}</td>'
        )
        for mk in month_keys_seen:
            n, arr = group_val(mk, g)
            is_now = mk == today.strftime("%Y-%m")
            cell_bg = g["bg"] if n else ("#F0FDF4" if is_now else "transparent")
            val_html = (
                f'<b>{n}</b><div style="font-size:10px;color:#6B7280;">${arr:,.0f}</div>'
                if n else '<span style="color:#D1D5DB;">—</span>'
            )
            cells += (
                f'<td style="text-align:center;padding:7px 12px;font-size:12px;'
                f'border-bottom:1px solid #F3F4F6;background:{cell_bg};">{val_html}</td>'
            )
        cells += (
            f'<td style="text-align:center;padding:7px 12px;font-size:12px;font-weight:700;'
            f'border-bottom:1px solid #F3F4F6;">'
            f'<b>{row_total_n}</b>'
            f'<div style="font-size:10px;color:#6B7280;">${row_total_arr:,.0f}</div></td>'
        )
        rows_html += f'<tr>{cells}</tr>'

    # Totals footer
    grand_n   = sum(d.get("arr", 0) for d in deals)  # reuse arr for footer arr
    foot_cells = '<td style="padding:7px 12px;font-size:12px;font-weight:700;border-top:2px solid #E5E7EB;">Total</td>'
    all_total_n = 0
    for mk in month_keys_seen:
        col_n   = sum(group_val(mk, g)[0] for g in STAGE_GROUPS)
        col_arr = sum(group_val(mk, g)[1] for g in STAGE_GROUPS)
        all_total_n += col_n
        is_now = mk == today.strftime("%Y-%m")
        foot_cells += (
            f'<td style="text-align:center;padding:7px 12px;font-size:12px;font-weight:700;'
            f'border-top:2px solid #E5E7EB;{"background:#F0FDF4;" if is_now else ""}">'
            f'<b>{col_n}</b>'
            f'<div style="font-size:10px;color:#6B7280;">${col_arr:,.0f}</div></td>'
        )
    foot_cells += (
        f'<td style="text-align:center;padding:7px 12px;font-size:12px;font-weight:700;'
        f'border-top:2px solid #E5E7EB;"><b>{all_total_n}</b>'
        f'<div style="font-size:10px;color:#6B7280;">${total_arr:,.0f}</div></td>'
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
