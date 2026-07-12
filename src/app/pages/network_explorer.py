# 4.1 Air Traffic Network Explorer
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from src.app.db import get_airlines, get_airport_list, get_network_data, get_states

try:
    dash.register_page(__name__, path="/network-explorer", name="Air Traffic Network Explorer")
except Exception:
    pass

# ── Shared inline styles ──────────────────────────────────────────────
# Moved to premium.css

def get_layout():
    airlines = get_airlines()
    airline_options = [{"label": "All Airlines", "value": ""}] + [
        {"label": carrier, "value": carrier} for carrier in airlines
    ]

    airports_df = get_airport_list()
    airport_options = [{"label": "All Airports", "value": ""}] + [
        {"label": f"{row.faa} – {row.name}", "value": row.faa} for row in airports_df.itertuples()
    ]

    states = get_states()
    state_options = [{"label": "Any State", "value": ""}] + [
        {"label": name, "value": code} for code, name in states
    ]

    return html.Div(
        className="premium-page-container",
        children=[

            # ── Title ──────────────────────────────────────────────
            html.Div([
                html.H1("Air Traffic Network Explorer", className="premium-title"),
                html.P("Explore hub airports, busy routes, and state-to-state connectivity across the US flight network.", className="premium-subtitle"),
            ]),

            # ── Row 1: Core filters ───────────────────────────────
            html.Div(className="premium-filter-section", children=[
                dbc.Row([
                    dbc.Col([
                        html.Div("Airline", className="premium-label"),
                        dcc.Dropdown(id="network-airline-dropdown", options=airline_options,
                                     value="", clearable=False, className="dark-dropdown",
                                     style={"fontSize": "0.85rem"}),
                    ], lg=4, md=6, sm=12),
                    dbc.Col([
                        html.Div("Season", className="premium-label"),
                        dcc.Dropdown(
                            id="network-season-dropdown",
                            options=[
                                {"label": "All Seasons", "value": ""},
                                {"label": "Winter (Dec-Feb)", "value": "Winter"},
                                {"label": "Spring (Mar-May)", "value": "Spring"},
                                {"label": "Summer (Jun-Aug)", "value": "Summer"},
                                {"label": "Fall (Sep-Nov)", "value": "Fall"},
                            ],
                            value="", clearable=False, className="dark-dropdown",
                            style={"fontSize": "0.85rem"},
                        ),
                    ], lg=3, md=6, sm=12),
                    dbc.Col([
                        html.Div("Top N routes", className="premium-label"),
                        dcc.Slider(
                            id="network-topn-slider",
                            min=50, max=2000, step=None,
                            marks={v: {"label": str(v), "style": {"fontSize": "0.7rem", "color": "#94a3b8"}}
                                   for v in [50, 100, 200, 500, 1000, 2000]},
                            value=200,
                        ),
                    ], lg=5, md=12, sm=12),
                ], className="g-2"),
                
                dbc.Row([
                    dbc.Col([
                        html.Div(id="network-filter-status-badge", className="mt-3"),
                    ], width=12, className="d-flex align-items-end justify-content-end")
                ], className="g-2 mt-2")
            ]),

            # ── KPI strip ─────────────────────────────────────────
            dbc.Row([
                dbc.Col(html.Div(className="premium-kpi-card", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px", "backgroundColor": "#191b28", "borderRadius": "12px", "border": "1px solid #242938"}, children=[
                    html.Div(html.I(className="bi bi-airplane-fill", style={"fontSize": "1.5rem", "color": "#a78bfa"}), 
                             style={"backgroundColor": "rgba(167, 139, 250, 0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                    html.Div([
                        html.P("AIRPORTS", className="premium-kpi-title", style={"margin": "0", "textAlign": "left", "color": "#a78bfa"}),
                        html.H5(id="network-kpi-airports", className="premium-kpi-value", style={"color": "#ffffff", "margin": "0", "textAlign": "left", "fontSize": "1.8rem"}),
                    ])
                ]), lg=3, md=3, sm=6),
                
                dbc.Col(html.Div(className="premium-kpi-card", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px", "backgroundColor": "#161b2a", "borderRadius": "12px", "border": "1px solid #1e293b"}, children=[
                    html.Div(html.I(className="bi bi-diagram-3-fill", style={"fontSize": "1.5rem", "color": "#38bdf8"}), 
                             style={"backgroundColor": "rgba(56, 189, 248, 0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                    html.Div([
                        html.P("ROUTES", className="premium-kpi-title", style={"margin": "0", "textAlign": "left", "color": "#38bdf8"}),
                        html.H5(id="network-kpi-routes", className="premium-kpi-value", style={"color": "#ffffff", "margin": "0", "textAlign": "left", "fontSize": "1.8rem"}),
                    ])
                ]), lg=3, md=3, sm=6),
                
                dbc.Col(html.Div(className="premium-kpi-card", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px", "backgroundColor": "#1e182d", "borderRadius": "12px", "border": "1px solid #2d2442"}, children=[
                    html.Div(html.I(className="bi bi-building", style={"fontSize": "1.5rem", "color": "#c084fc"}), 
                             style={"backgroundColor": "rgba(192, 132, 252, 0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                    html.Div([
                        html.P("TOP HUB (PAGERANK)", className="premium-kpi-title", style={"margin": "0", "textAlign": "left", "color": "#c084fc"}),
                        html.H5(id="network-kpi-hub", className="premium-kpi-value", style={"color": "#ffffff", "margin": "0", "textAlign": "left", "fontSize": "1.8rem"}),
                    ])
                ]), lg=3, md=3, sm=6),
                
                dbc.Col(html.Div(className="premium-kpi-card", style={"display": "flex", "alignItems": "center", "textAlign": "left", "padding": "15px", "backgroundColor": "#29211c", "borderRadius": "12px", "border": "1px solid #3d312a"}, children=[
                    html.Div(html.I(className="bi bi-airplane-engines-fill", style={"fontSize": "1.5rem", "color": "#fbbf24"}), 
                             style={"backgroundColor": "rgba(251, 191, 36, 0.15)", "padding": "12px 16px", "borderRadius": "8px", "marginRight": "15px"}),
                    html.Div([
                        html.P("BUSIEST ROUTE", className="premium-kpi-title", style={"margin": "0", "textAlign": "left", "color": "#fbbf24"}),
                        html.H5(id="network-kpi-busiest", className="premium-kpi-value", style={"color": "#fbbf24", "margin": "0", "textAlign": "left", "fontSize": "1.6rem"}),
                    ])
                ]), lg=3, md=3, sm=6),
            ], className="g-2 mb-2"),

            # ── Map ───────────────────────────────────────────────
            html.Div(
                className="premium-card",
                children=[
                    dcc.Graph(
                        id="network-map-graph", 
                        style={"height": "72vh"}, 
                        config={"responsive": True, "displayModeBar": True, "scrollZoom": True}
                    )
                ]
            ),
        ],
    )


