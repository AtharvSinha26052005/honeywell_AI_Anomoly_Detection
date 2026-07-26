"""
Analyst-Facing Dashboard
=========================
Premium dark-themed Plotly Dash dashboard for SOC analysts.
Features:
  - Real-time KPI overview
  - Ranked alert queue with filtering
  - Anomaly breakdown charts
  - Entity deep-dive with history
  - Geographic visualization
  - Explainability panel
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime

import dash
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_data():
    """Load scored access logs."""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "scored_access_logs.csv")
    if not os.path.exists(data_path):
        print("ERROR: scored_access_logs.csv not found. Run 'python train.py' first.")
        sys.exit(1)

    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["date"] = df["timestamp"].dt.date
    df["day_of_week"] = df["timestamp"].dt.day_name()

    # Parse geo coordinates
    def parse_lat_lon(geo_str):
        try:
            coords = str(geo_str).split("(")[1].rstrip(")")
            lat, lon = coords.split(",")
            return float(lat), float(lon)
        except:
            return 0.0, 0.0

    df[["lat", "lon"]] = df["geo_location"].apply(
        lambda x: pd.Series(parse_lat_lon(x))
    )
    df["city"] = df["geo_location"].apply(
        lambda x: str(x).split("(")[0] if "(" in str(x) else str(x)
    )

    return df


# ---------------------------------------------------------------------------
# Chart Theme
# ---------------------------------------------------------------------------

CHART_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, sans-serif", "color": "#94a3b8", "size": 12},
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
    "xaxis": {"gridcolor": "rgba(255,255,255,0.04)", "zerolinecolor": "rgba(255,255,255,0.04)"},
    "yaxis": {"gridcolor": "rgba(255,255,255,0.04)", "zerolinecolor": "rgba(255,255,255,0.04)"},
}

ANOMALY_COLORS = {
    "normal": "#4ade80",
    "brute_force": "#ef4444",
    "impossible_travel": "#f59e0b",
    "credential_stuffing": "#ec4899",
    "lateral_movement": "#8b5cf6",
    "device_spoofing": "#06b6d4",
    "low_and_slow": "#f97316",
    "insider_drift": "#64748b",
}


# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    assets_folder="assets",
    title="🛡️ AI Anomaly Detection | SOC Dashboard",
    update_title=None,
    suppress_callback_exceptions=True,
)

server = app.server

# Load data
df = load_data()

# Precompute stats
total_events = len(df)
anomaly_df = df[df["predicted_label"] != "normal"]
total_anomalies = len(anomaly_df)
high_risk_alerts = len(df[df["risk_score"] >= 70])
critical_alerts = len(df[df["risk_score"] >= 85])
unique_entities = df["entity_id"].nunique()
avg_risk = df[df["predicted_label"] != "normal"]["risk_score"].mean()


# ---------------------------------------------------------------------------
# Layout Helper Functions
# ---------------------------------------------------------------------------

def make_kpi_card(label, value, color, delta_text=""):
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(str(value), className=f"kpi-value {color}"),
        html.Div(delta_text, className="kpi-delta"),
    ], className=f"kpi-card {color}")


# ---------------------------------------------------------------------------
# App Layout
# ---------------------------------------------------------------------------

app.layout = html.Div([
    # --- Header ---
    html.Div([
        html.Div([
            html.Div("🛡️ AI Anomaly Detection", className="header-title"),
            html.Div("Behavioral Anomaly Detection for Cybersecurity | Honeywell Hackathon", className="header-subtitle"),
        ]),
        html.Div([
            html.Span(className="live-dot"),
            html.Span("LIVE MONITORING"),
        ], className="header-badge"),
    ], className="header-bar"),

    # --- Main Content ---
    html.Div([

        # --- KPI Row ---
        html.Div([
            make_kpi_card("Total Events", f"{total_events:,}", "blue", f"Synthetic dataset"),
            make_kpi_card("Anomalies Detected", f"{total_anomalies:,}", "red", f"{total_anomalies/total_events*100:.1f}% of total"),
            make_kpi_card("High Risk Alerts", f"{high_risk_alerts:,}", "amber", "Risk Score ≥ 70"),
            make_kpi_card("Critical Alerts", f"{critical_alerts:,}", "purple", "Risk Score ≥ 85"),
            make_kpi_card("Entities Monitored", f"{unique_entities}", "cyan", f"Users + Devices + Services"),
            make_kpi_card("Avg Risk Score", f"{avg_risk:.0f}", "green", "Anomalies only"),
        ], className="kpi-row"),

        # --- Charts Row 1 ---
        html.Div("📊 Anomaly Analytics", className="section-title"),
        html.Div([
            # Anomaly Type Distribution
            html.Div([
                html.Div([
                    html.Span("🎯", className="chart-title-icon"),
                    "Anomaly Type Distribution"
                ], className="chart-title"),
                dcc.Graph(id="anomaly-pie", config={"displayModeBar": False}),
            ], className="chart-card"),

            # Timeline
            html.Div([
                html.Div([
                    html.Span("📈", className="chart-title-icon"),
                    "Anomaly Timeline (Daily)"
                ], className="chart-title"),
                dcc.Graph(id="timeline-chart", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], className="chart-grid"),

        # --- Charts Row 2 ---
        html.Div([
            # Risk Score Distribution
            html.Div([
                html.Div([
                    html.Span("⚡", className="chart-title-icon"),
                    "Risk Score Distribution"
                ], className="chart-title"),
                dcc.Graph(id="risk-histogram", config={"displayModeBar": False}),
            ], className="chart-card"),

            # Hourly Heatmap
            html.Div([
                html.Div([
                    html.Span("🕐", className="chart-title-icon"),
                    "Anomaly Heatmap (Hour × Day)"
                ], className="chart-title"),
                dcc.Graph(id="heatmap-chart", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], className="chart-grid"),

        # --- Geographic Map ---
        html.Div("🌍 Geographic Analysis", className="section-title"),
        html.Div([
            html.Div([
                html.Div([
                    html.Span("📍", className="chart-title-icon"),
                    "Global Access Map — Anomaly Hotspots"
                ], className="chart-title"),
                dcc.Graph(id="geo-map", config={"displayModeBar": False}),
            ], className="chart-card full-width"),
        ], className="chart-grid"),

        # --- Alert Queue ---
        html.Div("🚨 Alert Queue — Ranked by Risk Score", className="section-title"),

        # Filters
        html.Div([
            dcc.Dropdown(
                id="filter-anomaly-type",
                options=[{"label": t.replace("_", " ").title(), "value": t} for t in ANOMALY_COLORS.keys() if t != "normal"],
                placeholder="Filter by Anomaly Type",
                multi=True,
                style={"width": "300px", "background": "rgba(15,23,42,0.8)", "color": "#e2e8f0"},
            ),
            dcc.Dropdown(
                id="filter-entity-type",
                options=[
                    {"label": "User", "value": "user"},
                    {"label": "Service Account", "value": "service_account"},
                    {"label": "Edge Device", "value": "edge_device"},
                ],
                placeholder="Filter by Entity Type",
                multi=True,
                style={"width": "250px", "background": "rgba(15,23,42,0.8)", "color": "#e2e8f0"},
            ),
            dcc.Dropdown(
                id="filter-risk-level",
                options=[
                    {"label": "🔴 Critical (≥85)", "value": "critical"},
                    {"label": "🟠 High (70-84)", "value": "high"},
                    {"label": "🟡 Medium (40-69)", "value": "medium"},
                    {"label": "🟢 Low (<40)", "value": "low"},
                ],
                placeholder="Filter by Risk Level",
                multi=True,
                style={"width": "250px", "background": "rgba(15,23,42,0.8)", "color": "#e2e8f0"},
            ),
        ], className="filter-bar"),

        # Alert Table
        html.Div([
            dash_table.DataTable(
                id="alert-table",
                columns=[
                    {"name": "Risk", "id": "risk_score", "type": "numeric"},
                    {"name": "Entity ID", "id": "entity_id"},
                    {"name": "Type", "id": "entity_type"},
                    {"name": "Anomaly", "id": "predicted_label"},
                    {"name": "Confidence", "id": "confidence", "type": "numeric",
                     "format": dash_table.FormatTemplate.percentage(1)},
                    {"name": "Resource", "id": "resource_accessed"},
                    {"name": "Source IP", "id": "source_ip"},
                    {"name": "Location", "id": "city"},
                    {"name": "Time", "id": "timestamp"},
                ],
                data=[],
                page_size=15,
                sort_action="native",
                sort_by=[{"column_id": "risk_score", "direction": "desc"}],
                row_selectable="single",
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "rgba(30, 41, 59, 0.8)",
                    "color": "#94a3b8",
                    "fontWeight": "600",
                    "fontSize": "0.75rem",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.05em",
                    "border": "none",
                    "borderBottom": "1px solid rgba(255,255,255,0.08)",
                },
                style_cell={
                    "backgroundColor": "transparent",
                    "color": "#cbd5e1",
                    "fontSize": "0.82rem",
                    "border": "none",
                    "borderBottom": "1px solid rgba(255,255,255,0.04)",
                    "padding": "10px 14px",
                    "fontFamily": "Inter, sans-serif",
                    "textAlign": "left",
                    "maxWidth": "180px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_data_conditional=[
                    {"if": {"filter_query": "{risk_score} >= 85"},
                     "color": "#ef4444", "fontWeight": "600"},
                    {"if": {"filter_query": "{risk_score} >= 70 && {risk_score} < 85"},
                     "color": "#f59e0b"},
                    {"if": {"filter_query": "{risk_score} >= 40 && {risk_score} < 70"},
                     "color": "#3b82f6"},
                    {"if": {"filter_query": "{risk_score} < 40"},
                     "color": "#4ade80"},
                    {"if": {"state": "selected"},
                     "backgroundColor": "rgba(99, 102, 241, 0.15)",
                     "border": "1px solid rgba(99, 102, 241, 0.3)"},
                ],
                style_as_list_view=True,
            ),
        ], className="alert-table-container"),

        # --- Alert Detail Panel ---
        html.Div(id="alert-detail-panel"),

        # --- Entity Breakdown ---
        html.Div("👤 Entity Analysis", className="section-title"),
        html.Div([
            # Top risky entities
            html.Div([
                html.Div([
                    html.Span("🏆", className="chart-title-icon"),
                    "Top 15 Riskiest Entities"
                ], className="chart-title"),
                dcc.Graph(id="top-entities-chart", config={"displayModeBar": False}),
            ], className="chart-card"),

            # Attack type per entity type
            html.Div([
                html.Div([
                    html.Span("📊", className="chart-title-icon"),
                    "Attack Distribution by Entity Type"
                ], className="chart-title"),
                dcc.Graph(id="entity-attack-chart", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], className="chart-grid"),

    ], className="main-content"),

], id="app-container")


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("anomaly-pie", "figure"),
    Input("anomaly-pie", "id"),
)
def update_anomaly_pie(_):
    anomaly_counts = anomaly_df["predicted_label"].value_counts()
    fig = go.Figure(go.Pie(
        labels=[l.replace("_", " ").title() for l in anomaly_counts.index],
        values=anomaly_counts.values,
        hole=0.55,
        marker=dict(colors=[ANOMALY_COLORS.get(l, "#64748b") for l in anomaly_counts.index]),
        textinfo="percent+label",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        **CHART_THEME,
        showlegend=False,
        height=350,
        annotations=[dict(
            text=f"<b>{total_anomalies:,}</b><br><span style='font-size:11px;color:#94a3b8'>anomalies</span>",
            x=0.5, y=0.5, font_size=22, font_color="#e2e8f0",
            showarrow=False,
        )],
    )
    return fig


@app.callback(
    Output("timeline-chart", "figure"),
    Input("timeline-chart", "id"),
)
def update_timeline(_):
    daily = anomaly_df.groupby([anomaly_df["timestamp"].dt.date, "predicted_label"]).size().reset_index(name="count")
    daily.columns = ["date", "predicted_label", "count"]

    fig = go.Figure()
    for label in ANOMALY_COLORS:
        if label == "normal":
            continue
        subset = daily[daily["predicted_label"] == label]
        if len(subset) > 0:
            fig.add_trace(go.Scatter(
                x=subset["date"], y=subset["count"],
                mode="lines+markers",
                name=label.replace("_", " ").title(),
                line=dict(color=ANOMALY_COLORS[label], width=2),
                marker=dict(size=4),
                fill="tozeroy",
                fillcolor=ANOMALY_COLORS[label].replace(")", ",0.1)").replace("rgb", "rgba") if "rgb" in ANOMALY_COLORS[label] else None,
            ))

    fig.update_layout(
        **CHART_THEME,
        height=350,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10),
        ),
        hovermode="x unified",
    )
    return fig


@app.callback(
    Output("risk-histogram", "figure"),
    Input("risk-histogram", "id"),
)
def update_risk_histogram(_):
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=anomaly_df["risk_score"],
        nbinsx=30,
        marker=dict(
            color=anomaly_df["risk_score"],
            colorscale=[[0, "#22c55e"], [0.4, "#3b82f6"], [0.7, "#f59e0b"], [1, "#ef4444"]],
            line=dict(color="rgba(255,255,255,0.1)", width=1),
        ),
        hovertemplate="Risk: %{x}<br>Count: %{y}<extra></extra>",
    ))
    fig.update_layout(
        **CHART_THEME,
        height=350,
        xaxis_title="Risk Score",
        yaxis_title="Count",
        bargap=0.05,
    )
    return fig


@app.callback(
    Output("heatmap-chart", "figure"),
    Input("heatmap-chart", "id"),
)
def update_heatmap(_):
    heatmap_data = anomaly_df.groupby([
        anomaly_df["timestamp"].dt.day_name(),
        anomaly_df["timestamp"].dt.hour
    ]).size().reset_index(name="count")
    heatmap_data.columns = ["day", "hour", "count"]

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_pivot = heatmap_data.pivot_table(index="day", columns="hour", values="count", fill_value=0)
    heatmap_pivot = heatmap_pivot.reindex(day_order)

    fig = go.Figure(go.Heatmap(
        z=heatmap_pivot.values,
        x=[f"{h:02d}:00" for h in range(24)],
        y=day_order,
        colorscale=[[0, "#0f172a"], [0.3, "#312e81"], [0.6, "#7c3aed"], [0.8, "#ec4899"], [1, "#ef4444"]],
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>Anomalies: %{z}<extra></extra>",
    ))
    fig.update_layout(
        **CHART_THEME,
        height=350,
        xaxis=dict(
            **CHART_THEME["xaxis"],
            tickangle=-45,
            dtick=2,
        ),
    )
    return fig


@app.callback(
    Output("geo-map", "figure"),
    Input("geo-map", "id"),
)
def update_geo_map(_):
    geo_anomalies = anomaly_df.groupby(["city", "lat", "lon", "predicted_label"]).agg(
        count=("entity_id", "count"),
        avg_risk=("risk_score", "mean"),
    ).reset_index()

    fig = go.Figure()
    for label in ANOMALY_COLORS:
        if label == "normal":
            continue
        subset = geo_anomalies[geo_anomalies["predicted_label"] == label]
        if len(subset) > 0:
            fig.add_trace(go.Scattergeo(
                lat=subset["lat"],
                lon=subset["lon"],
                text=subset.apply(
                    lambda r: f"{r['city']}<br>{label.replace('_', ' ').title()}<br>"
                              f"Count: {r['count']}<br>Avg Risk: {r['avg_risk']:.0f}",
                    axis=1
                ),
                marker=dict(
                    size=np.clip(subset["count"] / 2, 6, 40),
                    color=ANOMALY_COLORS[label],
                    opacity=0.7,
                    line=dict(width=1, color="rgba(255,255,255,0.3)"),
                ),
                name=label.replace("_", " ").title(),
                hoverinfo="text",
            ))

    fig.update_layout(
        **CHART_THEME,
        height=450,
        geo=dict(
            bgcolor="rgba(0,0,0,0)",
            showland=True,
            landcolor="rgba(30, 41, 59, 0.6)",
            showocean=True,
            oceancolor="rgba(10, 14, 26, 0.8)",
            showcoastlines=True,
            coastlinecolor="rgba(99, 102, 241, 0.2)",
            showframe=False,
            showcountries=True,
            countrycolor="rgba(99, 102, 241, 0.15)",
            projection_type="natural earth",
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5,
            font=dict(size=10),
        ),
    )
    return fig


@app.callback(
    Output("alert-table", "data"),
    [
        Input("filter-anomaly-type", "value"),
        Input("filter-entity-type", "value"),
        Input("filter-risk-level", "value"),
    ],
)
def update_alert_table(anomaly_types, entity_types, risk_levels):
    filtered = anomaly_df.copy()

    if anomaly_types:
        filtered = filtered[filtered["predicted_label"].isin(anomaly_types)]

    if entity_types:
        filtered = filtered[filtered["entity_type"].isin(entity_types)]

    if risk_levels:
        conditions = []
        for level in risk_levels:
            if level == "critical":
                conditions.append(filtered["risk_score"] >= 85)
            elif level == "high":
                conditions.append((filtered["risk_score"] >= 70) & (filtered["risk_score"] < 85))
            elif level == "medium":
                conditions.append((filtered["risk_score"] >= 40) & (filtered["risk_score"] < 70))
            elif level == "low":
                conditions.append(filtered["risk_score"] < 40)
        if conditions:
            combined = conditions[0]
            for c in conditions[1:]:
                combined = combined | c
            filtered = filtered[combined]

    # Sort by risk score descending
    filtered = filtered.sort_values("risk_score", ascending=False).head(200)

    # Format for display
    display_df = filtered[["risk_score", "entity_id", "entity_type", "predicted_label",
                            "confidence", "resource_accessed", "source_ip", "city", "timestamp"]].copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    display_df["predicted_label"] = display_df["predicted_label"].str.replace("_", " ").str.title()

    return display_df.to_dict("records")


@app.callback(
    Output("alert-detail-panel", "children"),
    Input("alert-table", "selected_rows"),
    State("alert-table", "data"),
)
def update_detail_panel(selected_rows, table_data):
    if not selected_rows or not table_data:
        return html.Div()

    row = table_data[selected_rows[0]]
    entity_id = row["entity_id"]

    # Find full row in original df
    entity_events = anomaly_df[anomaly_df["entity_id"] == entity_id].sort_values("timestamp", ascending=False)

    # Parse contributing factors
    try:
        first_event = entity_events.iloc[0]
        factors = json.loads(first_event["contributing_factors"])
    except:
        factors = ["No detailed factors available"]

    return html.Div([
        html.Div([
            html.Span("🔍", className="chart-title-icon"),
            f"Alert Detail — {entity_id}"
        ], className="chart-title"),

        html.Div([
            # Left: Details
            html.Div([
                html.H4(f"Entity: {entity_id}", style={"color": "#818cf8", "marginBottom": "12px"}),
                html.P(f"Type: {row['entity_type']}", style={"color": "#94a3b8", "fontSize": "0.9rem"}),
                html.P(f"Anomaly: {row['predicted_label']}", style={"color": "#f87171", "fontSize": "0.9rem", "fontWeight": "600"}),
                html.P(f"Risk Score: {row['risk_score']}/100", style={"color": "#fbbf24", "fontSize": "0.9rem"}),
                html.P(f"Confidence: {float(row['confidence']):.1%}", style={"color": "#94a3b8", "fontSize": "0.9rem"}),
                html.P(f"Location: {row['city']}", style={"color": "#94a3b8", "fontSize": "0.9rem"}),
                html.P(f"Resource: {row['resource_accessed']}", style={"color": "#94a3b8", "fontSize": "0.9rem"}),
                html.P(f"Source IP: {row['source_ip']}", style={"color": "#94a3b8", "fontSize": "0.9rem"}),

                html.Hr(style={"borderColor": "rgba(255,255,255,0.08)", "margin": "16px 0"}),

                html.H5("Contributing Factors:", style={"color": "#e2e8f0", "marginBottom": "10px"}),
                html.Div([
                    html.Div(factor, className="factor-item") for factor in factors
                ]),
            ], style={"flex": "1"}),

            # Right: Entity history chart
            html.Div([
                html.H5("Entity Access History", style={"color": "#e2e8f0", "marginBottom": "10px"}),
                dcc.Graph(
                    figure=_make_entity_history_chart(entity_id),
                    config={"displayModeBar": False},
                    style={"height": "250px"},
                ),
                html.P(f"Total events by this entity: {len(df[df['entity_id'] == entity_id])}",
                       style={"color": "#64748b", "fontSize": "0.8rem", "marginTop": "8px"}),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "24px", "flexWrap": "wrap"}),
    ], className="detail-panel")


def _make_entity_history_chart(entity_id):
    """Create a mini timeline chart for a specific entity."""
    entity_data = df[df["entity_id"] == entity_id].copy()
    entity_data = entity_data.sort_values("timestamp")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=entity_data["timestamp"],
        y=entity_data["risk_score"],
        mode="lines+markers",
        marker=dict(
            size=6,
            color=entity_data["risk_score"],
            colorscale=[[0, "#22c55e"], [0.5, "#f59e0b"], [1, "#ef4444"]],
        ),
        line=dict(color="rgba(99,102,241,0.5)", width=1),
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.05)",
        hovertemplate="Time: %{x}<br>Risk: %{y}<br>Label: %{text}<extra></extra>",
        text=entity_data["predicted_label"],
    ))
    fig.update_layout(
        **CHART_THEME,
        height=250,
        xaxis_title="",
        yaxis_title="Risk Score",
        showlegend=False,
    )
    return fig


@app.callback(
    Output("top-entities-chart", "figure"),
    Input("top-entities-chart", "id"),
)
def update_top_entities(_):
    top = anomaly_df.groupby("entity_id").agg(
        total_anomalies=("entity_id", "count"),
        avg_risk=("risk_score", "mean"),
        max_risk=("risk_score", "max"),
    ).sort_values("avg_risk", ascending=True).tail(15)

    fig = go.Figure(go.Bar(
        y=top.index,
        x=top["avg_risk"],
        orientation="h",
        marker=dict(
            color=top["avg_risk"],
            colorscale=[[0, "#3b82f6"], [0.5, "#f59e0b"], [1, "#ef4444"]],
            line=dict(width=0),
        ),
        text=top["avg_risk"].round(0).astype(int),
        textposition="outside",
        textfont=dict(size=10, color="#94a3b8"),
        hovertemplate="<b>%{y}</b><br>Avg Risk: %{x:.0f}<br>Anomalies: %{customdata[0]}<extra></extra>",
        customdata=top[["total_anomalies"]].values,
    ))
    fig.update_layout(
        **CHART_THEME,
        height=400,
        xaxis_title="Average Risk Score",
        yaxis=dict(**CHART_THEME["yaxis"], tickfont=dict(size=10)),
    )
    return fig


@app.callback(
    Output("entity-attack-chart", "figure"),
    Input("entity-attack-chart", "id"),
)
def update_entity_attack(_):
    cross = anomaly_df.groupby(["entity_type", "predicted_label"]).size().reset_index(name="count")

    fig = go.Figure()
    for label in ANOMALY_COLORS:
        if label == "normal":
            continue
        subset = cross[cross["predicted_label"] == label]
        if len(subset) > 0:
            fig.add_trace(go.Bar(
                x=subset["entity_type"].str.replace("_", " ").str.title(),
                y=subset["count"],
                name=label.replace("_", " ").title(),
                marker=dict(color=ANOMALY_COLORS[label]),
            ))

    fig.update_layout(
        **CHART_THEME,
        height=400,
        barmode="group",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10),
        ),
        xaxis_title="Entity Type",
        yaxis_title="Count",
    )
    return fig


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🛡️  AI Anomaly Detection Dashboard")
    print("  Open in browser: http://127.0.0.1:8050")
    print("=" * 60 + "\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
