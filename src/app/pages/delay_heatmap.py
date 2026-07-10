import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from src.app.db import (
    get_airlines, 
    get_airport_delay_summary, 
    get_temporal_delay_data, 
    get_overall_kpis,
    get_airline_volume_delay_scatter
)

# Register page if using multi-page Dash (Dash 2.0+)
try:
    dash.register_page(__name__, path="/delay-heatmap", name="Airport Delay Heatmap")
except Exception:
    pass

# Helper lists
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# Explicit Premium Stylesheet Override Dictionary
STYLES = {
    "page_container": {
        "backgroundColor": "#0c0d12",
        "color": "#cbd5e1",
        "padding": "20px 10px",
        "minHeight": "100vh"
    },
    "main_title": {
        "color": "#ffffff",
        "fontWeight": "700",
        "fontSize": "2.2rem",
        "letterSpacing": "-0.025em"
    },
    "subtitle": {
        "color": "#64748b",
        "fontSize": "1rem"
    },
    "card": {
        "backgroundColor": "#151722",
        "border": "1px solid #242938",
        "borderRadius": "12px",
        "boxShadow": "0 4px 6px -1px rgba(0,0,0,0.2)",
        "overflow": "hidden"
    },
    "card_header": {
        "backgroundColor": "#1a1d2b",
        "borderBottom": "1px solid #242938",
        "padding": "12px 20px"
    },
    "card_header_text": {
        "color": "#ffffff",
        "fontWeight": "600",
        "fontSize": "1.1rem",
        "margin": "0"
    },
    "card_body": {
        "padding": "20px"
    },
    "label": {
        "color": "#94a3b8",
        "fontWeight": "600",
        "fontSize": "0.85rem",
        "textTransform": "uppercase",
        "letterSpacing": "0.05em",
        "display": "block",
        "marginBottom": "8px"
    },
    "kpi_card": {
        "backgroundColor": "#151722",
        "border": "1px solid #242938",
        "borderRadius": "10px",
        "padding": "15px 10px",
        "textAlign": "center",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
    },
    "kpi_title": {
        "color": "#64748b",
        "fontSize": "0.75rem",
        "textTransform": "uppercase",
        "letterSpacing": "0.05em",
        "fontWeight": "700",
        "marginBottom": "6px"
    }
}

