"""
Analyst-Facing Dashboard — LIVE Real-Time Edition
===================================================
Premium dark-themed Plotly Dash dashboard with real-time anomaly simulation.
Features:
  - Live event stream with auto-refresh (2s interval)
  - Real-time KPI counters that update
  - Ranked alert queue with filtering
  - Anomaly breakdown charts (all working)
  - Geographic visualization
  - Entity deep-dive with history
  - Explainability panel
"""

import os
import sys
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import dash
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go


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

    def parse_lat_lon(geo_str):
        try:
            coords = str(geo_str).split("(")[1].rstrip(")")
            lat, lon = coords.split(",")
            return float(lat), float(lon)
        except Exception:
            return 0.0, 0.0

    coords = df["geo_location"].apply(lambda x: pd.Series(parse_lat_lon(x)))
    df["lat"] = coords[0]
    df["lon"] = coords[1]
    df["city"] = df["geo_location"].apply(
        lambda x: str(x).split("(")[0] if "(" in str(x) else str(x)
    )
    return df


# ---------------------------------------------------------------------------
# Chart Theme
# ---------------------------------------------------------------------------

CHART_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(255,255,255,0.04)"
FONT_COLOR = "#94a3b8"

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

ANOMALY_LABELS = {k: k.replace("_", " ").title() for k in ANOMALY_COLORS}


def base_layout(height=350):
    return dict(
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(family="Inter, sans-serif", color=FONT_COLOR, size=12),
        margin=dict(l=50, r=20, t=40, b=50),
        height=height,
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    )


# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    assets_folder="assets",
    title="AI Anomaly Detection | SOC Dashboard",
    update_title=None,
    suppress_callback_exceptions=True,
)
server = app.server

# Load data
df = load_data()
anomaly_df = df[df["predicted_label"] != "normal"].copy()

# Stats
total_events = len(df)
total_anomalies = len(anomaly_df)
high_risk_alerts = len(df[df["risk_score"] >= 70])
critical_alerts = len(df[df["risk_score"] >= 85])
unique_entities = df["entity_id"].nunique()
avg_risk = anomaly_df["risk_score"].mean() if len(anomaly_df) > 0 else 0

# Pre-build live event pool (anomalies only for the ticker)
live_event_pool = anomaly_df.to_dict("records")

# Pre-compute heatmap data (vectorized, fast)
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_day_map = {d: i for i, d in enumerate(DAY_ORDER)}
_hm_days = anomaly_df["timestamp"].dt.day_name().map(_day_map).values
_hm_hours = anomaly_df["timestamp"].dt.hour.values
PRECOMPUTED_HEATMAP = np.zeros((7, 24))
for _d, _h in zip(_hm_days, _hm_hours):
    if 0 <= _d < 7 and 0 <= _h < 24:
        PRECOMPUTED_HEATMAP[int(_d)][int(_h)] += 1
print(f"  Heatmap precomputed: max={PRECOMPUTED_HEATMAP.max()}, total={PRECOMPUTED_HEATMAP.sum()}")

# Pre-build the ENTIRE heatmap figure at load time
HEATMAP_FIG = go.Figure(go.Heatmap(
    z=PRECOMPUTED_HEATMAP.tolist(),
    x=[f"{h:02d}:00" for h in range(24)],
    y=DAY_ORDER,
    colorscale=[[0, "#0f172a"], [0.2, "#1e1b4b"], [0.4, "#4c1d95"], [0.6, "#7c3aed"], [0.8, "#c026d3"], [1, "#ef4444"]],
    hovertemplate="Day: %{y}<br>Hour: %{x}<br>Anomalies: %{z}<extra></extra>",
    showscale=True,
    colorbar=dict(title="Count", title_font=dict(color="#94a3b8"), tickfont=dict(color="#94a3b8")),
))
HEATMAP_FIG.update_layout(
    paper_bgcolor=CHART_BG,
    plot_bgcolor=CHART_BG,
    font=dict(family="Inter, sans-serif", color=FONT_COLOR, size=12),
    margin=dict(l=90, r=20, t=20, b=60),
    height=350,
    xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, tickangle=-45, dtick=3),
    yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, autorange="reversed"),
)
print(f"  Heatmap figure built: {len(HEATMAP_FIG.data)} traces")

