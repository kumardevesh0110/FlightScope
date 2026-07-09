# 4.1 Air Traffic Network Explorer
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from src.app.db import get_airlines, get_airport_list, get_network_data

try:
    dash.register_page(__name__, path="/network-explorer", name="Air Traffic Network Explorer")
except Exception:
    pass


def get_layout():
    airlines = get_airlines()
    airline_options = [{"label": "All Airlines", "value": ""}] + [
        {"label": carrier, "value": carrier} for carrier in airlines
    ]

    airports_df = get_airport_list()
    airport_options = [{"label": "All Airports", "value": ""}] + [
        {"label": f"{row.faa} - {row.name}", "value": row.faa} for row in airports_df.itertuples()
    ]

    return html.Div(
        style={"padding": "20px"},
        children=[
            dcc.Store(id="network-selected-airport-store", data=None),

            html.H1("Air Traffic Network Explorer", className="mb-1"),
            html.P("Explore hub airports and busy routes across the US flight network.", className="text-muted mb-4"),

            dbc.Row([
                dbc.Col([
                    html.Label("Airport (origin)"),
                    dcc.Dropdown(id="network-airport-dropdown", options=airport_options, value="", clearable=False),
                ], width=4),
                dbc.Col([
                    html.Label("Airline"),
                    dcc.Dropdown(id="network-airline-dropdown", options=airline_options, value="", clearable=False),
                ], width=4),
                dbc.Col([
                    html.Label("Season"),
                    dcc.Dropdown(
                        id="network-season-dropdown",
                        options=[
                            {"label": "All Seasons", "value": ""},
                            {"label": "Winter (Dec-Feb)", "value": "Winter"},
                            {"label": "Spring (Mar-May)", "value": "Spring"},
                            {"label": "Summer (Jun-Aug)", "value": "Summer"},
                            {"label": "Fall (Sep-Nov)", "value": "Fall"},
                        ],
                        value="", clearable=False,
                    ),
                ], width=4),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    html.Label("Traffic volume: show top N routes"),
                    dcc.Slider(
                        id="network-topn-slider",
                        min=50, max=2000, step=None,
                        marks={v: str(v) for v in [50, 100, 200, 500, 1000, 2000]},
                        value=200,
                    ),
                ], width=8),
                dbc.Col(
                    dbc.Button("Reset Airport Filter", id="network-reset-btn", color="secondary", outline=True, className="mt-4"),
                    width=4
                ),
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(dbc.Card([html.H5("Airports Shown"), html.H2(id="network-kpi-airports")],
                                  color="primary", inverse=True, body=True), width=3),
                dbc.Col(dbc.Card([html.H5("Routes Shown"), html.H2(id="network-kpi-routes")],
                                  color="info", inverse=True, body=True), width=3),
                dbc.Col(dbc.Card([html.H5("Top Hub (by PageRank)"), html.H2(id="network-kpi-hub")],
                                  color="success", inverse=True, body=True), width=3),
                dbc.Col(dbc.Card([html.H5("Busiest Route"), html.H2(id="network-kpi-busiest")],
                                  color="warning", inverse=True, body=True), width=3),
            ], className="mb-3"),

            html.Div(id="network-selection-status-div", className="mb-2"),

            dbc.Card(dbc.CardBody(
                dcc.Graph(id="network-map-graph", style={"height": "70vh"})
            )),
        ]
    )


def register_callbacks(app_ignored):
    """Placeholder for legacy multi-page wiring (callback is registered globally via @callback)."""
    pass


@callback(
    Output("network-selected-airport-store", "data", allow_duplicate=True),
    Input("network-reset-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_selected_airport(n_clicks):
    return None


@callback(
    Output("network-selected-airport-store", "data"),
    Input("network-map-graph", "clickData"),
    Input("network-airport-dropdown", "value"),
    State("network-selected-airport-store", "data"),
)
def update_selected_airport(clickData, dropdown_value, current_selected):
    triggered = dash.ctx.triggered_id
    if triggered == "network-airport-dropdown":
        return dropdown_value or None
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


@callback(
    [
        Output("network-kpi-airports", "children"),
        Output("network-kpi-routes", "children"),
        Output("network-kpi-hub", "children"),
        Output("network-kpi-busiest", "children"),
        Output("network-selection-status-div", "children"),
        Output("network-map-graph", "figure"),
    ],
    [
        Input("network-airline-dropdown", "value"),
        Input("network-season-dropdown", "value"),
        Input("network-topn-slider", "value"),
        Input("network-selected-airport-store", "data"),
    ]
)
def update_network(airline, season, top_n, selected_airport):
    df_edges, df_nodes = get_network_data(airline=airline, season=season, airport=selected_airport)

    if selected_airport:
        status_text = html.Div([
            html.Span("Viewing routes from: ", style={"color": "#64748b"}),
            html.Span(selected_airport, style={"color": "#f59e0b", "fontWeight": "700"}),
        ])
    else:
        status_text = html.Span("Viewing National Network Overview", style={"color": "#10b981", "fontWeight": "600"})

    if df_edges.empty or df_nodes.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(template="plotly_dark", mapbox_style="carto-darkmatter",
                                 mapbox=dict(center={"lat": 37.09, "lon": -95.71}, zoom=3))
        return "0", "0", "N/A", "N/A", status_text, empty_fig

    top_edges = df_edges.sort_values("weight", ascending=False).head(int(top_n))
    node_lookup = df_nodes.set_index("faa")
    top_edges = top_edges[top_edges["Origin"].isin(node_lookup.index) & top_edges["Dest"].isin(node_lookup.index)]

    # Bucket routes into traffic tiers so line width/opacity reflects volume without one trace per edge
    fig = go.Figure()
    if not top_edges.empty:
        tiers = pd.qcut(top_edges["weight"], q=min(3, top_edges["weight"].nunique()), duplicates="drop")
        tier_styles = [
            {"width": 1, "color": "rgba(100,150,255,0.25)"},
            {"width": 2, "color": "rgba(100,200,255,0.5)"},
            {"width": 3, "color": "rgba(255,200,80,0.8)"},
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
            marker=dict(size=marker_size, color=shown_nodes["betweenness"], colorscale="Plasma", showscale=True,
                        colorbar=dict(title="Betweenness")),
            customdata=shown_nodes.index,
            text=[f"{faa} - {name}<br>Degree: {d:.3f}<br>PageRank: {pr:.4f}"
                  for faa, name, d, pr in zip(shown_nodes.index, shown_nodes["name"],
                                               shown_nodes["degree"], shown_nodes["pagerank"])],
            hoverinfo="text",
            showlegend=False,
        ))

    fig.update_layout(
        template="plotly_dark",
        mapbox_style="carto-darkmatter",
        mapbox=dict(center={"lat": 37.09, "lon": -95.71}, zoom=3.2),
        margin=dict(l=0, r=0, t=30, b=0),
        title="Route Network (line width = traffic tier, node size = PageRank, node color = betweenness)",
    )

    kpi_airports = f"{len(shown_nodes):,}"
    kpi_routes = f"{len(top_edges):,}"
    kpi_hub = "N/A"
    if not shown_nodes.empty:
        kpi_hub = shown_nodes.sort_values("pagerank", ascending=False).index[0]
    kpi_busiest = "N/A"
    if not top_edges.empty:
        busiest = top_edges.sort_values("weight", ascending=False).iloc[0]
        kpi_busiest = f"{busiest['Origin']} -> {busiest['Dest']}"

    return kpi_airports, kpi_routes, kpi_hub, kpi_busiest, status_text, fig


layout = get_layout()
