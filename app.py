"""
CR Pulse — ClearlyRated KPI Dashboard
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
from PIL import Image
from database.db import get_db
from auth.google_auth import is_authenticated, login_page, current_user, logout

_favicon_path = Path(__file__).parent / "assets" / "pulse-logo.png"
_favicon = Image.open(_favicon_path) if _favicon_path.exists() else "📊"

st.set_page_config(
    page_title="CR Pulse",
    page_icon=_favicon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global brand CSS (ClearlyRated Brand Style Guide 2025) ──────────────────────
st.markdown("""
<style>
/* Inter — closest web-safe match to ClearlyRated's Matter grotesque font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stMarkdown, button, label, input, textarea, select {
    font-family: 'Inter', sans-serif !important;
}

/* ── Sidebar: Green/500 dark teal background ─────────────────────────── */
[data-testid="stSidebar"] > div:first-child {
    background-color: #094C3D;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stMarkdown {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] .stSubheader {
    color: #C6FF7E !important;
    font-weight: 600;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(198,255,126,0.25) !important;
}
[data-testid="stSidebar"] .stInfo {
    background-color: rgba(198,255,126,0.12);
    border: 1px solid rgba(198,255,126,0.3);
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: rgba(255,255,255,0.1);
    border-color: rgba(255,255,255,0.25);
    color: #FFFFFF;
}

/* ── Primary button: Lime Green (#C6FF7E) with dark text ─────────────── */
button[kind="primary"] {
    background-color: #C6FF7E !important;
    color: #171717 !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 4px !important;
}
button[kind="primary"]:hover {
    background-color: #0F7D64 !important;
    color: #FFFFFF !important;
}

/* ── Headings: brand teal ────────────────────────────────────────────── */
h1 { color: #0F7D64 !important; font-weight: 700; }
h2 { color: #0B5846 !important; font-weight: 600; }
h3 { color: #0F7D64 !important; font-weight: 600; }

/* ── Metric cards: white with subtle shadow ──────────────────────────── */
[data-testid="metric-container"] {
    background-color: #FFFFFF;
    border: 1px solid #F2F2F2;
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 1px 4px rgba(9,76,61,0.08);
}

/* ── Dataframe / table borders ───────────────────────────────────────── */
[data-testid="stDataFrame"] > div {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #EFEFEF;
}

/* ── Tab active state ────────────────────────────────────────────────── */
[data-baseweb="tab"][aria-selected="true"] {
    color: #0F7D64 !important;
    border-bottom-color: #0F7D64 !important;
}

/* ── Progress bar: lime green fill ──────────────────────────────────── */
[data-testid="stProgress"] > div > div {
    background-color: #C6FF7E;
}
</style>
""", unsafe_allow_html=True)

# ── Authentication gate ──────────────────────────────────────────────────────────
if not is_authenticated():
    login_page()
    st.stop()

# ── Navigation (Streamlit 1.36+ explicit nav — controls sidebar labels) ─────────
pg = st.navigation(
    pages=[
        st.Page("app_home.py",                       title="CR Pulse",     default=True),
        st.Page("pages/1_📊_Dashboard.py",            title="Dashboard"),
        st.Page("pages/2_📁_Strategic_Initiatives.py", title="Strategic Initiatives"),
        st.Page("pages/4_⚙️_Settings.py",             title="Settings"),
    ],
    position="sidebar",
)

# ── Database init ───────────────────────────────────────────────────────────────
if 'db_initialized' not in st.session_state:
    try:
        db = get_db()
        db.create_tables()
        st.session_state.db_initialized = True
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        st.stop()

# ── Quarter/Year session defaults ──────────────────────────────────────────────
if 'current_quarter' not in st.session_state:
    m = datetime.now().month
    st.session_state.current_quarter = "Q1" if m <= 3 else "Q2" if m <= 6 else "Q3" if m <= 9 else "Q4"

if 'current_year' not in st.session_state:
    st.session_state.current_year = datetime.now().year

# ── Sidebar (runs for every page) ───────────────────────────────────────────────
logo_path = Path(__file__).parent / "assets" / "pulse-logo.png"
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Period")
quarter = st.sidebar.selectbox(
    "Quarter", ["Q1", "Q2", "Q3", "Q4"],
    index=["Q1", "Q2", "Q3", "Q4"].index(st.session_state.current_quarter)
)
year = st.sidebar.selectbox(
    "Year", [2024, 2025, 2026, 2027],
    index=[2024, 2025, 2026, 2027].index(st.session_state.current_year)
)

st.session_state.current_quarter = quarter
st.session_state.current_year    = year

st.sidebar.markdown("---")
st.sidebar.info(f"**Period:** {quarter} {year}")

# ── User info + logout ───────────────────────────────────────────────────────────
user = current_user()
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<div style='font-size:0.8rem; color:rgba(255,255,255,0.7); margin-bottom:4px;'>"
    f"Signed in as</div>"
    f"<div style='font-size:0.85rem; color:#C6FF7E; font-weight:500; margin-bottom:8px;'>"
    f"{user.get('name', user.get('email', ''))}</div>",
    unsafe_allow_html=True,
)
if st.sidebar.button("Sign Out", use_container_width=True):
    logout()
    st.rerun()

# ── Run current page ────────────────────────────────────────────────────────────
pg.run()