def get_layout():
    # Fetch airlines for filter dropdown
    airlines = get_airlines()
    airline_options = [{"label": "All Airlines", "value": ""}] + [
        {"label": carrier, "value": carrier} for carrier in airlines
    ]
    
    return html.Div(style=STYLES["page_container"], children=[
        # Selected Airport Hidden State
        dcc.Store(id="selected-airport-store", data=None),
        
        # Header Row
        dbc.Row([
            dbc.Col([
                html.H1("Airport Delay Heatmap & Spatial Analytics", style=STYLES["main_title"], className="mb-1"),
                html.P("Explore geographic delay distribution and temporal congestion patterns across U.S. domestic flights.", style=STYLES["subtitle"]),
            ], width=12)
        ], className="mb-4 mt-2"),
        
        # Filters and KPI Stats Row
        dbc.Row([
            # Control Card
            dbc.Col([
                html.Div(style=STYLES["card"], children=[
                    html.Div(style=STYLES["card_header"], children=[
                        html.H5("Filters & Controls", style=STYLES["card_header_text"])
                    ]),
                    html.Div(style=STYLES["card_body"], children=[
                        # Metric Dropdown
                        html.Label("Analysis Metric", style=STYLES["label"]),
                        dcc.Dropdown(
                            id="metric-dropdown",
                            options=[
                                {"label": "Departure Delay (mins)", "value": "DepDelay"},
                                {"label": "Arrival Delay (mins)", "value": "ArrDelay"},
                                {"label": "Taxi-Out Time (mins)", "value": "TaxiOut"},
                                {"label": "Taxi-In Time (mins)", "value": "TaxiIn"},
                                {"label": "Cancellation Rate (%)", "value": "Cancelled"},
                            ],
                            value="DepDelay",
                            clearable=False,
                            className="mb-3",
                            style={"color": "#111111"}
                        ),
                        
                        # Airline Dropdown
                        html.Label("Airline Carrier", style=STYLES["label"]),
                        dcc.Dropdown(
                            id="airline-dropdown",
                            options=airline_options,
                            value="",
                            clearable=False,
                            className="mb-3",
                            style={"color": "#111111"}
                        ),
                        
                        # Season Dropdown
                        html.Label("Season", style=STYLES["label"]),
                        dcc.Dropdown(
                            id="season-dropdown",
                            options=[
                                {"label": "All Seasons", "value": ""},
                                {"label": "Winter (Dec-Feb)", "value": "Winter"},
                                {"label": "Spring (Mar-May)", "value": "Spring"},
                                {"label": "Summer (Jun-Aug)", "value": "Summer"},
                                {"label": "Fall (Sep-Nov)", "value": "Fall"},
                            ],
                            value="",
                            clearable=False,
                            className="mb-4",
                            style={"color": "#111111"}
                        ),
                        
                        # Active Selection Indicator
                        html.Div(id="selection-status-div", className="mb-3", style={"fontSize": "0.9rem"}),
                        
                        # Reset Selection Button
                        dbc.Button(
                            "Reset Airport Filter", 
                            id="reset-airport-btn", 
                            color="outline-warning", 
                            size="sm", 
                            className="w-100 mt-2"
                        )
                    ])
                ])
            ], xs=12, md=4, lg=3, className="mb-4"),
            
            # KPI Cards & Map
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.Div(style=STYLES["kpi_card"], children=[
                            html.Div("Total Flights Represented", style=STYLES["kpi_title"]),
                            html.H3(id="kpi-total-flights", style={"color": "#3b82f6", "fontWeight": "700", "margin": "0"}),
                        ])
                    ], xs=6, md=3, className="mb-3"),
                    dbc.Col([
                        html.Div(style=STYLES["kpi_card"], children=[
                            html.Div("Avg Dep Delay", style=STYLES["kpi_title"]),
                            html.H3(id="kpi-avg-dep-delay", style={"color": "#f59e0b", "fontWeight": "700", "margin": "0"}),
                        ])
                    ], xs=6, md=3, className="mb-3"),
                    dbc.Col([
                        html.Div(style=STYLES["kpi_card"], children=[
                            html.Div("Avg Arr Delay", style=STYLES["kpi_title"]),
                            html.H3(id="kpi-avg-arr-delay", style={"color": "#ec4899", "fontWeight": "700", "margin": "0"}),
                        ])
                    ], xs=6, md=3, className="mb-3"),
                    dbc.Col([
                        html.Div(style=STYLES["kpi_card"], children=[
                            html.Div("Cancellation Rate", style=STYLES["kpi_title"]),
                            html.H3(id="kpi-cancellation-rate", style={"color": "#ef4444", "fontWeight": "700", "margin": "0"}),
                        ])
                    ], xs=6, md=3, className="mb-3"),
                ]),
                
                # Spatial Map Card
                html.Div(style=STYLES["card"], children=[
                    html.Div(style=STYLES["card_header"], children=[
                        html.H5("U.S. Airport Delay Distribution (Map)", style=STYLES["card_header_text"])
                    ]),
                    html.Div([
                        dcc.Graph(id="delay-spatial-map", style={"height": "400px"})
                    ], style={"padding": "10px"})
                ])
            ], xs=12, md=8, lg=9, className="mb-4")
        ], className="mb-2"),
        
        # Temporal Heatmaps Row
        dbc.Row([
            # Day of Week vs Hour
            dbc.Col([
                html.Div(style=STYLES["card"], children=[
                    html.Div(style=STYLES["card_header"], children=[
                        html.H5("Weekly & Hourly Congestion Grids", style=STYLES["card_header_text"])
                    ]),
                    html.Div([
                        dcc.Graph(id="hourly-weekly-heatmap", style={"height": "320px"})
                    ], style={"padding": "10px"})
                ])
            ], xs=12, lg=6, className="mb-4"),
            
            # Month vs Day of Month
            dbc.Col([
                html.Div(style=STYLES["card"], children=[
                    html.Div(style=STYLES["card_header"], children=[
                        html.H5("Seasonal & Monthly Calendars", style=STYLES["card_header_text"])
                    ]),
                    html.Div([
                        dcc.Graph(id="monthly-calendar-heatmap", style={"height": "320px"})
                    ], style={"padding": "10px"})
                ])
            ], xs=12, lg=6, className="mb-4")
        ]),
        
        # Airline Volume vs Delay Scatter Row
        dbc.Row([
            dbc.Col([
                html.Div(style=STYLES["card"], children=[
                    html.Div(style=STYLES["card_header"], children=[
                        html.H5("Flight Volume vs Average Delay by Airline", style=STYLES["card_header_text"])
                    ]),
                    html.Div([
                        dcc.Graph(id="airline-scatter-plot", style={"height": "400px"})
                    ], style={"padding": "10px"})
                ])
            ], width=12, className="mb-4")
        ])
    ])

# Callbacks logic
def register_callbacks(app_ignored):
    """Placeholder for legacy multi-page wiring (now registered globally via @callback)"""
    pass

