"""
KPI Calculation Utilities

Handles variance calculations, status determination, and data parsing
"""

from typing import Optional, Tuple
import re


def parse_numeric_value(value) -> Optional[float]:
    """
    Parse a value that might be a string with $, %, commas, etc.

    Args:
        value: Value to parse (string, int, float)

    Returns:
        Float value or None if cannot parse
    """
    if value is None or value == '':
        return None

    # Handle different types
    if isinstance(value, (int, float)):
        return float(value)

    # Convert to string and clean
    value_str = str(value).strip()
    if not value_str:
        return None

    # Remove common formatting
    value_str = value_str.replace('$', '').replace(',', '').replace('%', '')
    value_str = value_str.replace('<', '').replace('>', '').replace('=', '').strip()

    try:
        return float(value_str)
    except ValueError:
        return None


def calculate_variance(
    actual: any,
    target: any,
    is_percentage_target: bool = False,
    is_inverse: bool = False
) -> Tuple[Optional[float], str, str]:
    """
    Calculate variance between actual and target values

    Args:
        actual: Actual value
        target: Target value
        is_percentage_target: If True, target is a percentage (e.g., "15%")
        is_inverse: If True, lower is better (e.g., for cost metrics)

    Returns:
        Tuple of (variance_pct, status, emoji)
        - variance_pct: Percentage achieved (or None if cannot calculate)
        - status: "On Track", "At Risk", or "Behind"
        - emoji: Status emoji
    """
    actual_num = parse_numeric_value(actual)
    target_num = parse_numeric_value(target)

    if actual_num is None or target_num is None:
        return None, "", ""

    # Special case: zero target (e.g., Incidents — goal is zero)
    if target_num == 0:
        if actual_num == 0:
            return 100.0, "On Track", "🟢"
        else:
            return 0.0, "Behind", "🔴"

    # Special case: negative target (e.g., Employee NPS -35, Cash EBITDA -$416K)
    # Higher is still better; use percentage gap relative to the target magnitude.
    # Gap thresholds: ≤10% → On Track, 10-30% → At Risk, >30% → Behind
    if target_num < 0:
        if actual_num >= target_num:
            return 100.0, "On Track", "🟢"
        else:
            gap_pct = abs(actual_num - target_num) / abs(target_num) * 100
            if gap_pct <= 10:
                return round(100.0 - gap_pct, 1), "On Track", "🟢"
            elif gap_pct <= 30:
                return round(100.0 - gap_pct, 1), "At Risk", "🟡"
            else:
                return round(100.0 - gap_pct, 1), "Behind", "🔴"

    # Normal case: calculate variance percentage
    variance_pct = (actual_num / target_num) * 100

    # Determine status based on variance
    if is_inverse:
        # Lower is better (e.g., cost, error rate)
        # Mirror normal-KPI thresholds but flipped:
        #   ≤110% of target (within 10% over) → On Track
        #   110–130% of target                → At Risk
        #   >130% of target                   → Behind
        if variance_pct <= 110:
            status = "On Track"
            emoji = "🟢"
        elif variance_pct <= 130:
            status = "At Risk"
            emoji = "🟡"
        else:
            status = "Behind"
            emoji = "🔴"
    else:
        # Higher is better (most KPIs)
        if variance_pct >= 90:
            status = "On Track"
            emoji = "🟢"
        elif variance_pct >= 70:
            status = "At Risk"
            emoji = "🟡"
        else:
            status = "Behind"
            emoji = "🔴"

    return variance_pct, status, emoji


