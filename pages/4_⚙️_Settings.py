"""
Settings & Configuration Page

Database initialization, data export, HubSpot sync, and Google Sheets sync
"""

import streamlit as st
from datetime import datetime
import pandas as pd
from pathlib import Path
from database.db import get_db


st.title("⚙️ Settings & Configuration")
st.markdown("---")

# Get database
db = get_db()

# Database Initialization
st.subheader("📂 Database Setup")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    **Initialize Database with Targets**

    This will load the 2026 annual targets from CSV into the database.
    Run this once when first setting up the application.
    """)

    targets_csv = Path(__file__).parent.parent / 'assets' / 'annual_targets_2026.csv'

    if targets_csv.exists():
        st.success(f"✅ Targets CSV found: `{targets_csv.name}`")

        if st.button("Load Targets from CSV"):
            try:
                with st.spinner("Loading targets..."):
                    db.load_targets_from_csv(str(targets_csv), year=2026)
                    targets = db.get_targets(year=2026)
                    st.success(f"✅ Successfully loaded {len(targets)} KPI targets for 2026!")
                    st.balloons()
            except Exception as e:
                st.error(f"Error loading targets: {e}")

with col2:
    # Check current targets
    targets = db.get_targets(year=2026)
    st.metric("Targets Loaded", len(targets))

    if targets:
        st.caption("Database initialized ✅")
    else:
        st.warning("No targets loaded yet")

st.markdown("---")

# HubSpot Data Sync
st.subheader("🔄 HubSpot Data Sync")

st.markdown("""
**Auto-Captured KPIs from HubSpot:**
- New Logo ARR
- Expansion ARR
- SQL (Total)
- New Logo Pipeline Created
- Win Rate (Overall), Win Rate (SAL), Win Rate (AEC)
""")

st.info("""
**How HubSpot Sync Works:**

Since you're running this app locally, HubSpot data sync happens through Claude:

1. Ask Claude to sync HubSpot data: "Refresh HubSpot KPIs for Q1 2026"
2. Claude will use HubSpot MCP tools to fetch deal data
3. Claude will process the data using existing scripts
4. Claude will save the calculated KPIs to the database
5. Refresh this dashboard to see updated data

