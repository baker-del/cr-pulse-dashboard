"""
CR Pulse — Strategic Initiatives
Card view of active strategic initiatives with status, updates, docs, and next steps.
Data sourced from AI Assistant project files.
"""

import streamlit as st
from datetime import date, datetime

# ── Initiative data ───────────────────────────────────────────────────────────
# Each initiative is a dict loaded from AI Assistant memory/project files.
# To update: edit the initiative dicts below or point to a JSON/DB source.

TODAY = date.today()


def days_until(d_str):
    """Return days until a date string (YYYY-MM-DD or 'Month D' or None)."""
    if not d_str:
        return None
    try:
        dt = datetime.strptime(d_str, "%Y-%m-%d").date()
        return (dt - TODAY).days
    except ValueError:
        return None


PROJECTS = [
    {
        "name": "Wayfinder",
        "tagline": "Validate journey-based CX with staffing customers",
        "owner": "Baker / Hina",
        "status": "Behind",
        "phase": "Customer Validation (Part 1) — good learnings",
        "updates": [
            "Phase 2 outreach complete — 11 staffing + 4 accounting firms interested in CX assessments",
            "Meeting scheduling in progress — many CX assessments already on calendar for next 3 weeks",
            "5 customer calls completed (Medicus GREEN, LocumTenens YELLOW, Procom YELLOW, Tempositions YELLOW, J. Kent RED)",
            "Key learning: majority land YELLOW — interest is real but change management blocks conversion",
            "Emerging ICP: mid-market+ firms with CX champion role and multi-touchpoint journeys",
        ],
        "due_next_30": [
            {"item": "Medicus pilot results review — first survey responses", "due": "2026-04-10", "owner": "Hina / Hunter"},
            {"item": "LocumTenens follow-up call with Ali", "due": "2026-04-01", "owner": "Baker / Hina"},
            {"item": "Tempositions CFT demo + Matt (Dir Sales)", "due": "2026-03-31", "owner": "Zach"},
            {"item": "Procom follow-up with Alex (CRO)", "due": "2026-04-07", "owner": "Scheri"},
            {"item": "Schedule remaining CX assessments (11 staffing + 4 accounting)", "due": "2026-04-15", "owner": "Hina / Zach"},
        ],
        "docs": [
            {"label": "Tracking Sheet", "url": "https://docs.google.com/spreadsheets/d/1s24NhCYPPQ_EA-qSnGWtUXQIzdVDVHKUk-ZqZ3xXS00/edit"},
            {"label": "Hypothesis Doc", "url": "https://docs.google.com/document/d/1kfKHrtCbohJt7KFWUsjm9AfE2qCaQ3Dx2EoAI9MAcEc/edit"},
            {"label": "Call Learnings", "url": "https://docs.google.com/document/d/1Gkg1aQgafkhimfvFnMRiKlXeRYTNkaKoqtJ2KnP9ko4/edit"},
            {"label": "Drive Folder", "url": "https://drive.google.com/drive/folders/1IwoVaM2sLW5ziRP24-VqecZLXX66M_nz"},
        ],
    },
    {
        "name": "S&M Efficiency",
        "tagline": "Improve S&M efficiency from 51% (2025) to 65% by end of 2026",
        "owner": "Pete / Stephen / Baker",
        "status": "At Risk",
        "phase": "Execution — Q1 action items",
        "updates": [
            "Goal: 51% → 65% S&M efficiency ratio — key dependency for $250K+ cash EBITDA target",
            "Mar 20 items due: ICP enforcement, paid search, MQL scoring (Freddy/Stephen/Pete)",
            "Mar 27 items due: BDR inbound process, partnership pipeline, referral program (Shannon/Pete/Stephen/Baker)",
            "ClearlyReferred referral program proposal complete — ready for leadership review",
            "Apr 30: SAL enablement program due (Pete/Stephen)",
        ],
        "due_next_30": [
            {"item": "ICP enforcement across non-ABM channels at MQL level", "due": "2026-03-20", "owner": "Freddy / Stephen"},
            {"item": "Paid search — industry-specific terms", "due": "2026-03-20", "owner": "Freddy / Stephen"},
            {"item": "MQL scoring model update", "due": "2026-03-20", "owner": "Freddy / Stephen / Pete"},
            {"item": "BDR inbound process for non-ICP leads", "due": "2026-03-27", "owner": "Shannon / Pete"},
            {"item": "Partnership referral pipeline (WPG model)", "due": "2026-03-27", "owner": "Pete / Shannon"},
            {"item": "ClearlyReferred program launch", "due": "2026-04-01", "owner": "Stephen / Baker"},
            {"item": "SAL enablement program", "due": "2026-04-30", "owner": "Pete / Stephen"},
        ],
        "docs": [
            {"label": "S&M Efficiency Plan", "url": "https://docs.google.com/document/d/1ji-Z0hPMJiIds-MuWaK_pMwJczu9qD1coLT0EqDPvrE/edit"},
            {"label": "ClearlyReferred Proposal", "url": "https://docs.google.com/document/d/17S82EK63yvu1fC__M5A7l8-4CpsdmufvYZO7BAvZ4RA/edit"},
            {"label": "CX Bootcamp ROI Analysis", "url": "https://docs.google.com/document/d/1D56wntEyJ0uQedupWtKgfKFqkvDMYa6-9bv-G3Lbz1w/edit"},
            {"label": "SAL Winrate Analysis", "url": "https://docs.google.com/document/d/1W1V98mV60higwSsOrZd7fzHqVwg8qlpMerjPQabrMDk/edit"},
            {"label": "AEC Winrate Analysis", "url": "https://docs.google.com/document/d/1m0DlU-gzvDeW3rq1WYzz2DR4R8Uj5-i118NDckjuo9A/edit"},
            {"label": "MQL→SQL Analysis", "url": "https://docs.google.com/document/d/1KcxW6ymZK57dk3pQ6HMBSjbsSDe8hkJ5tfRmqFYTN1E/edit"},
        ],
    },
    {
        "name": "Profitability",
        "tagline": "Hit $250K+ cash EBITDA by end of 2026",
        "owner": "Baker / Andrew",
        "status": "Behind",
        "phase": "Phase 1 executing (Apr 1 deadline), Phase 2 planning",
        "updates": [
            "Behind — dependent on S&M efficiency plan and Portland sublease to hit target",
            "Colby Kennedy (Product Marketing Lead) last day 2026-04-01",
            "Marketing discretionary budget review this week",
            "Portland sublease — broker selected, engagement signed. No target date yet.",
            "Engineering plan and budget review due 2026-04-01",
            "New ERP rollout week of 2026-04-01, on track",
        ],
        "due_next_30": [
            {"item": "Engineering plan and budget review", "due": "2026-04-01", "owner": "Baker / Jorgen"},
            {"item": "Colby Kennedy (Product Marketing Lead) last day", "due": "2026-04-01", "owner": "Stephen"},
            {"item": "New ERP rollout", "due": "2026-04-01", "owner": "Andrew"},
            {"item": "Portland sublease — set target date with broker", "due": "2026-04-15", "owner": "Andrew"},
            {"item": "Vendor/spend review kickoff", "due": "2026-04-15", "owner": "Andrew"},
        ],
        "docs": [
            {"label": "Cost Discipline Tracker", "url": "#", "local": "AI Assistant/projects/profitability/tracker.md"},
            {"label": "Portland Lease Strategy", "url": "https://docs.google.com/document/d/10Sg3ZBJ_pkgaMeTl71e2UeODmO6daX9iTyQ1JUaUWTI/edit"},
        ],
    },
    {
        "name": "PRISM",
        "tagline": "Launch agentic CX platform for professional services",
        "owner": "Hina / Jorgen",
        "status": "On Track",
        "phase": "Q2 prototyping — 12 experiments, mid-April validation target",
        "updates": [
            "12 prototype experiments defined across 3 data floors (Confluence shortlist)",
            "Goal: run 6-8 prototypes in Q2, get 2-3 to production quality, ship what works",
            "Sequencing: P3 (Detractor Tagger) → P4 → P2/P6 → P9/P10 → P12 → P1/P5/P11 → P7 → P8",
            "Engineering plan and budget review due 2026-04-01",
            "Thoughtminds transition planned for Q3",
        ],
        "due_next_30": [
            {"item": "P3 Detractor Category Tagger — build + CSM validation", "due": "2026-04-07", "owner": "Hina / Jorgen"},
            {"item": "P4 Feedback Insights Generator — build + CSM validation", "due": "2026-04-14", "owner": "Hina / Jorgen"},
            {"item": "Engineering plan and budget review", "due": "2026-04-01", "owner": "Baker / Jorgen"},
        ],
        "docs": [
            {"label": "Prototype Q2 Shortlist (Confluence)", "url": "https://clearlyrated.atlassian.net/wiki/spaces/PT/pages/2897084422/Prism+Prototype+Ideas+Q2+Shortlist"},
            {"label": "PRISM Initiative Folder", "url": "#", "local": "AI Assistant/projects/prism/"},
            {"label": "Roadmap Tracker (Q1 & Q2)", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12108"},
            {"label": "Story & Defect Dashboard", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12075"},
            {"label": "Epic Planning Board", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12042"},
        ],
    },
]


# ── Status colors ─────────────────────────────────────────────────────────────
STATUS_COLORS = {
    "On Track": ("#e6f4ea", "#1a7a2e", "1a7a2e"),
    "At Risk":  ("#fff8e1", "#b8860b", "b8860b"),
    "Behind":   ("#fde8e8", "#c0392b", "c0392b"),
    "Complete": ("#e8eef4", "#1A3C6E", "1A3C6E"),
}


def render_project_card(project):
    """Render a single project card."""
    bg, text_color, border_hex = STATUS_COLORS.get(project["status"], ("#f5f5f5", "#333", "999"))

    # Card container
    st.markdown(
        f'<div style="border:1px solid #{border_hex}; border-left:5px solid #{border_hex}; '
        f'border-radius:6px; padding:16px 20px; margin-bottom:16px; background:#fafafa;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
        f'<span style="font-size:1.15rem; font-weight:700; color:#1A3C6E;">{project["name"]}</span>'
        f'<span style="background:{bg}; color:{text_color}; padding:3px 12px; border-radius:12px; '
        f'font-size:0.78rem; font-weight:600;">{project["status"]}</span>'
        f'</div>'
        f'<div style="font-size:0.85rem; color:#666; margin-bottom:4px;">{project["tagline"]}</div>'
        f'<div style="font-size:0.8rem; color:#888;">Owner: {project["owner"]} &nbsp;|&nbsp; Phase: {project["phase"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Key updates
        st.markdown(
            '<div style="font-size:0.85rem; font-weight:600; color:#1A3C6E; margin-bottom:4px;">Recent Updates</div>',
            unsafe_allow_html=True,
        )
        update_html = "".join(
            f'<li style="margin-bottom:3px;">{u}</li>' for u in project["updates"][-5:]
        )
        st.markdown(
            f'<ul style="font-size:0.82rem; line-height:1.6; margin:0; padding-left:18px;">{update_html}</ul>',
            unsafe_allow_html=True,
        )

    with col_right:
        # Due next 30 days
        st.markdown(
            '<div style="font-size:0.85rem; font-weight:600; color:#1A3C6E; margin-bottom:4px;">Due Next 30 Days</div>',
            unsafe_allow_html=True,
        )
        due_items = project.get("due_next_30", [])
        if due_items:
            due_html = ""
            for d in due_items:
                days = days_until(d.get("due"))
                if days is not None and days < 0:
                    tag = f'<span style="color:#c0392b; font-weight:600;">OVERDUE</span>'
                elif days is not None and days <= 7:
                    tag = f'<span style="color:#b8860b; font-weight:600;">{days}d</span>'
                elif days is not None:
                    tag = f'<span style="color:#666;">{days}d</span>'
                else:
                    tag = ""
                due_html += (
                    f'<li style="margin-bottom:4px;">'
                    f'{d["item"]} '
                    f'<span style="color:#888;">({d.get("owner", "")})</span> '
                    f'{tag}'
                    f'</li>'
                )
            st.markdown(
                f'<ul style="font-size:0.82rem; line-height:1.6; margin:0; padding-left:18px;">{due_html}</ul>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No items due in the next 30 days.")

    # Docs row
    docs = project.get("docs", [])
    if docs:
        doc_links = " &nbsp;|&nbsp; ".join(
            f'<a href="{d["url"]}" target="_blank" style="font-size:0.8rem; color:#1A3C6E;">{d["label"]}</a>'
            for d in docs
        )
        st.markdown(
            f'<div style="margin-top:8px; padding-top:8px; border-top:1px solid #eee;">{doc_links}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")  # spacer


# ── Page ──────────────────────────────────────────────────────────────────────
st.title("📁 Strategic Initiatives")
st.caption(f"Last refreshed: {TODAY.strftime('%B %-d, %Y')}")

# Summary counts
on_track = sum(1 for p in PROJECTS if p["status"] == "On Track")
at_risk = sum(1 for p in PROJECTS if p["status"] == "At Risk")
behind = sum(1 for p in PROJECTS if p["status"] == "Behind")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Initiatives", len(PROJECTS))
c2.metric("On Track", on_track)
c3.metric("At Risk", at_risk)
c4.metric("Behind", behind)

st.markdown("---")

# Overdue items across all projects
all_overdue = []
for p in PROJECTS:
    for d in p.get("due_next_30", []):
        days = days_until(d.get("due"))
        if days is not None and days < 0:
            all_overdue.append(f'{p["name"]}: {d["item"]} ({d.get("owner", "")}) — due {d["due"]}')

if all_overdue:
    overdue_html = "".join(f"<li>{o}</li>" for o in all_overdue)
    st.markdown(
        f'<div style="background:#fde8e8; border-left:4px solid #c0392b; padding:10px 16px; '
        f'border-radius:4px; margin-bottom:16px;">'
        f'<div style="font-weight:600; color:#c0392b; margin-bottom:4px;">Overdue Items</div>'
        f'<ul style="font-size:0.82rem; margin:0; padding-left:18px;">{overdue_html}</ul>'
        f'</div>',
        unsafe_allow_html=True,
    )

# Render project cards
for project in PROJECTS:
    render_project_card(project)
