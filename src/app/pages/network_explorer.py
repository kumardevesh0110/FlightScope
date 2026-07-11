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
LABEL_STYLE = {
    "fontSize": "0.7rem", "fontWeight": "600", "color": "#94a3b8",
    "textTransform": "uppercase", "letterSpacing": "0.05em", "marginBottom": "2px",
}
CARD_BG = "#111318"
KPI_CARD_STYLE = {
    "background": "linear-gradient(135deg, #151822 0%, #1a1f2e 100%)",
    "border": "1px solid #242938", "borderRadius": "10px",
    "padding": "10px 14px", "textAlign": "center",
}
KPI_TITLE_STYLE = {"fontSize": "0.65rem", "color": "#64748b", "textTransform": "uppercase", "margin": "0"}
KPI_VALUE_STYLE = {"fontSize": "1.25rem", "fontWeight": "700", "margin": "2px 0 0 0"}
FILTER_SECTION_STYLE = {
    "background": "linear-gradient(135deg, #111318 0%, #141820 100%)",
    "border": "1px solid #1e293b", "borderRadius": "12px",
    "padding": "14px 18px", "marginBottom": "10px",
}
STATUS_BADGE_STYLE = {
    "background": "linear-gradient(90deg, #0f172a 0%, #1e293b 100%)",
    "border": "1px solid #334155", "borderRadius": "20px",
    "padding": "5px 16px", "display": "inline-block", "fontSize": "0.8rem",
}


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
        style={"padding": "12px 16px"},
        children=[
            dcc.Store(id="network-selected-airport-store", data=None),

            # ── Title ──────────────────────────────────────────────
            html.Div([
                html.H4("✈️ Air Traffic Network Explorer",
                         style={"margin": "0", "fontWeight": "700", "letterSpacing": "-0.02em"}),
                html.P("Explore hub airports, busy routes, and state-to-state connectivity across the US flight network.",
                        style={"color": "#64748b", "margin": "2px 0 8px 0", "fontSize": "0.85rem"}),
            ]),

            # ── Row 1: Core filters ───────────────────────────────
            html.Div(style=FILTER_SECTION_STYLE, children=[
                dbc.Row([
                    dbc.Col([
                        html.Div("Airline", style=LABEL_STYLE),
                        dcc.Dropdown(id="network-airline-dropdown", options=airline_options,
                                     value="", clearable=False, className="dark-dropdown",
                                     style={"fontSize": "0.85rem"}),
                    ], lg=4, md=6, sm=12),
                    dbc.Col([
                        html.Div("Season", style=LABEL_STYLE),
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
                        html.Div("Top N routes", style=LABEL_STYLE),
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
                dbc.Col(html.Div(style=KPI_CARD_STYLE, children=[
                    html.P("Airports", style=KPI_TITLE_STYLE),
                    html.H5(id="network-kpi-airports", style={**KPI_VALUE_STYLE, "color": "#38bdf8"}),
                ]), lg=3, md=3, sm=6),
                dbc.Col(html.Div(style=KPI_CARD_STYLE, children=[
                    html.P("Routes", style=KPI_TITLE_STYLE),
                    html.H5(id="network-kpi-routes", style={**KPI_VALUE_STYLE, "color": "#34d399"}),
                ]), lg=3, md=3, sm=6),
                dbc.Col(html.Div(style=KPI_CARD_STYLE, children=[
                    html.P("Top Hub (PageRank)", style=KPI_TITLE_STYLE),
                    html.H5(id="network-kpi-hub", style={**KPI_VALUE_STYLE, "color": "#a78bfa"}),
                ]), lg=3, md=3, sm=6),
                dbc.Col(html.Div(style=KPI_CARD_STYLE, children=[
                    html.P("Busiest Route", style=KPI_TITLE_STYLE),
                    html.H5(id="network-kpi-busiest", style={**KPI_VALUE_STYLE, "color": "#fbbf24"}),
                ]), lg=3, md=3, sm=6),
            ], className="g-2 mb-2"),

            # ── Map ───────────────────────────────────────────────
            dbc.Card(
                dbc.CardBody(
                    dcc.Graph(id="network-map-graph", style={"height": "72vh"}),
                    style={"padding": "6px"},
                ),
                style={"background": CARD_BG, "border": "1px solid #1e293b", "borderRadius": "12px"},
            ),
        ],
    )


def register_callbacks(app_ignored):
    """Placeholder for legacy multi-page wiring (callback is registered globally via @callback)."""
    pass


# ── Callback: click → selected airport store ───────────────
@callback(
    Output("network-selected-airport-store", "data"),
    Input("network-map-graph", "clickData"),
    State("network-selected-airport-store", "data"),
)
def update_selected_airport(clickData, current_selected):
    if clickData:
        try:
            point = clickData["points"][0]
            faa = point.get("customdata")
            if isinstance(faa, list):
                faa = faa[0]
            if faa:
                return faa
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
        Input("network-selected-airport-store", "data"),
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
            **STATUS_BADGE_STYLE, "color": "#f0abfc",
        })
    else:
        status_badge = html.Span("🌐 National Network Overview", style={
            **STATUS_BADGE_STYLE, "color": "#34d399",
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
