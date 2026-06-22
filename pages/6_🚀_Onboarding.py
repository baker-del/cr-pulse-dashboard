"""
CR Pulse — Customer Onboarding Board
Board view of customers in advanced stages / recently closed, by close month.
Window: last 90 days (closed) + next 90 days (pipeline).
"""

import os
import time
import requests
import streamlit as st
from datetime import date, timedelta, datetime
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY", "")

STAGE_CONFIG = {
    "contractsent": {
        "label": "Vendor of Choice",
        "color": "#92400E",
        "bg": "#FFFBEB",
        "border": "#F59E0B",
    },
    "266892604": {
        "label": "Contract Executed",
        "color": "#1E40AF",
        "bg": "#EFF6FF",
        "border": "#3B82F6",
    },
    "closedwon": {
        "label": "Closed Won",
        "color": "#065F46",
        "bg": "#F0FDF4",
        "border": "#10B981",
    },
    "1102698292": {
        "label": "Closed Won",
        "color": "#065F46",
        "bg": "#F0FDF4",
        "border": "#10B981",
    },
}

ONBOARDING_STAGES = set(STAGE_CONFIG.keys())
SALES_PIPELINE = "default"

PROPERTIES = [
    "dealname",
    "dealstage",
    "pipeline",
    "amount",
    "dealtype",
    "closedate",
    "company_industry_dropdown",
    "hubspot_owner_id",
    # onboarding doc — try common property names
    "onboarding_doc_link",
    "hs_onboarding_doc_link",
    "onboarding_document_link",
    "kickoff_doc_link",
    "kickoff_doc_url",
]


