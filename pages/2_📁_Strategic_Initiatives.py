"""
CR Pulse — Strategic Initiatives
Card view of active strategic initiatives with status, updates, docs, and next steps.
Data sourced from AI Assistant project files.
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
from database.db import get_db

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
        "phase": "Q2 execution — all three levers analyzed, actions starting April W1",
        "updates": [
            "Three-lever framework in place: MQL Quality (Lever 1), MQL→SQL (Lever 2), Win Rate (Lever 3)",
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
            {"label": "The AI Advantage Brief", "url": "#", "local": "Desktop/AI_Advantage_Podcast_OnePager.pdf"},
            {"label": "PRISM Initiative Folder", "url": "#", "local": "AI Assistant/projects/prism/"},
            {"label": "Roadmap Tracker (Q1 & Q2)", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12108"},
            {"label": "Story & Defect Dashboard", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12075"},
            {"label": "Epic Planning Board", "url": "https://clearlyrated.atlassian.net/jira/dashboards/12042"},
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
            {"label": "Strategic Target List (XLS)", "url": "https://drive.google.com/file/d/1bO1T3vYCpN4JiaMSuSBux5ZkLRieiuEu/view"},
            {"label": "Investor Profiles Folder", "url": "https://drive.google.com/drive/folders/1m2tLl3cWI1RPgZBYR8M32fHOQLURLCH2"},
            {"label": "Moonshot Drive Folder", "url": "https://drive.google.com/drive/folders/1_aFFPut4xXIbV92g5EcbJoPtb1MASD2r"},
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


def _derive_sm_status():
    """Derive S&M Efficiency status from the S&M dashboard KPIs."""
    try:
        db = get_db()
        quarter = st.session_state.get('current_quarter', 'Q2')
        year = st.session_state.get('current_year', 2026)
        kpis = db.get_latest_kpis(quarter, year)
        if kpis.empty:
            return "Behind"  # No data = behind

        sm_kpis = kpis[kpis['kpi_name'].str.startswith('SM_')]
        if sm_kpis.empty:
            return "Behind"

        # Count statuses
        statuses = sm_kpis['status'].dropna().tolist()
        behind = sum(1 for s in statuses if s == 'Behind')
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
    """Render a single project card."""
    status = project["status"]
    if status == "_derive_from_dashboard":
        status = _derive_sm_status()

    bg, text_color, border_hex = STATUS_COLORS.get(status, ("#f5f5f5", "#333", "999"))

    # Card container
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

# ── Moonshot Deep Dive ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## Moonshot — Strategic Target List & Investor Profiles")

# Load the XLS target list
MOONSHOT_XLS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "moonshot", "ClearlyRated-Strategic-Target-List-Updated.xlsx")
if os.path.exists(MOONSHOT_XLS):
    df = pd.read_excel(MOONSHOT_XLS)

    # Key documents — same link style as project cards
    moonshot_docs = " &nbsp;|&nbsp; ".join([
        '<a href="https://drive.google.com/file/d/1TKs8mtWaKKhWaSs1fe2Br9LSmshp5EtP/view" target="_blank" style="font-size:0.8rem; color:#1A3C6E;">📄 Deltek Profile</a>',
        '<a href="https://drive.google.com/file/d/1gXCXToRA3aCBd5ZAzXZzcbNRn4Nh7LTc/view" target="_blank" style="font-size:0.8rem; color:#1A3C6E;">📄 Intapp Profile</a>',
        '<a href="https://drive.google.com/file/d/1bEuMjQ2qZ1v82HF-ReSgHRUMCXBabQQG/view" target="_blank" style="font-size:0.8rem; color:#1A3C6E;">📄 Thomson Reuters Profile</a>',
        '<a href="https://drive.google.com/file/d/1twwQd6otdP8NayEx65_2XHv05nd8Wkic/view" target="_blank" style="font-size:0.8rem; color:#1A3C6E;">📄 Unanet Profile</a>',
        '<a href="https://drive.google.com/file/d/1bpKCSZcw76rEe6ytmfBc-KvWzfmlUMR0/view" target="_blank" style="font-size:0.8rem; color:#1A3C6E;">📄 Avionte Profile</a>',
    ])
    st.markdown(
        f'<div style="margin-bottom:12px; padding:8px 0; border-bottom:1px solid #eee;">{moonshot_docs}</div>',
        unsafe_allow_html=True,
    )

    # Show only High Priority by default
    df_high = df[df['Priority'].str.contains('High', na=False)]

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("High Priority Targets", len(df_high))
    m2.metric("Strategic Acquirers", len(df_high[df_high['Category'].str.contains('Platform|Tech|Staffing', na=False)]))
    m3.metric("PE / Financial", len(df_high[df_high['Category'].str.contains('PE|Holding', na=False)]))

    # Display high priority table
    display_cols = ['Company', 'Category', 'Est. Revenue / AUM', 'Key Contact', 'Title', 'Strategic Notes']
    st.dataframe(
        df_high[display_cols].reset_index(drop=True),
        use_container_width=True,
        height=400,
    )

    # Expandable: show full list
    with st.expander("View all 47 targets (Medium + Lower priority)"):
        priority_filter = st.selectbox("Filter", ["All", "Medium", "Lower"])
        if priority_filter != "All":
            df_rest = df[df['Priority'].str.contains(priority_filter, na=False)]
        else:
            df_rest = df[~df['Priority'].str.contains('High', na=False)]
        display_cols_full = ['Company', 'Category', 'Priority', 'Est. Revenue / AUM', 'Key Contact', 'Title', 'Strategic Notes']
        st.dataframe(
            df_rest[display_cols_full].reset_index(drop=True),
            use_container_width=True,
            height=300,
        )

    # Top 5 Investor Profile Cards
    st.markdown("### Top 5 Target Profiles")

    TOP_5_PROFILES = [
        {
            "rank": "#1",
            "company": "Roper Technologies / Deltek",
            "category": "AEC Platform (Parent)",
            "revenue": "$6.8B revenue / ~$55B mkt cap",
            "ceo": "Neil Hunn (Roper) / Bob Hughes (Deltek)",
            "thesis": "Owner of Deltek — ClearlyRated's deepest AEC integration. 30K global customers, 97% renewal rate. PRISM as AI CX layer for Deltek ecosystem. Roper's stock down 38% from peak — under pressure to show AI thesis.",
            "approach": "Warm up via Deltek partnership team Q2 2026. Don't approach Deltek without Roper's blessing.",
        },
        {
            "rank": "#2",
            "company": "Intapp",
            "category": "Professional Services Tech",
            "revenue": "$420M ARR (NASDAQ: INTA, ~$1.8B mkt cap)",
            "ceo": "John Hall (since 2007)",
            "thesis": "Serves exact same 4 verticals: legal, accounting, AEC, consulting. 2,750+ firms. 120%+ cloud NRR. AI platform (Celeste) with Anthropic Claude integration. PRISM fills a CX gap they'd otherwise build.",
            "approach": "Reach out Q2 2026 pre-PRISM. Frame as 'the CX intelligence layer for your 4 verticals.'",
        },
        {
            "rank": "#3",
            "company": "Thomson Reuters",
            "category": "Professional Services Tech",
            "revenue": "$9.2B revenue (NYSE: TRI)",
            "ceo": "Steve Hasker",
            "thesis": "$11B committed through 2028 for M&A, $6.8B deployed. 'Change the Professions' strategy = vertical AI platforms. $600M+ annual AI investment. CoCounsel at 1M users. Key risk: OpenAI/Perplexity commoditizing legal AI.",
            "approach": "Warm approach via TR Ventures or Reuters Events connections. Timing: post-PRISM launch Aug-Sep 2026.",
        },
        {
            "rank": "#4",
            "company": "Unanet",
            "category": "AEC Platform",
            "revenue": "~$115-160M ARR (PE-backed: JMI Equity + Onex)",
            "ceo": "Craig Halliday (since Sep 2019)",
            "thesis": "Direct integration partner, AEC-focused ERP. 4,200+ GovCon/AEC customers. ~110-120% NRR. Champ AI expansion + GrowthStudio downmarket play. ClearlyRated's $28K ACV AEC customers are already Unanet customers.",
            "approach": "Closest integration, most natural tuck-in. Approach directly or via Accel-KKR. Same customer base = no integration risk.",
        },
        {
            "rank": "#5",
            "company": "Avionte",
            "category": "Staffing Platform",
            "revenue": "~$41M revenue (Serent Capital-backed)",
            "ceo": "John Long (founder/operator)",
            "thesis": "900+ staffing agencies on unified ATS/CRM/payroll/VMS stack. Mid-market staffing agencies (<$50M) prefer Avionte's native stack over Salesforce. Lacks client feedback/performance analytics — the core gap PRISM fills.",
            "approach": "Strategic fit as acquisition target or deep partner. Staffing vertical alignment is strong.",
        },
    ]

    for profile in TOP_5_PROFILES:
        st.markdown(
            f'<div style="border:1px solid #1A3C6E; border-left:5px solid #1A3C6E; '
            f'border-radius:6px; padding:14px 18px; margin-bottom:12px; background:#f8fafc;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
            f'<span style="font-size:1.05rem; font-weight:700; color:#1A3C6E;">{profile["rank"]} {profile["company"]}</span>'
            f'<span style="background:#e6f4ea; color:#1a7a2e; padding:2px 10px; border-radius:10px; '
            f'font-size:0.75rem; font-weight:600;">{profile["category"]}</span>'
            f'</div>'
            f'<div style="font-size:0.82rem; color:#555; margin-bottom:2px;"><b>Revenue:</b> {profile["revenue"]} &nbsp;|&nbsp; <b>CEO:</b> {profile["ceo"]}</div>'
            f'<div style="font-size:0.82rem; color:#333; margin-top:6px;"><b>Thesis:</b> {profile["thesis"]}</div>'
            f'<div style="font-size:0.82rem; color:#1A3C6E; margin-top:4px;"><b>Approach:</b> {profile["approach"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.warning("Strategic target list not found. Run data sync to download from Google Drive.")
