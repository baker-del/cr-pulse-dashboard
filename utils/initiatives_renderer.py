"""
Shared renderer for Strategic Initiatives.
Imported by individual initiative pages and the full initiatives page.
"""

import streamlit as st
from datetime import date, datetime
from database.db import get_db

TODAY = date.today()


def days_until(d_str):
    if not d_str:
        return None
    try:
        dt = datetime.strptime(d_str, "%Y-%m-%d").date()
        return (dt - TODAY).days
    except ValueError:
        return None


PROJECTS = [
    {
        "name": "100% NRR",
        "tagline": "CS transformation — from retention to expansion. Crawl → Walk → Run to 130%+ NRR.",
        "owner": "Baker / Eric Gregg",
        "status": "On Track",
        "phase": "Crawl (Now–Q2): GRR 90% + CX Assessment offer defined. Walk starts Q3.",
        "updates": [
            "Crawl/Walk/Run model defined: Crawl = GRR 90%, Walk = NRR 100%, Run = 130%+ by 2027",
            "CX Assessment = expansion offer — CSMs become CX Maturity Partners, not just retention managers",
            "7 CX assessments completed: 1 GREEN (Medicus pilot live), 5 YELLOW, 1 RED",
            "Expansion pipeline: $237K (177% of paced Q2 target of $134K)",
            "Two anchor expansion deals: HDR $132K (Ryanne, Stage 1), Parkhill $60K (Stage 1)",
            "CS team: Eric Gregg + 7 CSMs. Strategic tier: Scheri, Zach Hankin, Amber (30–40 accounts each)",
        ],
        "due_next_30": [
            {"item": "Finalize CX Assessment operational plan + expansion offer menu", "due": "2026-04-30", "owner": "Eric / Hina"},
            {"item": "HDR $132K expansion — advance to Stage 2", "due": "2026-05-15", "owner": "Ryanne / Zach"},
            {"item": "Parkhill $60K expansion — advance to Stage 2", "due": "2026-05-15", "owner": "Eric"},
            {"item": "Top 30 accounts — CX Assessment scheduling complete", "due": "2026-06-30", "owner": "Eric / Hina"},
        ],
        "docs": [
            {"label": "📄 CXNext 2026", "url": "https://docs.google.com/document/d/1QmUaIkb_n4F3SiHKYXY16fYZ-O27bvN0QTJBZe5rqhY/edit"},
            {"label": "📈 100% NRR Model", "url": "https://docs.google.com/spreadsheets/d/1RM3-uzBlYPboXojge0DH_mPbLEM7B9E9s8TlEv1u8i0/edit"},
            {"label": "📁 Drive Folder", "url": "https://drive.google.com/drive/folders/1b4TaDnt2eLcp9bFEXTHtu1mb7AalgzeO"},
        ],
    },
    {
        "name": "Wayfinder",
        "tagline": "Path to 100% NRR — journey CX expansion in staffing",
        "owner": "Baker / Eric / Hina",
        "status": "On Track",
        "phase": "Q2 seeding — CX assessments + ROI calculator before Q3 renewals",
        "updates": [
            "Board doc complete: CX maturity segmentation, competitive intel, path to 100% NRR",
            "228 staffing customers segmented: 126 Reputation-Driven ($1.02M), 102 Measurement-Driven ($2.69M)",
            "7 CX assessments done: 1 GREEN (Medicus pilot live), 5 YELLOW, 1 RED",
            "Competitive intel: 19 Qualtrics accounts ($783K ARR), 42 total overlap accounts mapped",
            "NRR path: 98.7% by Q1 2027, 100%+ by Q2 2027. Needs ROI calculator before July.",
            "Expansion opportunity: $5.6M addressable wallet gap (ex-Qualtrics), 25% capture = $1.4M",
        ],
        "due_next_30": [
            {"item": "Medicus pilot results review — first survey responses", "due": "2026-04-10", "owner": "Hina / Hunter"},
            {"item": "LocumTenens follow-up call with Ali", "due": "2026-04-01", "owner": "Baker / Hina"},
            {"item": "Tempositions CFT demo + Matt (Dir Sales)", "due": "2026-03-31", "owner": "Zach"},
            {"item": "Procom follow-up with Alex (CRO)", "due": "2026-04-07", "owner": "Scheri"},
            {"item": "Schedule remaining CX assessments (11 staffing + 4 accounting)", "due": "2026-04-15", "owner": "Hina / Zach"},
        ],
        "docs": [
            {"label": "📊 Learnings & Recommendations (Board)", "url": "https://docs.google.com/document/d/1mYErZVWgPM5MiAKGwKVAvebD9tWW3g2a_5oE3Cm7iBg/edit"},
            {"label": "📋 Competitive Intelligence Tracker", "url": "https://docs.google.com/spreadsheets/d/1j9_FRuowvXyDfipfGDT3zJKpwM-hjvClGVit3rJlUbs/edit"},
            {"label": "Tracking Sheet", "url": "https://docs.google.com/spreadsheets/d/1s24NhCYPPQ_EA-qSnGWtUXQIzdVDVHKUk-ZqZ3xXS00/edit"},
            {"label": "Hypothesis Doc", "url": "https://docs.google.com/document/d/1kfKHrtCbohJt7KFWUsjm9AfE2qCaQ3Dx2EoAI9MAcEc/edit"},
            {"label": "Call Learnings", "url": "https://docs.google.com/document/d/1Gkg1aQgafkhimfvFnMRiKlXeRYTNkaKoqtJ2KnP9ko4/edit"},
            {"label": "Drive Folder", "url": "https://drive.google.com/drive/folders/1IwoVaM2sLW5ziRP24-VqecZLXX66M_nz"},
        ],
    },
    {
        "name": "S&M Efficiency",
        "tagline": "From 0.23x to 0.65x — Three-lever framework (MQL Quality, MQL→SQL, Win Rate)",
        "owner": "Baker / Pete / Stephen",
        "status": "_derive_from_dashboard",
        "phase": "Q2 improvement plan in action",
        "updates": [
            "Q2 improvement plan in action — all three levers moving",
            "Marketing discretionary budget reduction agreed — aligned with profitability goals",
            "Lever 3 (Win Rate): Action plans accepted by Pete — SAL 4%→20%, AEC 18%→25%. Execution starts April W1.",
            "Lever 2 (MQL→SQL): Analysis complete — 13% end-to-end, two different BDR problems identified. Actions under review.",
            "Lever 1 (MQL Cost): ICP enforcement live. Non-ICP MQLs turned off. Paid paused. ABM narrowed to 500 AEC + 100 Acct.",
            "Demand gen spend cuts: LinkedIn/Meta near zero. Google max $10K. ABM paused except D.C. Bootcamp.",
        ],
        "due_next_30": [
            {"item": "Lever 3: SAL discovery-first mandate + coach assigned", "due": "2026-04-01", "owner": "Pete"},
            {"item": "Lever 3: AEC SE deals transferred to AEs", "due": "2026-04-01", "owner": "Pete"},
            {"item": "Lever 2: Align on MQL→SQL action items", "due": "2026-04-01", "owner": "Baker / Shannon"},
            {"item": "Lever 1: MQL spend analysis with Finance", "due": "2026-04-04", "owner": "Stephen / Andrew"},
            {"item": "Lever 3: SAL 20-touch cadence sequences rebuilt", "due": "2026-04-15", "owner": "Pete / AE"},
            {"item": "Lever 2: 7-day discovery SLA implemented", "due": "2026-04-15", "owner": "Pete / Shannon"},
            {"item": "Lever 3: SAL multi-threading requirement live", "due": "2026-04-30", "owner": "Pete"},
        ],
        "docs": [
            {"label": "📈 S&M Efficiency Dashboard", "url": "https://cr-pulse.streamlit.app/SM_Efficiency"},
            {"label": "S&M Efficiency Plan", "url": "https://docs.google.com/document/d/1ji-Z0hPMJiIds-MuWaK_pMwJczu9qD1coLT0EqDPvrE/edit"},
            {"label": "SAL Winrate Analysis", "url": "https://docs.google.com/document/d/1W1V98mV60higwSsOrZd7fzHqVwg8qlpMerjPQabrMDk/edit"},
            {"label": "AEC Winrate Analysis", "url": "https://docs.google.com/document/d/1m0DlU-gzvDeW3rq1WYzz2DR4R8Uj5-i118NDckjuo9A/edit"},
            {"label": "MQL→SQL Analysis", "url": "https://docs.google.com/document/d/1KcxW6ymZK57dk3pQ6HMBSjbsSDe8hkJ5tfRmqFYTN1E/edit"},
            {"label": "CX Bootcamp ROI", "url": "https://docs.google.com/document/d/1D56wntEyJ0uQedupWtKgfKFqkvDMYa6-9bv-G3Lbz1w/edit"},
            {"label": "ClearlyReferred Proposal", "url": "https://docs.google.com/document/d/17S82EK63yvu1fC__M5A7l8-4CpsdmufvYZO7BAvZ4RA/edit"},
        ],
    },
    {
        "name": "Profitability",
        "tagline": "Hit $250K+ cash EBITDA by end of 2026",
        "owner": "Baker / Andrew",
        "status": "On Track",
        "phase": "Phase 1 executing (Apr 1 deadline), Phase 2 in progress",
        "updates": [
            "Back on track — marketing budget reduction and R&D resource/budget plan both agreed",
            "Colby Kennedy (Product Marketing Lead) last day 2026-04-01",
            "Marketing discretionary budget reduction — agreed",
            "R&D new resource and budget plan — agreed",
            "Portland sublease — not started. Broker engaged but no active pursuit yet.",
            "New ERP rollout week of 2026-04-01, on track",
        ],
        "due_next_30": [
            {"item": "Colby Kennedy (Product Marketing Lead) last day", "due": "2026-04-01", "owner": "Stephen"},
            {"item": "New ERP rollout", "due": "2026-04-01", "owner": "Andrew"},
            {"item": "Portland sublease — start active pursuit", "due": "2026-04-15", "owner": "Andrew"},
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
            "R&D new resource and budget plan — agreed (aligns with profitability goals)",
            "12 prototype experiments defined across 3 data floors (Confluence shortlist)",
            "Goal: run 6-8 prototypes in Q2, get 2-3 to production quality, ship what works",
            "Sequencing: P3 (Detractor Tagger) → P4 → P2/P6 → P9/P10 → P12 → P1/P5/P11 → P7 → P8",
            "Thoughtminds transition planned for Q3",
        ],
        "due_next_30": [
            {"item": "P3 Detractor Category Tagger — build + CSM validation", "due": "2026-04-07", "owner": "Hina / Jorgen"},
            {"item": "P4 Feedback Insights Generator — build + CSM validation", "due": "2026-04-14", "owner": "Hina / Jorgen"},
        ],
        "docs": [
            {"label": "Prism - Hypothesis Validation", "url": "https://docs.google.com/document/d/1ry-0GNK7QKBj-lq4pxcI-JPcqX6yu-2JrO3wfB-2Wpw/edit?tab=t.0#heading=h.2y6bc7m3luc"},
            {"label": "Prototype Q2 Shortlist (Confluence)", "url": "https://clearlyrated.atlassian.net/wiki/spaces/PT/pages/2897084422/Prism+Prototype+Ideas+Q2+Shortlist"},
            {"label": "The Human Edge Campaign Brief", "url": "https://docs.google.com/document/d/16nXxEA0XnB2uc3rXod0JiSz-OCMLkBK6SBFdEtBeWNA/edit"},
            {"label": "PRISM Initiative Folder", "url": "#", "local": "AI Assistant/projects/prism/"},
            {"label": "Roadmap Tracker (Q1 & Q2)", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12108"},
            {"label": "Story & Defect Dashboard", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12075"},
            {"label": "Epic Planning Board", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12042"},
        ],
    },
    {
        "name": "The Human Edge",
        "tagline": "Category-defining campaign — own 'Relationship Intelligence' across professional services",
        "owner": "Baker / Stephen",
        "status": "On Track",
        "phase": "6 blogs complete with full distribution packages. Dual podcast in pre-production. Blog skill operational.",
        "updates": [
            "6 blogs written with full distribution packages (email summary, LinkedIn post, infographic brief each)",
            "Blog skill created — learns from Baker's feedback, scans topics, iterates through 6 gates per blog",
            "Daily topic scanner scheduled (weekdays 12pm PT) — scans X, VC blogs, industry publications, emails Baker",
            "Campaign brief finalized — 5 pillars: Blog Series, Dual Podcasts, PRISM narrative, Best of Awards, Research Report",
            "Category locked: 'Relationship Intelligence' — no competitor owns this in professional services",
            "Dual podcast strategy: 'The AI Advantage' (Baker) + 'Relationship Intelligence' (Stephen)",
        ],
        "due_next_30": [
            {"item": "Publish Blog 4 — 'The 61% Problem'", "due": "2026-04-28", "owner": "Baker / Stephen"},
            {"item": "Record AI Advantage Episode 4 — Matthew Plinck (Coka)", "due": "2026-04-10", "owner": "Baker"},
            {"item": "Record AI Advantage Episode 5 — Guido Maciocci (AECFoundry)", "due": "2026-04-17", "owner": "Baker"},
        ],
        "docs": [
            {"label": "📄 Campaign Brief", "url": "https://docs.google.com/document/d/16nXxEA0XnB2uc3rXod0JiSz-OCMLkBK6SBFdEtBeWNA/edit"},
            {"label": "📝 Blog 1 — The Human Edge", "url": "https://docs.google.com/document/d/1Idqi4wPHxjglzNFYOBrUXX6pvQnHiitA7mvkY-RWKWs/edit"},
            {"label": "📝 Blog 2 — PwC Quiet Part", "url": "https://docs.google.com/document/d/1BFT6pBJ6JxOu52XgH_ru-Nnu12jkF1Mud2lDRKlwKHI/edit"},
            {"label": "📝 Blog 3 — The Broken Ladder", "url": "https://docs.google.com/document/d/1SDVUNC-Im09yvBfOWGtjqAnuILBFpD4FJzCUFCHmWUY/edit"},
            {"label": "📝 Blog 4 — The 61% Problem", "url": "https://docs.google.com/document/d/1uilR9nBMlhABkkqX0fQk93FMGRgxW_tWxCXKD4HRtCs/edit"},
            {"label": "📝 Blog 5 — Bill Trust", "url": "https://docs.google.com/document/d/17aVeVOO40oidtN8Iu7gYsRcO4NvGrpIbu0dY0r_a5zY/edit"},
            {"label": "📝 Blog 6 — The Renewal Skill", "url": "https://docs.google.com/document/d/1XfK6cyvI9jowVJapwwZPMUFrMW4SsRI76rmARneiVxY/edit"},
            {"label": "🎙️ AI Advantage Guest Tracker", "url": "https://docs.google.com/spreadsheets/d/1RIS42Rri_ZSSUyq5PTRZE_ZpKgI-ntmfejcmEoy_RiQ/edit"},
            {"label": "🎙️ AI Advantage One-Pager", "url": "https://drive.google.com/file/d/1XXu0JzZfhp_L65T88FsfGxFyLn38MeJq/view"},
            {"label": "🎙️ Interview Script", "url": "https://docs.google.com/document/d/1ugJC24A5nSyV5YFQpS5KBsXbGPbAl3TJh7chXBlc_rg/edit"},
            {"label": "📁 The Human Edge Drive Folder", "url": "https://drive.google.com/drive/folders/1eKMUBusMTzNIvFc8W01ybVJpi_jagNKy"},
        ],
    },
    {
        "name": "Moonshot",
        "tagline": "Find best exit value for investors — strategic acquirer & PE targeting",
        "owner": "Baker",
        "status": "On Track",
        "phase": "Research & target identification — no timeline set",
        "updates": [
            "47 strategic targets identified across AEC Platform, Prof Services Tech, and PE categories",
            "11 high-priority targets ranked: Roper/Deltek #1, Intapp #2, Thomson Reuters #3, Unanet #4",
            "5 detailed investor profiles completed (Thomson Reuters, Intapp, Deltek, Unanet, Avionte)",
            "PRISM launch (July 2026) is the key value inflection point for most acquirer conversations",
            "No active outreach timeline — building intelligence foundation first",
        ],
        "due_next_30": [],
        "docs": [
            {"label": "Strategic Target List", "url": "https://docs.google.com/spreadsheets/d/1NESoDVQxeDvXIssf2BZs5-PD9q8iQPqoUEDAJU2f020/edit"},
            {"label": "Investor Profiles Folder", "url": "https://drive.google.com/drive/folders/1m2tLl3cWI1RPgZBYR8M32fHOQLURLCH2"},
            {"label": "Moonshot Drive Folder", "url": "https://drive.google.com/drive/folders/1_aFFPut4xXIbV92g5EcbJoPtb1MASD2r"},
            {"label": "Deltek Profile", "url": "https://drive.google.com/file/d/1TKs8mtWaKKhWaSs1fe2Br9LSmshp5EtP/view"},
            {"label": "Intapp Profile", "url": "https://drive.google.com/file/d/1gXCXToRA3aCBd5ZAzXZzcbNRn4Nh7LTc/view"},
            {"label": "Thomson Reuters Profile", "url": "https://drive.google.com/file/d/1bEuMjQ2qZ1v82HF-ReSgHRUMCXBabQQG/view"},
            {"label": "Unanet Profile", "url": "https://drive.google.com/file/d/1twwQd6otdP8NayEx65_2X HfNRn4Nh7LTc/view"},
            {"label": "Avionte Profile", "url": "https://drive.google.com/file/d/1bpKCSZcw76rEe6ytmfBc-KjYZO7BAvZ4RA/view"},
        ],
    },
]

STATUS_COLORS = {
    "On Track": ("#e6f4ea", "#1a7a2e", "1a7a2e"),
    "At Risk":  ("#fff8e1", "#b8860b", "b8860b"),
    "Behind":   ("#fde8e8", "#c0392b", "c0392b"),
    "Complete": ("#e8eef4", "#1A3C6E", "1A3C6E"),
}


def _derive_sm_status():
    try:
        db = get_db()
        quarter = st.session_state.get('current_quarter', 'Q2')
        year = st.session_state.get('current_year', 2026)
        kpis = db.get_latest_kpis(quarter, year)
        if kpis.empty:
            return "Behind"
        sm_kpis = kpis[kpis['kpi_name'].str.startswith('SM_')]
        if sm_kpis.empty:
            return "Behind"
        statuses = sm_kpis['status'].dropna().tolist()
        behind  = sum(1 for s in statuses if s == 'Behind')
        at_risk = sum(1 for s in statuses if s == 'At Risk')
        on_track = sum(1 for s in statuses if s == 'On Track')
        if behind > len(statuses) * 0.3:
            return "Behind"
        elif at_risk + behind > len(statuses) * 0.3:
            return "At Risk"
        elif on_track > 0:
            return "On Track"
        return "Behind"
    except Exception:
        return "Behind"


def render_project_card(project):
    status = project["status"]
    if status == "_derive_from_dashboard":
        status = _derive_sm_status()

    bg, text_color, border_hex = STATUS_COLORS.get(status, ("#f5f5f5", "#333", "999"))

    st.markdown(
        f'<div style="border:1px solid #{border_hex}; border-left:5px solid #{border_hex}; '
        f'border-radius:6px; padding:16px 20px; margin-bottom:16px; background:#fafafa;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
        f'<span style="font-size:1.15rem; font-weight:700; color:#1A3C6E;">{project["name"]}</span>'
        f'<span style="background:{bg}; color:{text_color}; padding:3px 12px; border-radius:12px; '
        f'font-size:0.78rem; font-weight:600;">{status}</span>'
        f'</div>'
        f'<div style="font-size:0.85rem; color:#666; margin-bottom:4px;">{project["tagline"]}</div>'
        f'<div style="font-size:0.8rem; color:#888;">Owner: {project["owner"]} &nbsp;|&nbsp; Phase: {project["phase"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(
            '<div style="font-size:0.85rem; font-weight:600; color:#1A3C6E; margin-bottom:4px;">Recent Updates</div>',
            unsafe_allow_html=True,
        )
        update_html = "".join(f'<li style="margin-bottom:3px;">{u}</li>' for u in project["updates"][-5:])
        st.markdown(
            f'<ul style="font-size:0.82rem; line-height:1.6; margin:0; padding-left:18px;">{update_html}</ul>',
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            '<div style="font-size:0.85rem; font-weight:600; color:#1A3C6E; margin-bottom:4px;">Due Next 30 Days</div>',
            unsafe_allow_html=True,
        )
        due_items = project.get("due_next_30", [])
        upcoming = [d for d in due_items if days_until(d.get("due")) is None or days_until(d.get("due")) >= 0]
        if upcoming:
            due_html = ""
            for d in upcoming:
                days = days_until(d.get("due"))
                if days is not None and days <= 7:
                    tag = f'<span style="color:#b8860b; font-weight:600;">{days}d</span>'
                elif days is not None:
                    tag = f'<span style="color:#666;">{days}d</span>'
                else:
                    tag = ""
                due_html += (
                    f'<li style="margin-bottom:4px;">'
                    f'{d["item"]} '
                    f'<span style="color:#888;">({d.get("owner", "")})</span> '
                    f'{tag}</li>'
                )
            st.markdown(
                f'<ul style="font-size:0.82rem; line-height:1.6; margin:0; padding-left:18px;">{due_html}</ul>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No items due in the next 30 days.")

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

    st.markdown("")


def render_initiatives(target=None):
    """Render the full strategic initiatives page, optionally scrolled to `target`."""
    st.title("📁 Strategic Initiatives")
    st.caption(f"Last refreshed: {TODAY.strftime('%B %-d, %Y')}")

    on_track = sum(1 for p in PROJECTS if p["status"] == "On Track")
    at_risk  = sum(1 for p in PROJECTS if p["status"] == "At Risk")
    behind   = sum(1 for p in PROJECTS if p["status"] == "Behind")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Initiatives", len(PROJECTS))
    c2.metric("On Track", on_track)
    c3.metric("At Risk", at_risk)
    c4.metric("Behind", behind)

    st.markdown("---")

    for project in PROJECTS:
        anchor_id = project["name"].lower().replace(" ", "-").replace("&", "and")
        st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)
        render_project_card(project)

    if target:
        anchor_id = target.lower().replace(" ", "-").replace("&", "and")
        st.components.v1.html(
            f"<script>window.parent.document.getElementById('{anchor_id}')"
            f"?.scrollIntoView({{behavior:'smooth',block:'start'}});</script>",
            height=0,
        )