def register_callbacks(app_ignored):
    """Placeholder for legacy multi-page wiring (callback is registered globally via @callback)."""
    pass


# ── Callback: click → selected airport store ───────────────
@callback(
    Output("global-selected-airport-store", "data", allow_duplicate=True),
    Input("network-map-graph", "clickData"),
    State("global-selected-airport-store", "data"),
    prevent_initial_call=True
)
def update_selected_airport(clickData, current_selected):
    if clickData:
        try:
            point = clickData["points"][0]
            faa = point.get("customdata")
            if isinstance(faa, list):
                faa = faa[0]
            if faa:
                return {'airport': faa}
        except Exception:
            pass
    return current_selected


# ── Main update callback ──────────────────────────────────────────────
@callback(
    [
        Output("network-kpi-airports", "children"),
        Output("network-kpi-routes", "children"),
        Output("network-kpi-hub", "children"),
        Output("network-kpi-busiest", "children"),
        Output("network-filter-status-badge", "children"),
        Output("network-map-graph", "figure"),
    ],
    [
        Input("network-airline-dropdown", "value"),
        Input("network-season-dropdown", "value"),
        Input("network-topn-slider", "value"),
        Input("global-selected-airport-store", "data"),
        Input("global-route-store", "data"),
    ],
)
def update_network(airline, season, top_n, selected_airport, route_data):
    
    # Unpack global filters
    o_state = route_data.get("origin_state") if route_data else None
    d_state = route_data.get("dest_state") if route_data else None
    o_airport = route_data.get("origin_airport") if route_data else None
    d_airport = route_data.get("dest_airport") if route_data else None
    
    origin_state = o_state
    dest_state = d_state
    
    selected_airport = selected_airport.get('airport') if isinstance(selected_airport, dict) else selected_airport
    if selected_airport:
        o_airport = selected_airport
    # ── Build contextual status badge ─────────────────────────────
    parts = []
    if origin_state and dest_state:
        parts.append(f"🗺️ {origin_state} → {dest_state}")
    elif origin_state:
        parts.append(f"🗺️ From {origin_state}")
    elif dest_state:
        parts.append(f"🗺️ To {dest_state}")
    if selected_airport:
        parts.append(f"✈️ {selected_airport}")
    if airline:
        parts.append(f"🏷️ {airline}")
    if season:
        parts.append(f"🌤️ {season}")

    if parts:
        badge_text = " · ".join(parts)
        status_badge = html.Span(badge_text, style={
            "fontSize": "0.85rem", "fontWeight": "600", "padding": "6px 12px", 
            "borderRadius": "20px", "backgroundColor": "rgba(255,255,255,0.05)", 
            "border": "1px solid rgba(255,255,255,0.1)", "color": "#f0abfc",
        })
    else:
        status_badge = html.Span("🌐 National Network Overview", style={
            "fontSize": "0.85rem", "fontWeight": "600", "padding": "6px 12px", 
            "borderRadius": "20px", "backgroundColor": "rgba(255,255,255,0.05)", 
            "border": "1px solid rgba(255,255,255,0.1)", "color": "#34d399",
        })

    # ── Fetch data ────────────────────────────────────────────────
    df_edges, df_nodes = get_network_data(
        airline=airline, season=season, airport=o_airport,
        origin_state=origin_state or None, dest_state=dest_state or None,
        origin_airport=o_airport or None, dest_airport=d_airport or None
    )

    if df_edges.empty or df_nodes.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template="plotly_dark", mapbox_style="carto-darkmatter",
            mapbox=dict(center={"lat": 37.09, "lon": -95.71}, zoom=3),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="#111318", plot_bgcolor="#111318",
        )
        return "0", "0", "N/A", "N/A", status_badge, empty_fig

    top_edges = df_edges.sort_values("weight", ascending=False).head(int(top_n))
    node_lookup = df_nodes.set_index("faa")
    top_edges = top_edges[top_edges["Origin"].isin(node_lookup.index) & top_edges["Dest"].isin(node_lookup.index)]

    # ── Build map figure ──────────────────────────────────────────
    fig = go.Figure()

    # Route lines – bucket into traffic tiers
    if not top_edges.empty:
        tiers = pd.qcut(top_edges["weight"], q=min(3, top_edges["weight"].nunique()), duplicates="drop")
        tier_styles = [
            {"width": 1,   "color": "rgba(100,150,255,0.20)"},
            {"width": 1.8, "color": "rgba(100,200,255,0.45)"},
            {"width": 3,   "color": "rgba(251,191,36,0.75)"},
        ]
        for i, (_, group) in enumerate(top_edges.groupby(tiers, observed=True)):
            lats, lons = [], []
            for row in group.itertuples():
                lats += [node_lookup.at[row.Origin, "lat"], node_lookup.at[row.Dest, "lat"], None]
                lons += [node_lookup.at[row.Origin, "lon"], node_lookup.at[row.Dest, "lon"], None]
            style = tier_styles[min(i, len(tier_styles) - 1)]
            fig.add_trace(go.Scattermapbox(
                lat=lats, lon=lons, mode="lines",
                line=dict(width=style["width"], color=style["color"]),
                hoverinfo="skip", showlegend=False,
            ))

    # Airport nodes
    shown_nodes = node_lookup.loc[node_lookup.index.isin(
        pd.concat([top_edges["Origin"], top_edges["Dest"]]).unique()
    )] if not top_edges.empty else node_lookup.iloc[0:0]

    if not shown_nodes.empty:
        max_pr, min_pr = shown_nodes["pagerank"].max(), shown_nodes["pagerank"].min()
        if max_pr == min_pr:
            marker_size = pd.Series(14, index=shown_nodes.index)
        else:
            marker_size = 8 + (shown_nodes["pagerank"] - min_pr) / (max_pr - min_pr) * 30

        fig.add_trace(go.Scattermapbox(
            lat=shown_nodes["lat"], lon=shown_nodes["lon"], mode="markers",
            marker=dict(
                size=marker_size, color=shown_nodes["betweenness"],
                colorscale="Plasma", showscale=True,
                colorbar=dict(title="Betweenness", thickness=12, len=0.5, y=0.5),
            ),
            customdata=shown_nodes.index,
            text=[f"<b>{faa}</b> – {name}<br>Degree: {d:.3f}<br>PageRank: {pr:.4f}"
                  for faa, name, d, pr in zip(shown_nodes.index, shown_nodes["name"],
                                               shown_nodes["degree"], shown_nodes["pagerank"])],
            hoverinfo="text",
            showlegend=False,
        ))

    fig.update_layout(
        template="plotly_dark",
        mapbox_style="carto-darkmatter",
        mapbox=dict(center={"lat": 37.09, "lon": -95.71}, zoom=3.2),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#111318",
        plot_bgcolor="#111318",
    )

    # ── KPIs ──────────────────────────────────────────────────────
    kpi_airports = f"{len(shown_nodes):,}"
    kpi_routes = f"{len(top_edges):,}"
    kpi_hub = "N/A"
    if not shown_nodes.empty:
        kpi_hub = shown_nodes.sort_values("pagerank", ascending=False).index[0]
    kpi_busiest = "N/A"
    if not top_edges.empty:
        busiest = top_edges.sort_values("weight", ascending=False).iloc[0]
        kpi_busiest = f"{busiest['Origin']} → {busiest['Dest']}"

    return kpi_airports, kpi_routes, kpi_hub, kpi_busiest, status_badge, fig


layout = get_layout()
