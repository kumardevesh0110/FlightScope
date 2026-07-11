import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import os
import sys

# Ensure project root is on PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.pipeline.config import PROCESSED_DIR

FLIGHT_FILE = os.path.join(PROCESSED_DIR, "Flights_2022_sampled_1.8M.csv")

print("Loading Compare Mode Data...")

df = pd.read_csv(
    FLIGHT_FILE,
    usecols=["Operating_Airline ", "ArrDelay", "Cancelled", "Flights", "Origin", "Dest"],
    low_memory=False
)
df["Airline"] = df["Operating_Airline "]

# Pre-compute aggregates for speed
airline_options = [{"label": air, "value": air} for air in sorted(df["Airline"].dropna().unique())]
origin_options = [{"label": org, "value": org} for org in sorted(df["Origin"].dropna().unique())]

STYLES = {
    "card": {"backgroundColor": "#1e293b", "border": "none", "borderRadius": "12px", "boxShadow": "0 4px 6px -1px rgba(0,0,0,0.1)", "marginBottom": "20px"},
    "card_header": {"backgroundColor": "#0f172a", "borderBottom": "1px solid #334155", "padding": "15px 20px", "borderTopLeftRadius": "12px", "borderTopRightRadius": "12px"},
    "card_header_text": {"color": "#f8fafc", "margin": "0", "fontWeight": "600", "fontSize": "1.1rem"},
    "label": {"color": "#94a3b8", "fontWeight": "600", "fontSize": "0.9rem", "marginBottom": "8px"},
    "kpi_value": {"color": "#f8fafc", "fontWeight": "700", "margin": "0", "fontSize": "2rem"},
    "kpi_label": {"color": "#94a3b8", "fontSize": "0.9rem", "textTransform": "uppercase", "letterSpacing": "0.05em"}
}

def create_panel(panel_id):
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Select Airline", style=STYLES["label"]),
                dcc.Dropdown(
                    id=f"{panel_id}-airline-dropdown",
                    options=airline_options,
                    value=airline_options[0]["value"],
                    clearable=False,
                    className="dark-dropdown mb-3"
                )
            ], width=6),
            dbc.Col([
                html.Label("Select Origin", style=STYLES["label"]),
                dcc.Dropdown(
                    id=f"{panel_id}-origin-dropdown",
                    options=[{"label": "All Origins", "value": "ALL"}] + origin_options,
                    value="ALL",
                    clearable=False,
                    className="dark-dropdown mb-3"
                )
            ], width=6)
        ]),
        dbc.Row([
            dbc.Col([
                html.Div(style=STYLES["card"], children=[
                    html.Div(style={"padding": "20px", "textAlign": "center"}, children=[
                        html.P("Total Flights", style=STYLES["kpi_label"]),
                        html.H3(id=f"{panel_id}-total-flights", style=STYLES["kpi_value"])
                    ])
                ])
            ], width=4),
            dbc.Col([
                html.Div(style=STYLES["card"], children=[
                    html.Div(style={"padding": "20px", "textAlign": "center"}, children=[
                        html.P("Avg Delay", style=STYLES["kpi_label"]),
                        html.H3(id=f"{panel_id}-avg-delay", style={"color": "#fbbf24", "fontWeight": "700", "margin": "0", "fontSize": "2rem"})
                    ])
                ])
            ], width=4),
            dbc.Col([
                html.Div(style=STYLES["card"], children=[
                    html.Div(style={"padding": "20px", "textAlign": "center"}, children=[
                        html.P("Cancel Rate", style=STYLES["kpi_label"]),
                        html.H3(id=f"{panel_id}-cancel-rate", style={"color": "#ef4444", "fontWeight": "700", "margin": "0", "fontSize": "2rem"})
                    ])
                ])
            ], width=4)
        ]),
        html.Div(style=STYLES["card"], children=[
            html.Div(style=STYLES["card_header"], children=[
                html.H5("Delay Distribution", style=STYLES["card_header_text"])
            ]),
            html.Div(style={"padding": "15px"}, children=[
                dcc.Graph(id=f"{panel_id}-delay-histogram", style={"height": "300px"})
            ])
        ])
    ])

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("A/B Compare Mode", style={"color": "#f8fafc", "fontWeight": "700"}), width=12, className="mb-4")
    ]),
    dbc.Row([
        dbc.Col(create_panel("left"), width=6, style={"borderRight": "1px solid #334155", "paddingRight": "20px"}),
        dbc.Col(create_panel("right"), width=6, style={"paddingLeft": "20px"})
    ])
], fluid=True, className="py-4")

def register_callbacks(app):
    def generate_callback(panel_id):
        @app.callback(
            [Output(f"{panel_id}-total-flights", "children"),
             Output(f"{panel_id}-avg-delay", "children"),
             Output(f"{panel_id}-cancel-rate", "children"),
             Output(f"{panel_id}-delay-histogram", "figure")],
            [Input(f"{panel_id}-airline-dropdown", "value"),
             Input(f"{panel_id}-origin-dropdown", "value")]
        )
        def update_panel(airline, origin):
            dff = df[df["Airline"] == airline]
            if origin != "ALL":
                dff = dff[dff["Origin"] == origin]
            
            total_flights = dff["Flights"].sum() if not dff.empty else 0
            
            if total_flights > 0:
                avg_delay = dff["ArrDelay"].mean()
                cancel_rate = (dff["Cancelled"].sum() / len(dff)) * 100
                
                # Histogram
                hist_df = dff.dropna(subset=["ArrDelay"])
                if len(hist_df) > 10000:
                    hist_df = hist_df.sample(10000)
                
                fig = px.histogram(
                    hist_df, x="ArrDelay", nbins=50,
                    labels={"ArrDelay": "Arrival Delay (mins)"},
                    color_discrete_sequence=["#3b82f6"]
                )
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#cbd5e1",
                    margin=dict(t=10, l=10, r=10, b=10),
                    xaxis=dict(showgrid=True, gridcolor="#334155", range=[-30, 180]),
                    yaxis=dict(showgrid=True, gridcolor="#334155")
                )
            else:
                avg_delay = 0
                cancel_rate = 0
                fig = go.Figure()
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                
            return (
                f"{int(total_flights):,}",
                f"{avg_delay:.1f}m",
                f"{cancel_rate:.1f}%",
                fig
            )

    generate_callback("left")
    generate_callback("right")