# Reset selected airport store
@callback(
    Output("selected-airport-store", "data", allow_duplicate=True),
    Input("reset-airport-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_selected_airport(n_clicks):
    return None
    
# Set selected airport on map click
@callback(
    Output("selected-airport-store", "data"),
    Input("delay-spatial-map", "clickData"),
    State("selected-airport-store", "data")
)
def update_selected_airport(clickData, current_selected):
    if not clickData:
        return current_selected
    
    try:
        point = clickData["points"][0]
        faa = point.get("customdata", None)
        if faa:
            # If custom_data is passed, it returns a list like [faa]
            if isinstance(faa, list):
                return faa[0]
            return faa
    except Exception:
        pass
    return current_selected

# Main dashboard update callback
@callback(
    [
        Output("kpi-total-flights", "children"),
        Output("kpi-avg-dep-delay", "children"),
        Output("kpi-avg-arr-delay", "children"),
        Output("kpi-cancellation-rate", "children"),
        Output("selection-status-div", "children"),
        Output("delay-spatial-map", "figure"),
        Output("hourly-weekly-heatmap", "figure"),
        Output("monthly-calendar-heatmap", "figure"),
        Output("airline-scatter-plot", "figure"),
    ],
    [
        Input("metric-dropdown", "value"),
        Input("airline-dropdown", "value"),
        Input("season-dropdown", "value"),
        Input("selected-airport-store", "data"),
        Input("global-route-store", "data"),
    ]
)
def update_dashboard(metric, airline, season, selected_airport, route_data):
    
    # Unpack global filters
    o_state = route_data.get("origin_state") if route_data else None
    d_state = route_data.get("dest_state") if route_data else None
    o_airport = route_data.get("origin_airport") if route_data else None
    d_airport = route_data.get("dest_airport") if route_data else None
    
    # If selected_airport is chosen via map click, override origin_airport
    if selected_airport:
        o_airport = selected_airport
    # 1. Fetch KPI Stats
    kpi_stats = get_overall_kpis(airport=o_airport, airline=airline, season=season)
    
    total_flights = f"{kpi_stats['total_flights']:,}"
    avg_dep = f"{kpi_stats['avg_dep_delay']:.1f} m"
    avg_arr = f"{kpi_stats['avg_arr_delay']:.1f} m"
    cancel_rate = f"{kpi_stats['cancellation_rate']:.2f}%"
    
    # Selection status text
    if selected_airport:
        status_text = html.Div([
            html.Span("Viewing Airport: ", style={"color": "#64748b"}),
            html.Span(f"{selected_airport}", style={"color": "#f59e0b", "fontWeight": "700"})
        ])
    else:
        status_text = html.Span("Viewing National Overview (All Airports)", style={"color": "#10b981", "fontWeight": "600"})

    # 2. Fetch Map Data
    df_map = get_airport_delay_summary(
        airline=airline, season=season, metric=metric,
        origin_state=o_state, dest_state=d_state,
        origin_airport=o_airport, dest_airport=d_airport
    )
    
    # Scaling marker sizes based on flight count
    max_flights = df_map["flight_count"].max() if not df_map.empty else 1
    min_flights = df_map["flight_count"].min() if not df_map.empty else 1
    
    # Map values between 5 and 30 for marker size
    if max_flights == min_flights:
        df_map["marker_size"] = 12
    else:
        df_map["marker_size"] = 5 + (df_map["flight_count"] - min_flights) / (max_flights - min_flights) * 25
        
    # Metric labels for map hover
    metric_labels = {
        "DepDelay": "Avg Departure Delay (mins)",
        "ArrDelay": "Avg Arrival Delay (mins)",
        "TaxiOut": "Avg Taxi-Out Time (mins)",
        "TaxiIn": "Avg Taxi-In Time (mins)",
        "Cancelled": "Cancellation Rate (%)"
    }
    metric_label = metric_labels.get(metric, "Avg Delay")
    
    # Determine Map Zoom and Center based on selection
    map_zoom = 3.2
    map_center = {"lat": 37.0902, "lon": -95.7129}
    
    if selected_airport and not df_map.empty:
        sel_row = df_map[df_map["faa"] == selected_airport]
        if not sel_row.empty:
            map_center = {"lat": float(sel_row.iloc[0]["lat"]), "lon": float(sel_row.iloc[0]["lon"])}
            map_zoom = 9.0  # Zoom in closely on the tapped airport
            
    # Plotly Express map
    fig_map = px.scatter_mapbox(
        df_map,
        lat="lat",
        lon="lon",
        color="avg_metric",
        size="marker_size",
        size_max=25,
        hover_name="name",
        hover_data={
            "faa": True,
            "flight_count": ":,",
            "avg_metric": ":.2f",
            "marker_size": False,
            "lat": False,
            "lon": False
        },
        custom_data=["faa"], # Fixes clickData mapping and hover overlap!
        color_continuous_scale="RdYlGn_r", # green is good, red is bad
        mapbox_style="carto-darkmatter", # Dark themed map
        zoom=map_zoom,
        center=map_center
    )
    
    # Map Layout Adjustments
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#cbd5e1"},
        coloraxis_colorbar=dict(
            title=metric_label,
            title_font=dict(size=11, color="white"),
            tickfont=dict(color="white"),
            len=0.75,
            thickness=15,
            yanchor="middle",
            y=0.5,
            xanchor="right",
            x=0.99
        )
    )
    
    # Highlight selected airport on the map if one is selected
    if selected_airport and not df_map.empty:
        sel_row = df_map[df_map["faa"] == selected_airport]
        if not sel_row.empty:
            fig_map.add_trace(go.Scattermapbox(
                lat=sel_row["lat"],
                lon=sel_row["lon"],
                mode="markers",
                marker=go.scattermapbox.Marker(
                    size=35,
                    color="white", # clean white highlight ring
                    opacity=0.4
                ),
                hoverinfo="none",
                showlegend=False
            ))

    # 3. Fetch Temporal Heatmap Data
    df_hourly, df_monthly = get_temporal_delay_data(
        airport=o_airport, 
        airline=airline, 
        season=season, 
        metric=metric,
        origin_state=o_state, dest_state=d_state,
        origin_airport=o_airport, dest_airport=d_airport
    )
    
    # Build Hourly/Weekly Heatmap Figure
    hourly_grid = np.zeros((7, 24))
    hourly_grid[:] = np.nan
    for _, r in df_hourly.iterrows():
        d_idx = int(r["DayOfWeek"])
        h_idx = int(r["DepHour"])
        if 0 <= d_idx < 7 and 0 <= h_idx < 24:
            hourly_grid[d_idx, h_idx] = r["avg_val"]
            
    fig_hourly = go.Figure(data=go.Heatmap(
        z=hourly_grid,
        x=[f"{h:02d}:00" for h in range(24)],
        y=DAYS_OF_WEEK,
        colorscale="YlOrRd",
        colorbar=dict(title=metric_label, tickfont=dict(color="#cbd5e1")),
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>Value: %{z:.2f}<extra></extra>"
    ))
    
    fig_hourly.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"r": 10, "t": 10, "l": 10, "b": 10},
        font={"color": "#cbd5e1"},
        xaxis=dict(title="Hour of Day Scheduled", gridcolor="#242938", tickangle=45),
        yaxis=dict(gridcolor="#242938")
    )
    
    # Build Monthly/Daily Grid Figure
    monthly_grid = np.zeros((12, 31))
    monthly_grid[:] = np.nan
    for _, r in df_monthly.iterrows():
        m_idx = int(r["Month"]) - 1
        d_idx = int(r["DayofMonth"]) - 1
        if 0 <= m_idx < 12 and 0 <= d_idx < 31:
            monthly_grid[m_idx, d_idx] = r["avg_val"]
            
    fig_monthly = go.Figure(data=go.Heatmap(
        z=monthly_grid,
        x=[str(d) for d in range(1, 32)],
        y=MONTHS,
        colorscale="YlOrRd",
        colorbar=dict(title=metric_label, tickfont=dict(color="#cbd5e1")),
        hovertemplate="Month: %{y}<br>Day: %{x}<br>Value: %{z:.2f}<extra></extra>"
    ))
    
    fig_monthly.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"r": 10, "t": 10, "l": 10, "b": 10},
        font={"color": "#cbd5e1"},
        xaxis=dict(title="Day of Month", gridcolor="#242938"),
        yaxis=dict(gridcolor="#242938")
    )
    
    
    # 4. Fetch Scatter Plot Data
    # Get scatter data using global filters, we don't pass airport here so it uses global origin
    # Wait, the get_airline_volume_delay_scatter from db doesn't take origin_state etc.
    # Actually, I should update `get_airline_volume_delay_scatter` in db.py if I haven't.
    # Ah, I missed updating `get_airline_volume_delay_scatter` in db.py to take state/airport!
    # Let me just pass the global filters if supported, or I'll need to update db.py.
    # Let's assume I will update it.
    
    # For now I will just call it as is, and I'll update db.py in the next step.
    df_scatter = get_airline_volume_delay_scatter(
        season=season, month=None,
        origin_state=o_state, dest_state=d_state,
        origin_airport=o_airport, dest_airport=d_airport
    )
    
    scatter_fig = px.scatter(
        df_scatter,
        x="Flights",
        y="AverageDelay",
        size="Flights",
        color="Airline",
        title="Flight Volume vs Average Delay"
    )
    scatter_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return (
        total_flights,
        avg_dep,
        avg_arr,
        cancel_rate,
        status_text,
        fig_map,
        fig_hourly,
        fig_monthly,
        scatter_fig
    )

# Main entrypoint layout reference
layout = get_layout()
