"""
Manual KPI Entry Page

Allows users to manually enter KPI values that cannot be auto-captured
"""

import streamlit as st
from datetime import datetime, date
from database.db import get_db
from utils.kpi_calculator import calculate_variance, get_quarter_from_date, get_week_number


# Get current period
quarter = st.session_state.get('current_quarter', 'Q1')
year = st.session_state.get('current_year', 2026)

st.title("✏️ Manual KPI Entry")
st.markdown(f"Enter KPI data for **{quarter} {year}**")
st.markdown("---")

# Manual entry KPIs (not auto-captured from HubSpot)
MANUAL_KPI_LIST = [
    "Employee NPS",
    "Renewal Risk ($ at Risk in Next 180 Days)",
    "Core Product Adoption (Workflow Penetration)",
    "CFT - Monthly Active Users",
    "CRS - Monthly Active Users",
    "Total Surveys Sent",
    "30-day Response Rate excluding Express",
    "Tickets Resolved in Tier 1 within SLA",
    "Data OPS Tickets missing deadline",
    "Incidents",
    "Cash EBITDA (Plan vs. Variance)"
]

# Get database
db = get_db()

# Entry Form
st.subheader("Enter KPI Data")

col1, col2 = st.columns([2, 1])

with col1:
    selected_kpi = st.selectbox(
        "Select KPI",
        MANUAL_KPI_LIST,
        help="Choose the KPI you want to enter data for"
    )

with col2:
    entry_date = st.date_input(
        "Date",
        value=date.today(),
        help="Date for this KPI entry"
    )

# Get target for this KPI
target_obj = db.get_target(selected_kpi, year)

if target_obj:
    # Determine which quarter target to use
    quarter_field = f"{quarter.lower()}_target"
    target_value = getattr(target_obj, quarter_field, "")
    owner = target_obj.owner
else:
    target_value = ""
    owner = ""

# Display KPI info
col1, col2, col3 = st.columns(3)

with col1:
    st.info(f"**Owner:** {owner or 'Not specified'}")

with col2:
    st.info(f"**Target ({quarter}):** {target_value or 'Not set'}")

with col3:
    # Determine cadence based on KPI
    if 'NPS' in selected_kpi or 'EBITDA' in selected_kpi:
        cadence = 'Quarterly'
    elif 'Active Users' in selected_kpi or 'Response Rate' in selected_kpi:
        cadence = 'Weekly'
    else:
        cadence = 'Monthly'
    st.info(f"**Cadence:** {cadence}")

st.markdown("---")

# Value entry
col1, col2 = st.columns([1, 2])

with col1:
    actual_value = st.text_input(
        "Actual Value",
        help="Enter the actual value (can include $, %, commas)"
    )

with col2:
    comments = st.text_area(
        "Comments (Optional)",
        help="Add any notes or context about this KPI",
        height=100
    )

# Calculate variance if both values exist
variance_display = ""
status = ""
variance_pct = None

if actual_value and target_value:
    variance_pct, status, emoji = calculate_variance(actual_value, target_value)
    if variance_pct is not None:
        variance_display = f"{emoji} {variance_pct:.1f}% of target - {status}"
        st.metric("Status", variance_display)

# Save button
if st.button("💾 Save Entry", type="primary"):
    if not actual_value:
        st.error("Please enter an actual value")
    else:
        try:
            # Prepare KPI data
            kpi_data = {
                'kpi_name': selected_kpi,
                'owner': owner,
                'cadence': cadence,
                'quarter': quarter,
                'year': year,
                'week_number': get_week_number(entry_date.isoformat()),
                'date': entry_date,
                'target_value': target_value,
                'actual_value': actual_value,
                'status': status,
                'variance_pct': variance_pct,
                'source': 'Manual',
                'comments': comments,
                'updated_by': 'User'  # Would be actual username with auth
            }

            # Save to database
            db.save_kpi(kpi_data)

            st.success(f"✅ Successfully saved {selected_kpi} for {entry_date}")
            st.balloons()

        except Exception as e:
            st.error(f"Error saving KPI: {e}")

st.markdown("---")

# Recent Entries
st.subheader("Recent Manual Entries")

# Get recent manual entries
recent_kpis = db.get_kpis(quarter=quarter, year=year)
manual_kpis = [kpi for kpi in recent_kpis if kpi.source == 'Manual']

if manual_kpis:
    # Convert to DataFrame for display
    recent_data = []
    for kpi in manual_kpis[:10]:  # Show last 10
        recent_data.append({
            'KPI': kpi.kpi_name,
            'Date': kpi.date.strftime('%Y-%m-%d') if kpi.date else '',
            'Value': kpi.actual_value,
            'Target': kpi.target_value,
            'Status': f"{kpi.status}" if kpi.status else '',
            'Comments': kpi.comments[:50] + '...' if kpi.comments and len(kpi.comments) > 50 else kpi.comments or ''
        })

    import pandas as pd
    recent_df = pd.DataFrame(recent_data)

    st.dataframe(
        recent_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No manual entries yet for this period. Enter your first KPI above!")

st.markdown("---")

# Tips
with st.expander("💡 Tips for Manual Entry"):
    st.markdown("""
    **Value Formatting:**
    - Currency: Use `$` symbol (e.g., `$50,000` or `50000`)
    - Percentages: Use `%` symbol (e.g., `15%` or `0.15`)
    - Numbers: Enter as-is (e.g., `125`)

    **Frequency:**
    - **Quarterly KPIs**: Enter once per quarter (Employee NPS, Cash EBITDA)
    - **Monthly KPIs**: Enter at end of each month
    - **Weekly KPIs**: Enter weekly for tracking trends

    **Comments:**
    - Add context for unusual values
    - Link to source documents (e.g., "See Google Doc for detail")
    - Note any data quality issues

    **Best Practices:**
    - Enter data on the same day each period for consistency
    - Double-check values before saving
    - Use comments to explain significant changes
    """)
