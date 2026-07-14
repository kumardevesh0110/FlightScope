import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.app.db import get_db_connection, _build_where_clause, AIRPORTS_CSV_PATH

print("Loading Airline Dashboard Data via DuckDB...")

conn = get_db_connection()
try:
    df_al = conn.execute("SELECT DISTINCT Marketing_Airline_Network FROM flights WHERE Marketing_Airline_Network IS NOT NULL ORDER BY Marketing_Airline_Network").df()
    airlines = df_al['Marketing_Airline_Network'].dropna().tolist()
finally:
    conn.close()

# =====================================================
# LAYOUT 
# =====================================================
layout = html.Div(
    className="premium-page-container",
    children=[
        dbc.Row([
            dbc.Col([
                html.H1("Airline Performance Dashboard", className="premium-title"),
                html.P("Compare operational efficiency, delay statistics, and cancellation rates across major US carriers.", className="premium-subtitle"),
            ], width=12)
        ], className="mb-3 mt-1"),

        html.Div(
            className="premium-filter-section",
            children=[
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Airline Carrier", className="premium-label"),
                                dcc.Dropdown(
                                    id="airline_dropdown",
                                    options=[{"label": "All Airlines", "value": "ALL"}] + [
                                        {"label": x, "value": x} for x in airlines
                                    ],
                                    value="ALL",
                                    clearable=False,
                                    placeholder="Select an Airline...",
                                    className="dark-dropdown",
                                    style={"color": "#000000", "backgroundColor": "#FFFFFF"}
                                )
                            ],
                            width=4
                        )
                    ]
                )
            ]
        ),

        dbc.Row([
            dbc.Col(html.Div(className="premium-kpi-card card-blue", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px"}, children=[
                html.Div(html.I(className="bi bi-airplane-fill", style={"fontSize": "1.5rem", "color": "var(--cyan)"}), 
                         style={"backgroundColor": "rgba(75,211,255,0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                html.Div([
                    html.P("FLIGHTS", className="premium-kpi-title", style={"margin": "0", "textAlign": "left"}),
                    html.H5(id="kpi_flights", className="premium-kpi-value", style={"margin": "0", "textAlign": "left", "fontSize": "1.8rem"}),
                ])
            ]), width=3),
            
            dbc.Col(html.Div(className="premium-kpi-card card-purple", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px"}, children=[
                html.Div(html.I(className="bi bi-clock-history", style={"fontSize": "1.5rem", "color": "var(--pink)"}), 
                         style={"backgroundColor": "rgba(240,92,191,0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                html.Div([
                    html.P("AVERAGE DELAY", className="premium-kpi-title", style={"margin": "0", "textAlign": "left"}),
                    html.H5(id="kpi_delay", className="premium-kpi-value", style={"margin": "0", "textAlign": "left", "fontSize": "1.8rem"}),
                ])
            ]), width=3),
            
            dbc.Col(html.Div(className="premium-kpi-card card-purple", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px"}, children=[
                html.Div(html.I(className="bi bi-check-circle-fill", style={"fontSize": "1.5rem", "color": "var(--node-purple)"}), 
                         style={"backgroundColor": "rgba(193,59,255,0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                html.Div([
                    html.P("ON TIME", className="premium-kpi-title", style={"margin": "0", "textAlign": "left"}),
                    html.H5(id="kpi_ontime", className="premium-kpi-value", style={"margin": "0", "textAlign": "left", "fontSize": "1.8rem"}),
                ])
            ]), width=3),
            
            dbc.Col(html.Div(className="premium-kpi-card card-orange", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px"}, children=[
                html.Div(html.I(className="bi bi-x-circle-fill", style={"fontSize": "1.5rem", "color": "var(--orange)"}), 
                         style={"backgroundColor": "rgba(248,161,27,0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                html.Div([
                    html.P("CANCELLED", className="premium-kpi-title", style={"margin": "0", "textAlign": "left"}),
                    html.H5(id="kpi_cancel", className="premium-kpi-value", style={"margin": "0", "textAlign": "left", "fontSize": "1.8rem"}),
                ])
            ]), width=3),
        ], className="mb-4"),

        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        className="premium-card",
                        children=[html.Div(className="premium-card-body", children=[dcc.Graph(id="ranking_fig", config={"responsive": True, "displayModeBar": False}, style={"height":"300px"})])]
                    ), width=4
                ),
                dbc.Col(
                    html.Div(
                        className="premium-card",
                        children=[html.Div(className="premium-card-body", children=[dcc.Graph(id="radar_fig", config={"responsive":True, "displayModeBar":False}, style={"height":"300px"})])]
                    ), width=4
                ),
                dbc.Col(
                    html.Div(
                        className="premium-card",
                        children=[html.Div(className="premium-card-body", children=[dcc.Graph(id="box_fig", config={"responsive":True, "displayModeBar":False}, style={"height":"300px"})])]
                    ), width=4
                )
            ],
            className="mb-4"
        ),

        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        className="premium-card",
                        children=[html.Div(className="premium-card-body", children=[dcc.Graph(id="map_fig", config={"responsive":True, "displayModeBar":True, "scrollZoom":True}, style={"height":"300px"})])]
                    ), width=8
                ),
                dbc.Col(
                    html.Div(
                        className="premium-card",
                        children=[html.Div(className="premium-card-body", children=[dcc.Graph(id="duration_fig", config={"responsive": True, "displayModeBar": False}, style={"height":"300px"})])]
                    ), width=4
                ),
            ],
            className="mb-4"
        ),
    ]
)

