"""
Google OAuth 2.0 authentication — restricted to @clearlyrated.com accounts.

Setup (one-time):
  1. Go to https://console.cloud.google.com → APIs & Services → Credentials
  2. Create OAuth 2.0 Client ID (type: Web application)
  3. Add Authorized redirect URI:  http://localhost:8501  (and your ngrok URL)
  4. Copy Client ID and Secret into .env (see .env.example)
"""

import json
import os
import time
from urllib.parse import urlencode
from pathlib import Path

import requests as http_requests
import streamlit as st
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# ── Config ──────────────────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).parent.parent / ".env"
_TOKEN_PATH = Path(__file__).parent.parent / ".auth_token.json"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES          = "openid email profile"
TOKEN_MAX_AGE   = 30 * 24 * 60 * 60  # 30 days in seconds


def _get_secret(key: str, default: str = "") -> str:
    """Read from st.secrets (Streamlit Cloud) first, then os.getenv (local)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, AttributeError):
        return os.getenv(key, default).strip()


# ── Token persistence ────────────────────────────────────────────────────────────
def _save_token(email: str, name: str, picture: str):
    """Save auth token to disk for 30-day persistence."""
    data = {
        "email": email,
        "name": name,
        "picture": picture,
        "created_at": time.time(),
    }
    _TOKEN_PATH.write_text(json.dumps(data))


def _load_token() -> dict | None:
    """Load saved token if it exists and hasn't expired (30 days)."""
    if not _TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(_TOKEN_PATH.read_text())
        age = time.time() - data.get("created_at", 0)
        if age > TOKEN_MAX_AGE:
            _TOKEN_PATH.unlink(missing_ok=True)
            return None
        if not data.get("email", "").endswith(f"@{_get_secret('ALLOWED_DOMAIN')}"):
            _TOKEN_PATH.unlink(missing_ok=True)
            return None
        return data
    except (json.JSONDecodeError, KeyError):
        _TOKEN_PATH.unlink(missing_ok=True)
        return None


def _clear_token():
    """Remove saved token file."""
    _TOKEN_PATH.unlink(missing_ok=True)


# ── Helpers ─────────────────────────────────────────────────────────────────────
def _cfg():
    """Return (client_id, client_secret, redirect_uri) from st.secrets or env."""
    load_dotenv(_ENV_PATH, override=True)
    client_id     = _get_secret("GOOGLE_CLIENT_ID")
    client_secret = _get_secret("GOOGLE_CLIENT_SECRET")
    redirect_uri  = _get_secret("OAUTH_REDIRECT_URI", "http://localhost:8501")
    if not client_id or not client_secret:
        st.error(
            "Google OAuth is not configured. "
            "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file."
        )
        st.stop()
    return client_id, client_secret, redirect_uri


def _auth_url() -> str:
    client_id, _, redirect_uri = _cfg()
    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
    }
    return GOOGLE_AUTH_URL + "?" + urlencode(params)


def _exchange_code(code: str) -> dict:
    """Exchange the authorization code for tokens. Returns the token JSON dict."""
    client_id, client_secret, redirect_uri = _cfg()
    resp = http_requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── Public API ──────────────────────────────────────────────────────────────────
def is_authenticated() -> bool:
    """True if the current session has a valid, domain-verified user."""
    # Check session state first
    if (
        st.session_state.get("authenticated", False)
        and st.session_state.get("user_email", "").endswith(f"@{_get_secret('ALLOWED_DOMAIN')}")
    ):
        return True

    # Try restoring from saved token
    token = _load_token()
    if token:
        st.session_state["authenticated"] = True
        st.session_state["user_email"]    = token["email"]
        st.session_state["user_name"]     = token.get("name", "")
        st.session_state["user_picture"]  = token.get("picture", "")
        return True

    return False


def current_user() -> dict:
    """Return {name, email, picture} for the logged-in user, or empty dict."""
    if not is_authenticated():
        return {}
    return {
        "name":    st.session_state.get("user_name", ""),
        "email":   st.session_state.get("user_email", ""),
        "picture": st.session_state.get("user_picture", ""),
    }


def logout():
    _clear_token()
    for key in ("authenticated", "user_email", "user_name", "user_picture", "auth_error"):
        st.session_state.pop(key, None)


def _handle_callback() -> bool:
    """Process the OAuth callback. Returns True on success, False on failure."""
    params = st.query_params
    if "code" not in params:
        return False

    client_id = _cfg()[0]
    try:
        token_data = _exchange_code(params["code"])
        st.query_params.clear()

        id_info = id_token.verify_oauth2_token(
            token_data["id_token"],
            google_requests.Request(),
            client_id,
        )

        email  = id_info.get("email", "")
        domain = email.split("@")[-1] if "@" in email else ""

        if domain != _get_secret('ALLOWED_DOMAIN'):
            st.session_state["auth_error"] = (
                f"Access denied — only **@{ALLOWED_DOMAIN}** accounts can sign in. "
                f"You signed in as **{email}**."
            )
            return False

        name    = id_info.get("name", email.split("@")[0])
        picture = id_info.get("picture", "")

        st.session_state["authenticated"] = True
        st.session_state["user_email"]    = email
        st.session_state["user_name"]     = name
        st.session_state["user_picture"]  = picture

        # Persist to disk for 30 days
        _save_token(email, name, picture)
        return True

    except Exception as exc:
        st.query_params.clear()
        st.session_state["auth_error"] = f"Authentication failed: {exc}"
        return False


def login_page():
    """Render the login screen. Call st.stop() after this to block further rendering."""
    # Process OAuth callback if Google redirected back with a code
    if "code" in st.query_params:
        if _handle_callback():
            st.rerun()
        # On failure, fall through to show the error + login button again

    # ── Hide sidebar on login page ───────────────────────────────────────────
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        header, footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Layout: centred card ─────────────────────────────────────────────────
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        logo_path = Path(__file__).parent.parent / "assets" / "pulse-logo.png"
        if logo_path.exists():
            li, lc, ri = st.columns([1, 2, 1])
            with lc:
                st.image(str(logo_path), use_container_width=True)

        st.markdown(
            """
            <div style="text-align:center; margin:16px 0 28px;">
                <h2 style="color:#0F7D64; margin-bottom:4px; font-size:1.8rem;">CR Pulse</h2>
                <p style="color:#666; font-size:0.95rem; margin:0;">
                    ClearlyRated KPI Dashboard
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Error message (domain mismatch, token failure, etc.)
        if "auth_error" in st.session_state:
            st.error(st.session_state.pop("auth_error"))

        # Google Sign-In button
        auth_url = _auth_url()
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; margin-top:8px;">
                <a href="{auth_url}" style="
                    display:inline-flex; align-items:center; gap:12px;
                    background:#FFFFFF; color:#3C4043;
                    border:1px solid #DADCE0; border-radius:6px;
                    padding:12px 32px; font-size:0.95rem; font-weight:500;
                    text-decoration:none;
                    box-shadow:0 1px 3px rgba(60,64,67,0.15), 0 1px 2px rgba(60,64,67,0.3);
                    transition:box-shadow 0.2s;
                ">
                    <svg width="20" height="20" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                        <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"/>
                        <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"/>
                        <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"/>
                        <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"/>
                    </svg>
                    Sign in with Google
                </a>
            </div>
            <div style="text-align:center; margin-top:20px; color:#929292; font-size:0.82rem;">
                Access restricted to authorized company accounts
            </div>
            """,
            unsafe_allow_html=True,
        )
