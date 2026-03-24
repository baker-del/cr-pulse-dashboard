"""
Plotly Chart Generation Utilities

Creates interactive charts for KPI trends and visualizations
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional
from utils.colors import (
    CHART_TARGET, CHART_ACTUAL, CHART_GRID,
    PRIMARY_TEAL, LIGHT_GREY, DARK_GREY
)


def create_trend_chart(
    df: pd.DataFrame,
    kpi_name: str,
    target_col: str = 'target_value',
    actual_col: str = 'actual_value',
    date_col: str = 'date',
    height: int = 400
) -> go.Figure:
    """
    Create a trend line chart showing target vs actual over time

    Args:
        df: DataFrame with KPI trend data
        kpi_name: Name of the KPI for the title
        target_col: Column name for target values
        actual_col: Column name for actual values
        date_col: Column name for dates
        height: Chart height in pixels

    Returns:
        Plotly Figure object
    """
    # Convert string values to numeric if needed
    df = df.copy()

    def parse_value(val):
        if pd.isna(val) or val == '':
            return None
        val_str = str(val).replace('$', '').replace(',', '').replace('%', '')
        try:
            return float(val_str)
        except:
            return None

    df[actual_col] = df[actual_col].apply(parse_value)
    df[target_col] = df[target_col].apply(parse_value)

    # Sort by date
    df = df.sort_values(date_col)

    # Create figure
    fig = go.Figure()

    # Add target line
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df[target_col],
        mode='lines',
        name='Target',
        line=dict(color=CHART_TARGET, width=2, dash='dash'),
        hovertemplate='<b>Target</b><br>Date: %{x}<br>Value: %{y:,.2f}<extra></extra>'
    ))

    # Add actual line
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df[actual_col],
        mode='lines+markers',
        name='Actual',
        line=dict(color=CHART_ACTUAL, width=3),
        marker=dict(size=6),
        hovertemplate='<b>Actual</b><br>Date: %{x}<br>Value: %{y:,.2f}<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        title=dict(
            text=f"{kpi_name} - Trend",
            font=dict(size=18, color=DARK_GREY, family="Arial"),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor=CHART_GRID,
            zeroline=False
        ),
        yaxis=dict(
            title="Value",
            showgrid=True,
            gridcolor=CHART_GRID,
            zeroline=False
        ),
        plot_bgcolor=LIGHT_GREY,
        paper_bgcolor='white',
        hovermode='x unified',
        height=height,
        margin=dict(l=60, r=40, t=60, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


def create_variance_bar_chart(
    df: pd.DataFrame,
    kpi_col: str = 'kpi_name',
    variance_col: str = 'variance_pct',
    top_n: int = 10,
    height: int = 400
) -> go.Figure:
    """
    Create a horizontal bar chart showing variance from target

    Args:
        df: DataFrame with KPI data
        kpi_col: Column name for KPI names
        variance_col: Column name for variance percentages
        top_n: Number of top KPIs to show
        height: Chart height in pixels

    Returns:
        Plotly Figure object
    """
    # Sort by variance and take top N
    df = df.sort_values(variance_col, ascending=False).head(top_n)

    # Color bars based on variance
    colors = []
    for variance in df[variance_col]:
        if variance >= 90:
            colors.append(PRIMARY_TEAL)
        elif variance >= 70:
            colors.append('#FFC857')  # Yellow
        else:
            colors.append('#E75944')  # Red

    fig = go.Figure(data=[
        go.Bar(
            y=df[kpi_col],
            x=df[variance_col],
            orientation='h',
            marker=dict(color=colors),
            text=df[variance_col].apply(lambda x: f"{x:.1f}%"),
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Variance: %{x:.1f}%<extra></extra>'
        )
    ])

    fig.update_layout(
        title=dict(
            text="KPI Performance (% of Target)",
            font=dict(size=18, color=DARK_GREY),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="% of Target Achieved",
            showgrid=True,
            gridcolor=CHART_GRID,
            range=[0, max(df[variance_col].max(), 100) * 1.1]
        ),
        yaxis=dict(
            title="",
            showgrid=False
        ),
        plot_bgcolor=LIGHT_GREY,
        paper_bgcolor='white',
        height=height,
        margin=dict(l=200, r=60, t=60, b=60)
    )

    # Add reference line at 100%
    fig.add_vline(
        x=100,
        line=dict(color=CHART_TARGET, width=2, dash='dash'),
        annotation_text="Target",
        annotation_position="top"
    )

    return fig


def create_kpi_gauge(
    actual: float,
    target: float,
    kpi_name: str,
    unit: str = "",
    height: int = 300
) -> go.Figure:
    """
    Create a gauge chart for a single KPI

    Args:
        actual: Actual value
        target: Target value
        kpi_name: Name of the KPI
        unit: Unit for display (e.g., "$", "%")
        height: Chart height in pixels

    Returns:
        Plotly Figure object
    """
    variance_pct = (actual / target * 100) if target != 0 else 0

    # Determine color
    if variance_pct >= 90:
        color = PRIMARY_TEAL
    elif variance_pct >= 70:
        color = '#FFC857'
    else:
        color = '#E75944'

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=actual,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': kpi_name, 'font': {'size': 16}},
        delta={'reference': target, 'increasing': {'color': PRIMARY_TEAL}},
        number={'suffix': unit, 'font': {'size': 32}},
        gauge={
            'axis': {'range': [None, target * 1.5]},
            'bar': {'color': color},
            'bgcolor': LIGHT_GREY,
            'steps': [
                {'range': [0, target * 0.7], 'color': '#FEE2E2'},
                {'range': [target * 0.7, target * 0.9], 'color': '#FEF3C7'},
                {'range': [target * 0.9, target * 1.5], 'color': '#D1FAE5'}
            ],
            'threshold': {
                'line': {'color': DARK_GREY, 'width': 4},
                'thickness': 0.75,
                'value': target
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor='white',
        height=height,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig
