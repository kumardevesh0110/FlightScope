# 4.5 High-Dimensional Flight Analytics
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px

from src.app.db import get_airlines, get_pca_sample

try:
    dash.register_page(__name__, path="/high-dim-analytics", name="High-Dimensional Analytics")
except Exception:
    pass

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def get_layout():
    airlines = get_airlines()
    airline_options = [{"label": "All Airlines", "value": ""}] + [
        {"label": carrier, "value": carrier} for carrier in airlines
    ]

    return dbc.Container([
        html.H3("High-Dimensional Analytics", className="mt-4 mb-3 text-primary"),
        html.P(
            "Visualizing dimensional reduction (PCA) to identify hidden clusters in flight delays and systemic congestion.",
            className="text-muted"
        ),

        dbc.Row([
            dbc.Col([
                html.Label("Airline"),
                dcc.Dropdown(id="hd-airline-dropdown", options=airline_options, value="", clearable=False),
            ], width=4),
            dbc.Col([
                html.Label("Season"),
                dcc.Dropdown(
                    id="hd-season-dropdown",
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
            dbc.Col([
                html.Label("Month"),
                dcc.Dropdown(
                    id="hd-month-dropdown",
                    options=[{"label": "All Months", "value": ""}] + [
                        {"label": MONTHS[m], "value": m} for m in range(1, 13)
                    ],
                    value="", clearable=False,
                ),
            ], width=4),
        ], className="mb-4"),

        dbc.Card([
            dbc.CardBody([
                dcc.Graph(id="pca-scatter-plot", style={"height": "65vh"})
            ])
        ], className="shadow-sm border-0")
    ], fluid=True)


def register_callbacks(app_ignored):
    """Placeholder for legacy multi-page wiring (callback is registered globally via @callback)."""
    pass


@callback(
    Output("pca-scatter-plot", "figure"),
    [
        Input("hd-airline-dropdown", "value"),
        Input("hd-season-dropdown", "value"),
        Input("hd-month-dropdown", "value"),
    ]
)
def update_pca_scatter(airline, season, month):
    df = get_pca_sample(airline=airline, season=season, month=month, sample_size=5000)

    fig = px.scatter(
        df,
        x='PCA_1',
        y='PCA_2',
        color='Origin_Dep_Congestion',
        hover_data=['Marketing_Airline_Network', 'ArrDelay'],
        title="Flight Delay Clusters (Principal Component Analysis)",
        color_continuous_scale="Plasma",
        labels={'Origin_Dep_Congestion': 'Airport Congestion Score'},
        opacity=0.7
    )

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(240,240,240,0.5)"
    )

    return fig


layout = get_layout()