**Note:** In a cloud deployment, this could be automated with scheduled jobs.
""")

# Show last sync time (mock for now)
if 'last_hubspot_sync' not in st.session_state:
    st.session_state.last_hubspot_sync = None

if st.session_state.last_hubspot_sync:
    st.success(f"Last synced: {st.session_state.last_hubspot_sync}")
else:
    st.warning("HubSpot data has not been synced yet")

# Manual sync button (placeholder - requires Claude intervention)
if st.button("📥 Request HubSpot Sync"):
    st.info("""
    To sync HubSpot data, please ask Claude:

    **"Please sync HubSpot KPIs for Q1 2026 and save to the database"**

    Claude will:
    1. Fetch deal data from HubSpot using MCP tools
    2. Calculate KPIs using the existing scripts
    3. Save results to the database
    4. Confirm when complete
    """)

st.markdown("---")

# Google Sheets Sync
st.subheader("📊 Google Sheets Sync (Engineering & Support KPIs)")

CREDENTIALS_FILE = Path(__file__).parent.parent / "google_credentials.json"
creds_exist = CREDENTIALS_FILE.exists()

col_gs1, col_gs2 = st.columns([2, 1])

with col_gs1:
    st.markdown("""
    **KPIs pulled from Google Sheets:**
    - Tickets out of SLA
    - Data OPS Tickets missing deadline
    - Tickets Created (Week)
    - Tickets Resolved in Tier 1 within SLA
    - AI Coded %
    - 30-day Response Rate (Overall & excl. Express)
    - Emails & SMS Sent
    - MS Placement in Box
    - Survey Click Rate (30-day)
    """)

with col_gs2:
    if creds_exist:
        st.success("✅ Credentials found")
    else:
        st.warning("⚠️ No credentials file")
        st.caption("Add `google_credentials.json`\nto the project root folder")

if not creds_exist:
    with st.expander("🔑 How to set up Google Sheets access"):
        st.markdown("""
        **One-time setup:**

        1. Go to [Google Cloud Console](https://console.cloud.google.com/)
        2. Create a project → Enable **Google Sheets API** and **Google Drive API**
        3. Create a **Service Account** → Download the credentials JSON
        4. Save it as **`google_credentials.json`** in the KPI Dashboard folder
        5. Open your Google Sheet → Share it (View only) with the service account email

        The service account email looks like:
        `your-service@your-project.iam.gserviceaccount.com`
        """)

quarter_gs = st.session_state.get('current_quarter', 'Q1')
year_gs    = st.session_state.get('current_year', 2026)

if st.button("📊 Sync Google Sheet KPIs Now", disabled=not creds_exist):
    try:
        import subprocess
        script_path = Path(__file__).parent.parent / "scripts" / "fetch_google_sheet_kpis.py"
        with st.spinner("Fetching from Google Sheets..."):
            result = subprocess.run(
                ["python3", str(script_path), quarter_gs, str(year_gs)],
                capture_output=True, text=True,
                cwd=str(Path(__file__).parent.parent)
            )
        if result.returncode == 0:
            st.success("✅ Google Sheets sync complete!")
            st.text(result.stdout)
            st.session_state.last_sheet_sync = datetime.now().strftime("%b %d, %Y %I:%M %p")
        else:
            st.error("Sync failed:")
            st.code(result.stderr)
    except Exception as e:
        st.error(f"Error: {e}")

if 'last_sheet_sync' in st.session_state:
    st.caption(f"Last synced: {st.session_state.last_sheet_sync}")

st.markdown("---")

# Renewal Analysis Sheet Sync
st.subheader("📈 Renewal Analysis Sheet Sync")

RENEWAL_CREDS = CREDENTIALS_FILE  # same service account

st.markdown("""
**KPIs pulled from Renewal Analysis sheet:**
- NRR (cell H2)
- High Risk Accounts — Next 6 Months (J24)
- High Risk Account ARR — Next 6 Months (J12)
- Account Risk — Low Surveys Sent (J42)
- Account Risk — Product Issues (J47)
- Account Risk — Support Issues (J48)
- Account Risk — Response Rate Issues (J48)
- ARR at Risk — Product Issues (sum of D55, D60, D61, D62)
""")

if st.button("📈 Sync Renewal Analysis KPIs", disabled=not creds_exist):
    try:
        import subprocess
        renewal_script = Path(__file__).parent.parent / "scripts" / "fetch_renewal_sheet_kpis.py"
        with st.spinner("Fetching from Renewal Analysis sheet…"):
            result = subprocess.run(
                ["python3", str(renewal_script), quarter_gs, str(year_gs)],
                capture_output=True, text=True,
                cwd=str(Path(__file__).parent.parent),
            )
        if result.returncode == 0:
            st.success("✅ Renewal sheet sync complete!")
            st.text(result.stdout)
            st.session_state.last_renewal_sync = datetime.now().strftime("%b %d, %Y %I:%M %p")
        else:
            st.error("Sync failed:")
            st.code(result.stderr)
    except Exception as e:
        st.error(f"Error: {e}")

if 'last_renewal_sync' in st.session_state:
    st.caption(f"Last synced: {st.session_state.last_renewal_sync}")

st.markdown("---")

# Data Export
st.subheader("📥 Data Export")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Export All KPIs**")

    quarter = st.session_state.get('current_quarter', 'Q1')
    year = st.session_state.get('current_year', 2026)

    kpis_df = db.get_latest_kpis(quarter, year)

    if not kpis_df.empty:
        csv_kpis = kpis_df.to_csv(index=False)
        st.download_button(
            label="📥 Download KPIs CSV",
            data=csv_kpis,
            file_name=f"kpis_{quarter}_{year}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        st.caption(f"{len(kpis_df)} KPIs available for export")
    else:
        st.info("No KPI data to export")

with col2:
    st.markdown("**Export Action Items**")

    actions = db.get_actions()

    if actions:
        # Convert to DataFrame
        actions_data = [a.to_dict() for a in actions]
        actions_df = pd.DataFrame(actions_data)

        csv_actions = actions_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Actions CSV",
            data=csv_actions,
            file_name=f"actions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        st.caption(f"{len(actions)} actions available for export")
    else:
        st.info("No action items to export")

st.markdown("---")

# Action Items Import
st.subheader("✅ Action Items Import")

col_ai1, col_ai2 = st.columns([2, 1])

with col_ai1:
    st.markdown("""
    **Import action items from ClearlyRated team sheet**

    Loads the 26 action items from the Q1 2026 team sheet into the database.
    Safe to re-run — skips items that already exist.
    """)

    if st.button("📥 Import Action Items"):
        try:
            import subprocess
            import_script = Path(__file__).parent.parent / "scripts" / "import_action_items.py"
            with st.spinner("Importing action items…"):
                result = subprocess.run(
                    ["python3", str(import_script)],
                    capture_output=True, text=True,
                    cwd=str(Path(__file__).parent.parent),
                )
            if result.returncode == 0:
                st.success(f"✅ {result.stdout.strip()}")
            else:
                st.error("Import failed:")
                st.code(result.stderr)
        except Exception as e:
            st.error(f"Error: {e}")

with col_ai2:
    actions_count = len(db.get_actions())
    st.metric("Actions in DB", actions_count)

st.markdown("---")

# Database Information
st.subheader("📊 Database Information")

col1, col2, col3 = st.columns(3)

# Get database stats
kpis = db.get_kpis()
all_actions = db.get_actions()
targets = db.get_targets()

with col1:
    st.metric("Total KPI Entries", len(kpis))

with col2:
    st.metric("Total Actions", len(all_actions))

with col3:
    st.metric("Targets Configured", len(targets))

# Database location
import os
db_path = os.path.join(Path(__file__).parent.parent, 'database', 'kpi_dashboard.db')
st.caption(f"**Database Location:** `{db_path}`")

st.markdown("---")

# Application Info
st.subheader("ℹ️ Application Information")

st.markdown(f"""
**KPI Dashboard v1.0**

- **Framework:** Streamlit {st.__version__}
- **Database:** SQLite
- **Charts:** Plotly
- **Deployment:** Local

**Support:**
- Check the main README for documentation
- Report issues or request features through your development process
""")

st.markdown("---")

# Advanced Settings (Future)
with st.expander("🔧 Advanced Settings"):
    st.markdown("""
    **Future Enhancements:**
    - User management (add/remove users, roles)
    - Automated HubSpot sync scheduling
    - Email notifications for off-track KPIs
    - Custom KPI definitions
    - Theme customization
    - Backup/restore database

    These features can be added as the application matures.
    """)