def _headers():
    return {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def _load_owners():
    resp = requests.get(
        "https://api.hubapi.com/crm/v3/owners",
        headers=_headers(),
        params={"limit": 100},
        timeout=15,
    )
    if resp.status_code != 200:
        return {}
    return {
        str(o["id"]): f"{o.get('firstName', '')} {o.get('lastName', '')}".strip()
        for o in resp.json().get("results", [])
    }


@st.cache_data(ttl=3600, show_spinner=False)
def _load_deals():
    today = date.today()
    past = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    future = (today + timedelta(days=90)).strftime("%Y-%m-%d")

    payload = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": "closedate",
                        "operator": "GTE",
                        "value": past,
                    },
                    {
                        "propertyName": "closedate",
                        "operator": "LTE",
                        "value": future,
                    },
                    {
                        "propertyName": "pipeline",
                        "operator": "EQ",
                        "value": SALES_PIPELINE,
                    },
                ]
            }
        ],
        "properties": PROPERTIES,
        "limit": 200,
    }

    raw = []
    after = None
    for _ in range(10):
        if after:
            payload["after"] = after
        resp = requests.post(
            "https://api.hubapi.com/crm/v3/objects/deals/search",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        raw.extend(data.get("results", []))
        paging = data.get("paging", {})
        if "next" not in paging:
            break
        after = paging["next"]["after"]
        time.sleep(0.1)

    owners = _load_owners()
    deals = []

    for d in raw:
        p = d["properties"]
        stage = p.get("dealstage", "")
        if stage not in ONBOARDING_STAGES:
            continue

        closedate_str = (p.get("closedate") or "")[:10]
        if not closedate_str:
            continue

        closedate = datetime.strptime(closedate_str, "%Y-%m-%d").date()
        owner_id = str(p.get("hubspot_owner_id") or "")
        dt = p.get("dealtype") or ""

        onboard_doc = (
            p.get("onboarding_doc_link")
            or p.get("hs_onboarding_doc_link")
            or p.get("onboarding_document_link")
            or p.get("kickoff_doc_link")
            or p.get("kickoff_doc_url")
            or ""
        )

        deals.append(
            {
                "id": d["id"],
                "name": p.get("dealname") or "Unnamed",
                "arr": float(p.get("amount") or 0),
                "stage": stage,
                "closedate": closedate,
                "month_key": closedate.strftime("%Y-%m"),
                "month_label": closedate.strftime("%b %Y"),
                "dealtype": (
                    "New Biz"
                    if "new" in dt.lower()
                    else "Renewal"
                    if "renew" in dt.lower()
                    else dt[:12] or "—"
                ),
                "vertical": (p.get("company_industry_dropdown") or "—")[:25],
                "ae": owners.get(owner_id, "—"),
                "onboard_doc": onboard_doc,
            }
        )

    return sorted(deals, key=lambda x: x["closedate"])


def _card_html(deal):
    cfg = STAGE_CONFIG.get(
        deal["stage"],
        {"label": deal["stage"], "color": "#374151", "bg": "#F9FAFB", "border": "#9CA3AF"},
    )
    arr_str = f"${deal['arr']:,.0f}" if deal["arr"] else "—"
    doc_html = ""
    if deal["onboard_doc"]:
        doc_html = (
            f'<div style="margin-top:6px;">'
            f'<a href="{deal["onboard_doc"]}" target="_blank" '
            f'style="color:{cfg["color"]};font-size:11px;text-decoration:none;">'
            f"📄 Onboarding Doc</a></div>"
        )
    return f"""
<div style="background:{cfg['bg']};border-left:4px solid {cfg['border']};
            padding:10px 12px;border-radius:6px;margin-bottom:10px;
            box-shadow:0 1px 2px rgba(0,0,0,0.06);">
  <div style="font-size:10px;font-weight:700;color:{cfg['color']};
              text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">
    {cfg['label']}
  </div>
  <div style="font-weight:700;color:#111827;font-size:13px;line-height:1.3;
              margin-bottom:5px;">{deal['name']}</div>
  <div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:4px;">{arr_str}</div>
  <div style="font-size:11px;color:#6B7280;line-height:1.5;">
    {deal['vertical']}<br>
    {deal['dealtype']} · {deal['ae']}
  </div>
  {doc_html}
</div>"""


def _months_in_window(start: date, end: date):
    months = []
    cur = start.replace(day=1)
    while cur <= end:
        months.append(cur)
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months


def main():
    today = date.today()
    window_start = today - timedelta(days=90)
    window_end = today + timedelta(days=90)

    st.title("🚀 Customer Onboarding")
    st.caption(
        f"Sales Pipeline · Close dates {window_start.strftime('%b %d')} – "
        f"{window_end.strftime('%b %d, %Y')} · "
        "Vendor of Choice, Contract Executed, Closed Won"
    )

    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Loading from HubSpot…"):
        deals = _load_deals()

    if not deals:
        st.info("No onboarding deals in this window.")
        return

    # ── Summary metrics ────────────────────────────────────────────────────────
    closed = [d for d in deals if d["stage"] in ("closedwon", "1102698292")]
    pipeline = [d for d in deals if d["stage"] not in ("closedwon", "1102698292")]
    total_arr = sum(d["arr"] for d in deals)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", len(deals))
    m2.metric("Closed Won", len(closed))
    m3.metric("Advanced Pipeline", len(pipeline))
    m4.metric("Total ARR", f"${total_arr:,.0f}")

    # ── Group by month ─────────────────────────────────────────────────────────
    from collections import defaultdict

    by_month = defaultdict(list)
    for d in deals:
        by_month[d["month_key"]].append(d)

    months = _months_in_window(window_start, window_end)
    today_key = today.strftime("%Y-%m")

    past_months = [m for m in months if m.strftime("%Y-%m") < today_key]
    present_future = [m for m in months if m.strftime("%Y-%m") >= today_key]

    # ── Past: closed ──────────────────────────────────────────────────────────
    past_with_deals = [m for m in past_months if by_month.get(m.strftime("%Y-%m"))]
    if past_with_deals:
        st.markdown("---")
        st.markdown("#### Closed — Past 90 Days")
        cols = st.columns(len(past_with_deals))
        for i, month in enumerate(past_with_deals):
            key = month.strftime("%Y-%m")
            month_deals = by_month[key]
            with cols[i]:
                arr = sum(d["arr"] for d in month_deals)
                st.markdown(
                    f"**{month.strftime('%b %Y')}** &nbsp; {len(month_deals)} deal{'s' if len(month_deals) != 1 else ''} · "
                    f"${arr:,.0f}"
                )
                st.markdown(
                    "".join(_card_html(d) for d in month_deals),
                    unsafe_allow_html=True,
                )

    # ── Present + future ──────────────────────────────────────────────────────
    if present_future:
        st.markdown("---")
        st.markdown("#### Active & Upcoming — Next 90 Days")
        cols = st.columns(len(present_future))
        for i, month in enumerate(present_future):
            key = month.strftime("%Y-%m")
            month_deals = by_month.get(key, [])
            is_now = key == today_key
            label_suffix = " 📍" if is_now else ""
            arr = sum(d["arr"] for d in month_deals)
            arr_str = f" · ${arr:,.0f}" if arr else ""
            with cols[i]:
                st.markdown(
                    f"**{month.strftime('%b %Y')}**{label_suffix} &nbsp; "
                    f"{len(month_deals)} deal{'s' if len(month_deals) != 1 else ''}{arr_str}"
                )
                if month_deals:
                    st.markdown(
                        "".join(_card_html(d) for d in month_deals),
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="color:#9CA3AF;font-size:12px;padding:4px 0;">No deals</div>',
                        unsafe_allow_html=True,
                    )


main()
