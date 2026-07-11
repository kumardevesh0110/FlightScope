import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.pipeline.config import PROCESSED_DIR

FLIGHT_FILE = os.path.join(PROCESSED_DIR, "Flights_2022_sampled_1.8M.csv")

print("Loading Predictor Data...")

df = pd.read_csv(
    FLIGHT_FILE,
    usecols=["Operating_Airline ", "ArrDelay", "Origin", "Dest", "CRSDepTime", "Month", "DayOfWeek"],
    low_memory=False
)
df["Airline"] = df["Operating_Airline "]

# Add Scheduled Hour
df["CRSDepTime"] = df["CRSDepTime"].fillna(0).astype(int)
df["DepHour"] = (df["CRSDepTime"] // 100) % 24

# Precompute baseline averages to make prediction fast
global_avg = df["ArrDelay"].mean()

# Heuristic tables
route_avg = df.groupby(["Origin", "Dest"])["ArrDelay"].mean().to_dict()
airline_avg = df.groupby("Airline")["ArrDelay"].mean().to_dict()
hour_avg = df.groupby("DepHour")["ArrDelay"].mean().to_dict()
month_avg = df.groupby("Month")["ArrDelay"].mean().to_dict()
day_avg = df.groupby("DayOfWeek")["ArrDelay"].mean().to_dict()

airline_options = [{"label": air, "value": air} for air in sorted(df["Airline"].dropna().unique())]
origin_options = [{"label": org, "value": org} for org in sorted(df["Origin"].dropna().unique())]
dest_options = [{"label": dest, "value": dest} for dest in sorted(df["Dest"].dropna().unique())]

STYLES = {
    "card": {"backgroundColor": "#1e293b", "border": "none", "borderRadius": "12px", "boxShadow": "0 4px 6px -1px rgba(0,0,0,0.1)", "marginBottom": "20px"},
    "card_header": {"backgroundColor": "#0f172a", "borderBottom": "1px solid #334155", "padding": "15px 20px", "borderTopLeftRadius": "12px", "borderTopRightRadius": "12px"},
    "card_header_text": {"color": "#f8fafc", "margin": "0", "fontWeight": "600", "fontSize": "1.1rem"},
    "label": {"color": "#94a3b8", "fontWeight": "600", "fontSize": "0.9rem", "marginBottom": "8px"},
}

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("Flight Delay Predictor", style={"color": "#f8fafc", "fontWeight": "700"}), width=12, className="mb-4")
    ]),
    dbc.Row([
        # Inputs Side
        dbc.Col([
            html.Div(style=STYLES["card"], children=[
                html.Div(style=STYLES["card_header"], children=[
                    html.H5("Flight Parameters", style=STYLES["card_header_text"])
                ]),
                html.Div(style={"padding": "20px"}, children=[
                    html.Label("Origin Airport", style=STYLES["label"]),
                    dcc.Dropdown(id="pred-origin", options=origin_options, value="JFK", className="dark-dropdown mb-3"),
                    
                    html.Label("Destination Airport", style=STYLES["label"]),
                    dcc.Dropdown(id="pred-dest", options=dest_options, value="LAX", className="dark-dropdown mb-3"),
                    
                    html.Label("Airline", style=STYLES["label"]),
                    dcc.Dropdown(id="pred-airline", options=airline_options, value=airline_options[0]["value"], className="dark-dropdown mb-3"),
                    
                    html.Label("Scheduled Departure Hour", style=STYLES["label"]),
                    dcc.Slider(id="pred-hour", min=0, max=23, step=1, value=12, marks={i: str(i) for i in range(0, 24, 4)}, className="dark-slider"),
                    
                    html.Br(),
                    html.Label("Month", style=STYLES["label"]),
                    dcc.Slider(id="pred-month", min=1, max=12, step=1, value=6, marks={i: str(i) for i in range(1, 13, 2)}, className="dark-slider"),
                    
                    html.Br(),
                    html.Label("Day of Week", style=STYLES["label"]),
                    dcc.Dropdown(id="pred-day", options=[
                        {"label": "Monday", "value": 1},
                        {"label": "Tuesday", "value": 2},
                        {"label": "Wednesday", "value": 3},
                        {"label": "Thursday", "value": 4},
                        {"label": "Friday", "value": 5},
                        {"label": "Saturday", "value": 6},
                        {"label": "Sunday", "value": 7},
                    ], value=5, className="dark-dropdown mb-3"),
                ])
            ])
        ], md=4),
        
        # Results Side
        dbc.Col([
            html.Div(style=STYLES["card"], children=[
                html.Div(style=STYLES["card_header"], children=[
                    html.H5("Predicted Arrival Delay", style=STYLES["card_header_text"])
                ]),
                html.Div(style={"padding": "20px"}, children=[
                    dcc.Graph(id="pred-gauge", style={"height": "400px"}),
                    html.Div(id="pred-explanation", style={"color": "#cbd5e1", "marginTop": "20px", "fontSize": "1.1rem"})
                ])
            ])
        ], md=8)
    ])
], fluid=True, className="py-4")

def register_callbacks(app):
    @app.callback(
        [Output("pred-gauge", "figure"),
         Output("pred-explanation", "children")],
        [Input("pred-origin", "value"),
         Input("pred-dest", "value"),
         Input("pred-airline", "value"),
         Input("pred-hour", "value"),
         Input("pred-month", "value"),
         Input("pred-day", "value")]
    )
    def predict_delay(origin, dest, airline, hour, month, day):
        # Base prediction on global average
        pred = global_avg
        
        # Apply heuristics (difference from global avg)
        route = (origin, dest)
        if route in route_avg:
            route_impact = route_avg[route] - global_avg
            pred += route_impact
            route_text = f"Route ({origin}->{dest}) impact: {route_impact:+.1f}m. "
        else:
            route_text = f"Route ({origin}->{dest}) not enough data. "
            
        airline_impact = airline_avg.get(airline, global_avg) - global_avg
        pred += airline_impact
        
        hour_impact = hour_avg.get(hour, global_avg) - global_avg
        pred += hour_impact
        
        month_impact = month_avg.get(month, global_avg) - global_avg
        pred += month_impact
        
        day_impact = day_avg.get(day, global_avg) - global_avg
        pred += day_impact
        
        # Gauge Chart
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = pred,
            title = {'text': "Estimated Delay (Minutes)", 'font': {'color': '#f8fafc', 'size': 24}},
            gauge = {
                'axis': {'range': [-30, 120], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "white"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [-30, 0], 'color': '#22c55e'},    # Green (Early)
                    {'range': [0, 15], 'color': '#facc15'},     # Yellow (Minor Delay)
                    {'range': [15, 45], 'color': '#f97316'},    # Orange (Moderate Delay)
                    {'range': [45, 120], 'color': '#ef4444'}],  # Red (Severe Delay)
                'threshold': {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 0.75,
                    'value': pred}
            },
            number = {'font': {'color': '#f8fafc'}}
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            margin=dict(t=50, l=20, r=20, b=20)
        )
        
        # Explanation Text
        exp = html.Div([
            html.Strong("Heuristic Breakdown:"), html.Br(),
            f"Base Avg: {global_avg:.1f}m", html.Br(),
            route_text, html.Br(),
            f"Airline ({airline}) impact: {airline_impact:+.1f}m", html.Br(),
            f"Time ({hour}:00) impact: {hour_impact:+.1f}m", html.Br(),
            f"Month ({month}) impact: {month_impact:+.1f}m", html.Br(),
            f"Day ({day}) impact: {day_impact:+.1f}m"
        ])
        
        return fig, exp
