"""
ClearlyRated Color Palette — exact values from Brand Style Guide 2025
"""

# ── Primary Green Scale ───────────────────────────────────────────────────────
GREEN_LIGHT   = "#C6FF7E"   # Green Light / buttons highlight
GREEN_50      = "#E7F2F0"   # Green/50  — very light tint
GREEN_75      = "#9DCABF"   # Green/75
GREEN_100     = "#74B4A5"   # Green/100
GREEN_200     = "#38937E"   # Green/200
GREEN_300     = "#0F7D64"   # Green/300 ★ brand primary
GREEN_400     = "#0B5846"   # Green/400
GREEN_500     = "#094C3D"   # Green/500 — darkest teal (sidebar bg)

# ── Secondary Palette ─────────────────────────────────────────────────────────
RED           = "#E75944"   # Alert / behind
TEAL          = "#7EEFE9"   # Secondary teal accent
CYAN          = "#01BFA5"   # Cyan
PURPLE        = "#473CAA"   # Purple
BEIGE         = "#E8E5E3"   # Beige
BROWN         = "#623B28"   # Brown

# ── Neutral Scale ─────────────────────────────────────────────────────────────
DARK_GREY     = "#171717"   # Body text
NEUTRAL_200   = "#F2F2F2"   # Light bg
NEUTRAL_300   = "#EFEFEF"   # Borders/dividers
NEUTRAL_400   = "#A7A7A7"   # Placeholder text
NEUTRAL_500   = "#929292"   # Secondary text
NEUTRAL_600   = "#666666"   # Muted text
WHITE         = "#FFFFFF"

# ── Semantic aliases (used throughout the app) ────────────────────────────────
PRIMARY_TEAL        = GREEN_300
ACCENT_LIME         = GREEN_LIGHT
ACCENT_CYAN         = TEAL
ALERT_RED           = RED
ALERT_YELLOW        = "#FFC857"    # Not in brand guide — kept for caution states
LIGHT_GREY          = "#F6F6F6"    # Neutral/100
MEDIUM_GREY         = NEUTRAL_500
SIDEBAR_BG          = GREEN_500

# ── Status colors ─────────────────────────────────────────────────────────────
STATUS_GREEN  = GREEN_300
STATUS_YELLOW = ALERT_YELLOW
STATUS_RED    = RED

# ── Chart colors ─────────────────────────────────────────────────────────────
CHART_TARGET  = NEUTRAL_400
CHART_ACTUAL  = GREEN_300
CHART_GRID    = NEUTRAL_300


def get_status_color(variance_pct: float, inverse: bool = False) -> str:
    if inverse:
        return STATUS_GREEN if variance_pct <= 70 else STATUS_YELLOW if variance_pct <= 90 else STATUS_RED
    return STATUS_GREEN if variance_pct >= 90 else STATUS_YELLOW if variance_pct >= 70 else STATUS_RED


def get_status_emoji(variance_pct: float, inverse: bool = False) -> str:
    if inverse:
        return "🟢" if variance_pct <= 70 else "🟡" if variance_pct <= 90 else "🔴"
    return "🟢" if variance_pct >= 90 else "🟡" if variance_pct >= 70 else "🔴"


def get_status_text(variance_pct: float, inverse: bool = False) -> str:
    if inverse:
        return "On Track" if variance_pct <= 70 else "At Risk" if variance_pct <= 90 else "Behind"
    return "On Track" if variance_pct >= 90 else "At Risk" if variance_pct >= 70 else "Behind"