# Pre-compute top entities
PRECOMPUTED_TOP_ENTITIES = anomaly_df.groupby("entity_id").agg(
    total_anomalies=("entity_id", "count"),
    avg_risk=("risk_score", "mean"),
).sort_values("avg_risk", ascending=True).tail(15)


# ---------------------------------------------------------------------------
# Layout Helpers
# ---------------------------------------------------------------------------

def kpi_card(label, value, color, delta=""):
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(str(value), className=f"kpi-value {color}"),
        html.Div(delta, className="kpi-delta"),
    ], className=f"kpi-card {color}")


# ---------------------------------------------------------------------------
# App Layout
# ---------------------------------------------------------------------------

app.layout = html.Div([
    # Auto-refresh interval for live simulation
    dcc.Interval(id="live-interval", interval=2500, n_intervals=0),
    dcc.Store(id="live-events-store", data=[]),

    # --- Header ---
    html.Div([
        html.Div([
            html.Div("AI Anomaly Detection", className="header-title"),
            html.Div("Behavioral Anomaly Detection for Cybersecurity | Honeywell Hackathon", className="header-subtitle"),
        ]),
        html.Div([
            html.Span(className="live-dot"),
            html.Span("LIVE MONITORING"),
        ], className="header-badge"),
    ], className="header-bar"),

    # --- Main Content ---
    html.Div([

        # ============ LIVE EVENT STREAM ============
        html.Div("REAL-TIME THREAT FEED", className="section-title"),
        html.Div([
            html.Div(id="live-feed-container", className="live-feed"),
        ], className="chart-card", style={"marginBottom": "24px"}),

        # ============ KPI ROW ============
        html.Div(id="kpi-row", className="kpi-row"),

        # ============ ANOMALY ANALYTICS ============
        html.Div("ANOMALY ANALYTICS", className="section-title"),
        html.Div([
            html.Div([
                html.Div("Anomaly Type Distribution", className="chart-title"),
                dcc.Graph(id="anomaly-pie", config={"displayModeBar": False}),
            ], className="chart-card"),
            html.Div([
                html.Div("Anomaly Timeline (Daily)", className="chart-title"),
                dcc.Graph(id="timeline-chart", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], className="chart-grid"),

        html.Div([
            html.Div([
                html.Div("Risk Score Distribution", className="chart-title"),
                dcc.Graph(id="risk-histogram", config={"displayModeBar": False}),
            ], className="chart-card"),
            html.Div([
                html.Div("Anomaly Heatmap (Hour x Day)", className="chart-title"),
                dcc.Graph(id="heatmap-chart", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], className="chart-grid"),

        # ============ GEO MAP ============
        html.Div("GEOGRAPHIC ANALYSIS", className="section-title"),
        html.Div([
            html.Div([
                html.Div("Global Access Map - Anomaly Hotspots", className="chart-title"),
                dcc.Graph(id="geo-map", config={"displayModeBar": False}),
            ], className="chart-card full-width"),
        ], className="chart-grid"),

        # ============ ALERT QUEUE ============
        html.Div("ALERT QUEUE - Ranked by Risk Score", className="section-title"),
        html.Div([
            dcc.Dropdown(
                id="filter-anomaly-type",
                options=[{"label": ANOMALY_LABELS[t], "value": t} for t in ANOMALY_COLORS if t != "normal"],
                placeholder="Filter by Anomaly Type",
                multi=True,
                style={"width": "300px", "background": "#0f172a", "color": "#e2e8f0"},
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
                style={"width": "250px", "background": "#0f172a", "color": "#e2e8f0"},
            ),
            dcc.Dropdown(
                id="filter-risk-level",
                options=[
                    {"label": "CRITICAL (>=85)", "value": "critical"},
                    {"label": "HIGH (70-84)", "value": "high"},
                    {"label": "MEDIUM (40-69)", "value": "medium"},
                    {"label": "LOW (<40)", "value": "low"},
                ],
                placeholder="Filter by Risk Level",
                multi=True,
                style={"width": "250px", "background": "#0f172a", "color": "#e2e8f0"},
            ),
        ], className="filter-bar"),

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

        # Alert detail panel
        html.Div(id="alert-detail-panel"),

        # ============ ENTITY ANALYSIS ============
        html.Div("ENTITY ANALYSIS", className="section-title"),
        html.Div([
            html.Div([
                html.Div("Top 15 Riskiest Entities", className="chart-title"),
                dcc.Graph(id="top-entities-chart", config={"displayModeBar": False}),
            ], className="chart-card"),
            html.Div([
                html.Div("Attack Distribution by Entity Type", className="chart-title"),
                dcc.Graph(id="entity-attack-chart", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], className="chart-grid"),

    ], className="main-content"),
], id="app-container")


# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------

# ===== LIVE EVENT STREAM =====
@app.callback(
    [Output("live-feed-container", "children"),
     Output("live-events-store", "data"),
     Output("kpi-row", "children")],
    Input("live-interval", "n_intervals"),
    State("live-events-store", "data"),
)
def update_live_feed(n, stored_events):
    # Simulate 1-3 new events per tick
    new_count = random.randint(1, 3)
    new_events = random.sample(live_event_pool, min(new_count, len(live_event_pool)))

    formatted_events = []
    for evt in new_events:
        now = datetime.now()
        formatted_events.append({
            "time": now.strftime("%H:%M:%S"),
            "entity": evt.get("entity_id", "unknown"),
            "type": str(evt.get("predicted_label", "unknown")).replace("_", " ").title(),
            "risk": evt.get("risk_score", 0),
            "resource": evt.get("resource_accessed", ""),
            "city": str(evt.get("geo_location", "")).split("(")[0],
            "ip": evt.get("source_ip", ""),
        })

    # Prepend new events, keep last 20
    all_events = formatted_events + (stored_events or [])
    all_events = all_events[:20]

    # Build live feed cards
    feed_items = []
    for i, evt in enumerate(all_events):
        risk = evt.get("risk", 0)
        if risk >= 85:
            risk_class = "risk-critical"
            risk_icon = "!!"
        elif risk >= 70:
            risk_class = "risk-high"
            risk_icon = "!"
        elif risk >= 40:
            risk_class = "risk-medium"
            risk_icon = "~"
        else:
            risk_class = "risk-low"
            risk_icon = "-"

        opacity = max(0.3, 1.0 - i * 0.04)

        feed_items.append(
            html.Div([
                html.Span(evt["time"], className="feed-time"),
                html.Span(f"[{risk_icon} {risk}]", className=f"feed-risk {risk_class}"),
                html.Span(evt["entity"], className="feed-entity"),
                html.Span(evt["type"], className="feed-type"),
                html.Span(evt.get("resource", ""), className="feed-resource"),
                html.Span(evt.get("city", ""), className="feed-city"),
            ], className="feed-row", style={"opacity": opacity})
        )

    # Update KPI with simulated live counter
    detected_live = total_anomalies + n * random.randint(1, 3)
    events_live = total_events + n * random.randint(5, 15)

    kpis = [
        kpi_card("TOTAL EVENTS PROCESSED", f"{events_live:,}", "blue", "Streaming"),
        kpi_card("ANOMALIES DETECTED", f"{detected_live:,}", "red", f"{detected_live/max(events_live,1)*100:.1f}% of total"),
        kpi_card("HIGH RISK ALERTS", f"{high_risk_alerts + n:,}", "amber", "Risk Score >= 70"),
        kpi_card("CRITICAL ALERTS", f"{critical_alerts + (n // 2):,}", "purple", "Risk Score >= 85"),
        kpi_card("ENTITIES MONITORED", f"{unique_entities}", "cyan", "Users + Devices + Services"),
        kpi_card("AVG RISK SCORE", f"{avg_risk:.0f}", "green", "Anomalies only"),
    ]

    return feed_items, all_events, kpis


# ===== ANOMALY PIE =====
@app.callback(Output("anomaly-pie", "figure"), Input("live-interval", "n_intervals"))
def update_anomaly_pie(_):
    counts = anomaly_df["predicted_label"].value_counts()
    fig = go.Figure(go.Pie(
        labels=[ANOMALY_LABELS.get(l, l) for l in counts.index],
        values=counts.values,
        hole=0.55,
        marker=dict(colors=[ANOMALY_COLORS.get(l, "#64748b") for l in counts.index]),
        textinfo="percent+label",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        **base_layout(350),
        showlegend=False,
        annotations=[dict(
            text=f"<b>{total_anomalies:,}</b><br><span style='font-size:11px;color:#94a3b8'>anomalies</span>",
            x=0.5, y=0.5, font_size=22, font_color="#e2e8f0", showarrow=False,
        )],
    )
    return fig


# ===== TIMELINE =====
@app.callback(Output("timeline-chart", "figure"), Input("timeline-chart", "id"))
def update_timeline(_):
    adf = anomaly_df.copy()
    adf["date_str"] = adf["timestamp"].dt.strftime("%Y-%m-%d")
    daily = adf.groupby(["date_str", "predicted_label"]).size().reset_index(name="count")

    fig = go.Figure()
    for label in ANOMALY_COLORS:
        if label == "normal":
            continue
        subset = daily[daily["predicted_label"] == label]
        if len(subset) > 0:
            fig.add_trace(go.Scatter(
                x=subset["date_str"], y=subset["count"],
                mode="lines+markers",
                name=ANOMALY_LABELS[label],
                line=dict(color=ANOMALY_COLORS[label], width=2),
                marker=dict(size=5),
            ))
    fig.update_layout(
        **base_layout(350),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        hovermode="x unified",
    )
    return fig


# ===== RISK HISTOGRAM =====
@app.callback(Output("risk-histogram", "figure"), Input("risk-histogram", "id"))
def update_risk_histogram(_):
    fig = go.Figure(go.Histogram(
        x=anomaly_df["risk_score"],
        nbinsx=30,
        marker=dict(
            color=["#22c55e" if v < 40 else "#3b82f6" if v < 70 else "#f59e0b" if v < 85 else "#ef4444"
                   for v in sorted(anomaly_df["risk_score"].values)],
        ),
        hovertemplate="Risk: %{x}<br>Count: %{y}<extra></extra>",
    ))
    # Use a simpler color approach
    fig.update_traces(marker_color="#818cf8")
    bins = [0, 40, 70, 85, 101]
    colors_map = ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444"]
    fig2 = go.Figure()
    for i in range(len(bins) - 1):
        subset = anomaly_df[(anomaly_df["risk_score"] >= bins[i]) & (anomaly_df["risk_score"] < bins[i+1])]
        if len(subset) > 0:
            fig2.add_trace(go.Histogram(
                x=subset["risk_score"],
                nbinsx=8,
                marker=dict(color=colors_map[i], line=dict(color="rgba(255,255,255,0.1)", width=1)),
                name=["Low", "Medium", "High", "Critical"][i],
                hovertemplate="Risk: %{x}<br>Count: %{y}<extra></extra>",
            ))
    fig2.update_layout(
        **base_layout(350),
        barmode="stack",
        xaxis_title="Risk Score",
        yaxis_title="Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        bargap=0.05,
    )
    return fig2


# ===== HEATMAP (returns pre-built figure) =====
@app.callback(Output("heatmap-chart", "figure"), Input("heatmap-chart", "id"))
def update_heatmap(_):
    return HEATMAP_FIG


# ===== GEO MAP =====
@app.callback(Output("geo-map", "figure"), Input("geo-map", "id"))
def update_geo_map(_):
    geo_agg = anomaly_df.groupby(["city", "lat", "lon", "predicted_label"]).agg(
        count=("entity_id", "count"),
        avg_risk=("risk_score", "mean"),
    ).reset_index()

    fig = go.Figure()
    for label in ANOMALY_COLORS:
        if label == "normal":
            continue
        subset = geo_agg[geo_agg["predicted_label"] == label]
        if len(subset) > 0:
            fig.add_trace(go.Scattergeo(
                lat=subset["lat"],
                lon=subset["lon"],
                text=subset.apply(
                    lambda r: f"{r['city']}<br>{ANOMALY_LABELS.get(label, label)}<br>"
                              f"Count: {r['count']}<br>Avg Risk: {r['avg_risk']:.0f}",
                    axis=1
                ),
                marker=dict(
                    size=np.clip(subset["count"].values / 2, 6, 40),
                    color=ANOMALY_COLORS[label],
                    opacity=0.7,
                    line=dict(width=1, color="rgba(255,255,255,0.3)"),
                ),
                name=ANOMALY_LABELS[label],
                hoverinfo="text",
            ))

    fig.update_layout(
        **base_layout(450),
        geo=dict(
            bgcolor="rgba(0,0,0,0)",
            showland=True, landcolor="rgba(30, 41, 59, 0.6)",
            showocean=True, oceancolor="rgba(10, 14, 26, 0.8)",
            showcoastlines=True, coastlinecolor="rgba(99, 102, 241, 0.2)",
            showframe=False,
            showcountries=True, countrycolor="rgba(99, 102, 241, 0.15)",
            projection_type="natural earth",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
    )
    return fig


# ===== ALERT TABLE =====
@app.callback(
    Output("alert-table", "data"),
    [Input("filter-anomaly-type", "value"),
     Input("filter-entity-type", "value"),
     Input("filter-risk-level", "value")],
)
def update_alert_table(anomaly_types, entity_types, risk_levels):
    filtered = anomaly_df.copy()

    if anomaly_types:
        filtered = filtered[filtered["predicted_label"].isin(anomaly_types)]
    if entity_types:
        filtered = filtered[filtered["entity_type"].isin(entity_types)]
    if risk_levels:
        conds = []
        for lv in risk_levels:
            if lv == "critical":
                conds.append(filtered["risk_score"] >= 85)
            elif lv == "high":
                conds.append((filtered["risk_score"] >= 70) & (filtered["risk_score"] < 85))
            elif lv == "medium":
                conds.append((filtered["risk_score"] >= 40) & (filtered["risk_score"] < 70))
            elif lv == "low":
                conds.append(filtered["risk_score"] < 40)
        if conds:
            combined = conds[0]
            for c in conds[1:]:
                combined = combined | c
            filtered = filtered[combined]

    filtered = filtered.sort_values("risk_score", ascending=False).head(200)
    display = filtered[["risk_score", "entity_id", "entity_type", "predicted_label",
                         "confidence", "resource_accessed", "source_ip", "city", "timestamp"]].copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    display["predicted_label"] = display["predicted_label"].str.replace("_", " ").str.title()
    return display.to_dict("records")


# ===== ALERT DETAIL =====
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
    entity_events = df[df["entity_id"] == entity_id].sort_values("timestamp", ascending=False)

    # Parse contributing factors
    try:
        first_event = entity_events.iloc[0]
        factors = json.loads(first_event["contributing_factors"])
    except Exception:
        factors = ["No detailed factors available"]

    # Build entity history mini chart
    entity_data = df[df["entity_id"] == entity_id].sort_values("timestamp")
    history_fig = go.Figure()
    history_fig.add_trace(go.Scatter(
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
        hovertemplate="Time: %{x}<br>Risk: %{y}<extra></extra>",
    ))
    history_fig.update_layout(**base_layout(220), showlegend=False, yaxis_title="Risk Score")

    return html.Div([
        html.Div("ALERT DETAIL - " + entity_id, className="chart-title"),
        html.Div([
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
                html.Div([html.Div(f, className="factor-item") for f in factors]),
            ], style={"flex": "1"}),
            html.Div([
                html.H5("Entity Access History", style={"color": "#e2e8f0", "marginBottom": "10px"}),
                dcc.Graph(figure=history_fig, config={"displayModeBar": False}, style={"height": "220px"}),
                html.P(f"Total events: {len(entity_data)}", style={"color": "#64748b", "fontSize": "0.8rem", "marginTop": "8px"}),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "24px", "flexWrap": "wrap"}),
    ], className="detail-panel")


# ===== TOP ENTITIES =====
@app.callback(Output("top-entities-chart", "figure"), Input("top-entities-chart", "id"))
def update_top_entities(_):
    top = PRECOMPUTED_TOP_ENTITIES

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
        hovertemplate="<b>%{y}</b><br>Avg Risk: %{x:.0f}<extra></extra>",
    ))
    layout = base_layout(400)
    layout["xaxis"] = dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title="Average Risk Score")
    layout["yaxis"] = dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, tickfont=dict(size=10))
    fig.update_layout(**layout)
    return fig


# ===== ENTITY ATTACK DISTRIBUTION =====
@app.callback(Output("entity-attack-chart", "figure"), Input("entity-attack-chart", "id"))
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
                name=ANOMALY_LABELS[label],
                marker=dict(color=ANOMALY_COLORS[label]),
            ))
    fig.update_layout(
        **base_layout(400),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        xaxis_title="Entity Type",
        yaxis_title="Count",
    )
    return fig


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AI Anomaly Detection Dashboard - LIVE")
    print("  Open in browser: http://127.0.0.1:8050")
    print("=" * 60 + "\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