def calculate_pace_status(
    actual: any,
    target: any,
    pct_elapsed: float,
) -> Tuple[Optional[float], str, str]:
    """
    Status for accumulation KPIs (ARR, pipeline, SQLs) based on pace-to-date.

    Expected-to-date = target × pct_elapsed.
    Compare actual against that expected value.
    """
    actual_num = parse_numeric_value(actual)
    target_num = parse_numeric_value(target)

    if actual_num is None or target_num is None or target_num == 0 or pct_elapsed == 0:
        return None, "", ""

    expected_to_date = target_num * pct_elapsed
    pace_pct = (actual_num / expected_to_date) * 100

    # Late-quarter tightening: when >80% of quarter elapsed, also check
    # if actual can realistically reach the full target. If actual is <85%
    # of the FULL target with <20% of time left, flag as At Risk.
    late_quarter = pct_elapsed >= 0.80
    full_target_pct = (actual_num / target_num) * 100 if target_num > 0 else 0

    if late_quarter and full_target_pct < 85:
        # Late in quarter and significantly behind full target
        if full_target_pct < 70:
            return pace_pct, "Behind", "🔴"
        else:
            return pace_pct, "At Risk", "🟡"

    if pace_pct >= 90:
        return pace_pct, "On Track", "🟢"
    elif pace_pct >= 70:
        return pace_pct, "At Risk", "🟡"
    else:
        return pace_pct, "Behind", "🔴"


def format_value(value: any, is_currency: bool = False, is_percentage: bool = False) -> str:
    """
    Format a value for display

    Args:
        value: Value to format
        is_currency: If True, format as currency
        is_percentage: If True, format as percentage

    Returns:
        Formatted string
    """
    num = parse_numeric_value(value)

    if num is None:
        return str(value) if value else ""

    if is_currency:
        return f"${num:,.0f}"
    elif is_percentage:
        return f"{num:.1f}%"
    else:
        # Check if it's a whole number
        if num == int(num):
            return f"{int(num):,}"
        else:
            return f"{num:,.2f}"


def infer_value_type(value_str: str) -> Tuple[bool, bool]:
    """
    Infer if a value is currency or percentage

    Args:
        value_str: String representation of value

    Returns:
        Tuple of (is_currency, is_percentage)
    """
    if not value_str:
        return False, False

    value_str = str(value_str)
    is_currency = '$' in value_str
    is_percentage = '%' in value_str

    return is_currency, is_percentage


_INVERSE_KPI_NAMES = {
    '30-day Response Rate (Overall)',
    '30-day Response Rate excluding Express',
    'Tickets out of SLA',
    'Data OPS Tickets missing deadline',
}


def is_inverse_kpi(kpi_name: str) -> bool:
    """
    Determine if a KPI is inverse (lower is better)

    Args:
        kpi_name: Name of the KPI

    Returns:
        True if lower is better
    """
    if kpi_name in _INVERSE_KPI_NAMES:
        return True

    inverse_keywords = [
        'risk', 'cost', 'error', 'incident', 'missing', 'churn', 'late'
    ]

    kpi_lower = kpi_name.lower()
    return any(keyword in kpi_lower for keyword in inverse_keywords)


def get_quarter_from_date(date_str: str) -> str:
    """
    Get quarter (Q1-Q4) from a date string

    Args:
        date_str: Date string (YYYY-MM-DD)

    Returns:
        Quarter string (Q1, Q2, Q3, Q4)
    """
    if not date_str:
        return ""

    try:
        # Extract month
        if '-' in date_str:
            parts = date_str.split('-')
            month = int(parts[1])
        elif '/' in date_str:
            parts = date_str.split('/')
            month = int(parts[0] if len(parts[0]) <= 2 else parts[1])
        else:
            return ""

        # Map month to quarter
        if month <= 3:
            return "Q1"
        elif month <= 6:
            return "Q2"
        elif month <= 9:
            return "Q3"
        else:
            return "Q4"
    except:
        return ""


def get_week_number(date_str: str) -> Optional[int]:
    """
    Get week number from a date string

    Args:
        date_str: Date string (YYYY-MM-DD)

    Returns:
        Week number (1-52) or None
    """
    try:
        from datetime import datetime
        date_obj = datetime.fromisoformat(date_str.replace('/', '-'))
        return date_obj.isocalendar()[1]
    except:
        return None
