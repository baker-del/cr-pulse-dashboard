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

/* ── Sidebar nav section headers ──────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    color: rgba(198,255,126,0.6) !important;
    text-transform: uppercase;
    padding: 12px 0 4px 0;
}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
    border-radius: 6px !important;
    margin: 1px 4px !important;
    padding: 6px 12px !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"] {
    background-color: rgba(198,255,126,0.15) !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
    background-color: rgba(255,255,255,0.08) !important;
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
    pages={
        "": [
            st.Page("app_home.py", title="Home", icon="🏠", default=True),
        ],
        "DASHBOARDS": [
            st.Page("pages/1_📊_Dashboard.py", title="KPI Dashboard", icon="📊"),
            st.Page("pages/3_📈_SM_Efficiency.py", title="S&M Efficiency", icon="📈"),
        ],
        "STRATEGY": [
            st.Page("pages/2_📁_Strategic_Initiatives.py", title="Initiatives", icon="📁"),
        ],
        "ADMIN": [
            st.Page("pages/4_⚙️_Settings.py", title="Settings", icon="⚙️"),
        ],
    },
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
st.sidebar.markdown(
    '<div style="padding:8px 0 12px 0; white-space:nowrap;">'
    '<span style="font-size:1.4rem; font-weight:800; color:#C6FF7E; letter-spacing:-0.5px;">CR Pulse</span><br/>'
    '<span style="font-size:0.65rem; color:rgba(255,255,255,0.5);">by ClearlyRated</span>'
    '</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")

# Period selector — compact inline
col_q, col_y = st.sidebar.columns(2)
quarter = col_q.selectbox(
    "Quarter", ["Q1", "Q2", "Q3", "Q4"],
    index=["Q1", "Q2", "Q3", "Q4"].index(st.session_state.current_quarter),
    label_visibility="collapsed",
)
year = col_y.selectbox(
    "Year", [2024, 2025, 2026, 2027],
    index=[2024, 2025, 2026, 2027].index(st.session_state.current_year),
    label_visibility="collapsed",
)

st.session_state.current_quarter = quarter
st.session_state.current_year    = year

st.sidebar.markdown(
    f'<div style="background:rgba(198,255,126,0.12); border:1px solid rgba(198,255,126,0.3); '
    f'border-radius:6px; padding:8px 12px; margin:8px 0; text-align:center;">'
    f'<span style="font-size:0.9rem; font-weight:600; color:#C6FF7E;">{quarter} {year}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── User info + logout ───────────────────────────────────────────────────────────
user = current_user()
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<div style='font-size:0.75rem; color:rgba(255,255,255,0.5); margin-bottom:2px;'>"
    f"Signed in as</div>"
    f"<div style='font-size:0.82rem; color:#C6FF7E; font-weight:500; margin-bottom:8px;'>"
    f"{user.get('name', user.get('email', ''))}</div>",
    unsafe_allow_html=True,
)
if st.sidebar.button("Sign Out", use_container_width=True):
    logout()
    st.rerun()

# ── Run current page ────────────────────────────────────────────────────────────
pg.run()