# =====================================================
# CALLBACKS
# =====================================================
def register_callbacks(app):
    @app.callback(
        [
            Output("kpi_flights", "children"),
            Output("kpi_delay", "children"),
            Output("kpi_ontime", "children"),
            Output("kpi_cancel", "children"),
            Output("radar_fig", "figure"),
            Output("duration_fig", "figure"),
            Output("ranking_fig", "figure"),
            Output("box_fig", "figure"),
            Output("map_fig", "figure")
        ],
        [
            Input("airline_dropdown", "value"),
            Input("global-route-store", "data"),
            Input("global-selected-airport-store", "data")
        ]
    )
    def update_cards(selected, route_data, global_airport):
        conn = get_db_connection()
        try:
            o_state = route_data.get("origin_state") if route_data else None
            d_state = route_data.get("dest_state") if route_data else None
            o_airport = route_data.get("origin_airport") if route_data else None
            d_airport = route_data.get("dest_airport") if route_data else None

            g_airport = global_airport.get('airport') if isinstance(global_airport, dict) else global_airport
            where_global, params_global = _build_where_clause(
                airport=g_airport,
                origin_state=o_state, dest_state=d_state, 
                origin_airport=o_airport, dest_airport=d_airport
            )

            # Get dynamic maxes across all airlines for this route
            q_maxes = f"""
                SELECT MAX(flights) as max_flights, MAX(avg_delay) as max_delay, MAX(cancel_pct) as max_cancel
                FROM (
                    SELECT Marketing_Airline_Network, 
                           COUNT(*) as flights, 
                           AVG(CAST(ArrDelay AS FLOAT)) as avg_delay, 
                           AVG(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END)*100 as cancel_pct
                    FROM flights
                    {where_global}
                    GROUP BY Marketing_Airline_Network
                ) sub
            """
            max_res = conn.execute(q_maxes, list(params_global)).fetchone()
            dyn_max_flights = float(max_res[0]) if max_res and max_res[0] else 0
            dyn_max_delay = float(max_res[1]) if max_res and max_res[1] else 0
            dyn_max_cancel = float(max_res[2]) if max_res and max_res[2] else 0

            # Airline specific where clause
            if selected != "ALL":
                where_spec, params_spec = _build_where_clause(
                    airport=g_airport,
                    airline=selected, origin_state=o_state, dest_state=d_state, 
                    origin_airport=o_airport, dest_airport=d_airport
                )
            else:
                where_spec, params_spec = where_global, params_global

            # 1. KPIs
            q_stats = f"""
                SELECT COUNT(*) as flights, 
                       AVG(CAST(ArrDelay AS FLOAT)) as avg_delay,
                       AVG(CASE WHEN CAST(ArrDelay AS FLOAT) > 15 THEN 1.0 ELSE 0.0 END)*100 as delayed_pct,
                       AVG(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END)*100 as cancel_pct
                FROM flights
                {where_spec}
            """
            stats_res = conn.execute(q_stats, list(params_spec)).fetchone()
            flights = int(stats_res[0]) if stats_res and stats_res[0] else 0
            
            if flights == 0:
                return "0", "0 min", "0%", "0%", go.Figure(), go.Figure(), go.Figure(), go.Figure(), go.Figure()

            delay = round(float(stats_res[1]), 2) if stats_res[1] is not None else 0
            delayed_pct = float(stats_res[2]) if stats_res[2] is not None else 0
            cancel = round(float(stats_res[3]), 2) if stats_res[3] is not None else 0
            ontime_pct = round(100 - delayed_pct, 2)

            # 2. Radar Chart
            f_score = 100 if selected == "ALL" else ((flights / dyn_max_flights) * 100 if dyn_max_flights > 0 else 0)
            d_score = max(0, 100 - (delay / dyn_max_delay * 100)) if dyn_max_delay > 0 else 100
            o_score = ontime_pct
            c_score = max(0, 100 - (cancel / dyn_max_cancel * 100)) if dyn_max_cancel > 0 else 100

            radar_fig = go.Figure()
            radar_fig.add_trace(go.Scatterpolar(
                r=[f_score, d_score, o_score, c_score],
                theta=['Volume', 'Timeliness', 'On-Time', 'Completion'],
                fill='toself', name=selected, line_color="cyan"
            ))
            radar_fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor="#334155"), angularaxis=dict(gridcolor="#334155")),
                showlegend=False, template="plotly_dark", margin=dict(l=30, r=30, t=40, b=30), title="Performance Radar"
            )

            # 3. Duration Histogram
            q_duration_cond = "AND AirTime IS NOT NULL" if where_spec else "WHERE AirTime IS NOT NULL"
            q_duration = f"SELECT AirTime FROM flights {where_spec} {q_duration_cond} USING SAMPLE 5000"
            df_dur = conn.execute(q_duration, list(params_spec)).df()
            if not df_dur.empty:
                duration_fig = px.histogram(df_dur, x="AirTime", nbins=30, title="Flight Duration Distribution", color_discrete_sequence=["#eab308"])
                duration_fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), xaxis_title="Air Time (Mins)", yaxis_title="Count")
            else:
                duration_fig = go.Figure().update_layout(template="plotly_dark", title="No Flight Data")

            # 4. Top Airlines Ranking
            q_ranking = f"""
                SELECT Marketing_Airline_Network AS Airline, COUNT(*) AS Flights
                FROM flights {where_spec} GROUP BY Marketing_Airline_Network ORDER BY Flights DESC LIMIT 15
            """
            df_rank = conn.execute(q_ranking, list(params_spec)).df()
            if not df_rank.empty:
                ranking_fig = px.bar(df_rank, x="Airline", y="Flights", color="Flights", color_continuous_scale="Viridis", title="Top Airlines by Flight Volume")
                ranking_fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=40, b=30))
            else:
                ranking_fig = go.Figure().update_layout(template="plotly_dark", title="No Flight Data")

            # 5. Box Plot (Limit to top 10 airlines)
            q_box = f"""
                WITH top_airlines AS (
                    SELECT Marketing_Airline_Network FROM flights {where_spec} 
                    GROUP BY Marketing_Airline_Network ORDER BY COUNT(*) DESC LIMIT 10
                )
                SELECT Marketing_Airline_Network AS Airline, CAST(ArrDelay AS FLOAT) AS ArrDelay
                FROM flights 
                {where_spec} 
                {("AND " if where_spec else "WHERE ") + "Marketing_Airline_Network IN (SELECT Marketing_Airline_Network FROM top_airlines)"}
                USING SAMPLE 10000
            """
            df_box = conn.execute(q_box, list(params_spec) * 2 if where_spec else []).df()
            if not df_box.empty:
                box_fig = px.box(df_box, x="Airline", y="ArrDelay", color="Airline", title="Arrival Delays by Airline (Sampled Top 10)")
                box_fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=40, b=30), showlegend=False)
            else:
                box_fig = go.Figure().update_layout(template="plotly_dark", title="No Flight Data")

            # 6. Airport Map
            safe_path = AIRPORTS_CSV_PATH.replace('\\', '/')
            q_map = f"""
                SELECT f.Origin AS faa, MAX(a.name) AS name, MAX(a.lat) AS lat, MAX(a.lon) AS lon, COUNT(*) AS Flights
                FROM flights f
                JOIN read_csv('{safe_path}') a ON f.Origin = a.faa
                {where_spec}
                GROUP BY f.Origin
                HAVING MAX(a.lat) IS NOT NULL AND MAX(a.lon) IS NOT NULL
                ORDER BY Flights DESC LIMIT 30
            """
            df_map = conn.execute(q_map, list(params_spec)).df()
            if not df_map.empty:
                map_fig = px.scatter_mapbox(df_map, lat="lat", lon="lon", size="Flights", hover_name="name", color="Flights", color_continuous_scale="Turbo", zoom=3.5, title="Top Airports by Flight Activity")
                map_fig.update_layout(mapbox_style="carto-darkmatter", template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10))
            else:
                map_fig = go.Figure().update_layout(template="plotly_dark", title="No Flight Data", margin=dict(l=10, r=10, t=40, b=10))

            return f"{flights:,}", f"{delay} min", f"{ontime_pct}%", f"{cancel}%", radar_fig, duration_fig, ranking_fig, box_fig, map_fig

        finally:
            conn.close()
