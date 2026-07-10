import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from src.app.db import get_delay_causes, get_airlines

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
    }
}

# Define Layout
layout = html.Div(style=STYLES["page_container"], children=[
    dbc.Row([
        dbc.Col([
            html.H1("Delay Propagation Flow", style=STYLES["main_title"], className="mb-1"),
            html.P("Analyze how total delayed minutes distribute into specific root causes.", style=STYLES["subtitle"], className="mb-4")
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(style=STYLES["card"], children=[
                html.Div(style=STYLES["card_header"], children=[
                    html.H5("Filters & Controls", style=STYLES["card_header_text"])
                ]),
                html.Div(style=STYLES["card_body"], children=[
                    html.Label("Marketing Airline", style=STYLES["label"]),
                    dcc.Dropdown(
                        id="sankey-airline-filter",
                        options=[{"label": "All Airlines", "value": "ALL"}] + [{"label": a, "value": a} for a in get_airlines()],
                        value="ALL",
                        clearable=False,
                        className="mb-4",
                        style={"color": "#111111"}
                    ),
                    html.Label("Season", style=STYLES["label"]),
                    dcc.Dropdown(
                        id="sankey-season-filter",
                        options=[
                            {"label": "All Seasons", "value": "ALL"},
                            {"label": "Winter (Dec-Feb)", "value": "Winter"},
                            {"label": "Spring (Mar-May)", "value": "Spring"},
                            {"label": "Summer (Jun-Aug)", "value": "Summer"},
                            {"label": "Fall (Sep-Nov)", "value": "Fall"},
                        ],
                        value="ALL",
                        clearable=False,
                        className="mb-4",
                        style={"color": "#111111"}
                    ),
                    html.Label("Month (1-12)", style=STYLES["label"]),
                    dcc.Slider(
                        id="sankey-month-filter",
                        min=0,
                        max=12,
                        step=1,
                        value=0,
                        marks={
                            0: {"label": "All", "style": {"color": "#94a3b8"}},
                            1: {"label": "Jan", "style": {"color": "#cbd5e1"}},
                            3: {"label": "Mar", "style": {"color": "#cbd5e1"}},
                            6: {"label": "Jun", "style": {"color": "#cbd5e1"}},
                            9: {"label": "Sep", "style": {"color": "#cbd5e1"}},
                            12: {"label": "Dec", "style": {"color": "#cbd5e1"}}
                        },
                        className="mb-4"
                    ),
                    html.Label("Specific Date (Overrides Season/Month)", style=STYLES["label"]),
                    html.Div([
                        dcc.DatePickerSingle(
                            id='sankey-date-filter',
                            min_date_allowed='2018-01-01',
                            max_date_allowed='2022-12-31',
                            initial_visible_month='2022-01-01',
                            placeholder='Select a Date',
                            style={"backgroundColor": "transparent"}
                        )
                    ], className="mb-4"),
                    html.Hr(style={"borderColor": "#242938"}),
                    html.Small(
                        "Hover over the nodes and flows to see the exact number of delayed minutes attributed to each root cause.", 
                        style={"color": "#64748b"}
                    )
                ])
            ], className="h-100")
        ], xs=12, md=4, lg=3, className="mb-4"),
        
        dbc.Col([
            html.Div(style=STYLES["card"], children=[
                html.Div(style=STYLES["card_header"], children=[
                    html.H5("Root Cause Flow Distribution", style=STYLES["card_header_text"])
                ]),
                html.Div(style=STYLES["card_body"], children=[
                    dcc.Loading(
                        id="loading-sankey",
                        type="circle",
                        color="#3b82f6",
                        children=dcc.Graph(id="delay-sankey-graph", style={"height": "650px"})
                    )
                ])
            ], className="h-100")
        ], xs=12, md=8, lg=9, className="mb-4")
    ], className="mb-2")
])

def format_hours(m):
    h = m / 60
    if h >= 1_000_000:
        return f"{h/1_000_000:.2f}M hrs"
    elif h >= 1_000:
        return f"{h/1_000:.1f}k hrs"
    return f"{int(h)} hrs"

def register_callbacks(app):
    @app.callback(
        Output("delay-sankey-graph", "figure"),
        [Input("sankey-airline-filter", "value"),
         Input("sankey-season-filter", "value"),
         Input("sankey-month-filter", "value"),
         Input("sankey-date-filter", "date"),
         Input("global-route-store", "data")]
    )
    def update_sankey(airline, season, month, date, route_data):
        al = None if airline == "ALL" else airline
        
        # Unpack global filters
        o_state = route_data.get("origin_state") if route_data else None
        d_state = route_data.get("dest_state") if route_data else None
        o_airport = route_data.get("origin_airport") if route_data else None
        d_airport = route_data.get("dest_airport") if route_data else None
        
        # If a specific date is selected, ignore the Season and Month filters
        if date:
            sn = None
            mn = None
        else:
            sn = None if season == "ALL" else season
            mn = None if month == 0 else month
        
        causes = get_delay_causes(
            airline=al, season=sn, month=mn, date=date,
            origin_state=o_state, dest_state=d_state,
            origin_airport=o_airport, dest_airport=d_airport
        )
        
        # Calculate totals per severity
        minor = causes.get('Minor', {})
        major = causes.get('Major', {})
        
        minor_c = minor.get("CarrierDelay", 0)
        minor_w = minor.get("WeatherDelay", 0)
        minor_n = minor.get("NASDelay", 0)
        minor_s = minor.get("SecurityDelay", 0)
        minor_l = minor.get("LateAircraftDelay", 0)
        
        major_c = major.get("CarrierDelay", 0)
        major_w = major.get("WeatherDelay", 0)
        major_n = major.get("NASDelay", 0)
        major_s = major.get("SecurityDelay", 0)
        major_l = major.get("LateAircraftDelay", 0)
        
        minor_total = minor_c + minor_w + minor_n + minor_s + minor_l
        major_total = major_c + major_w + major_n + major_s + major_l
        
        minor_controllable = minor_c + minor_l
        minor_unavoidable = minor_w + minor_n + minor_s
        
        major_controllable = major_c + major_l
        major_unavoidable = major_w + major_n + major_s
        
        controllable_total = minor_controllable + major_controllable
        unavoidable_total = minor_unavoidable + major_unavoidable
        
        c_total = minor_c + major_c
        l_total = minor_l + major_l
        w_total = minor_w + major_w
        n_total = minor_n + major_n
        s_total = minor_s + major_s
        
        if (minor_total + major_total) == 0:
            fig = go.Figure()
            fig.update_layout(
                title="No Delay Data Available",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#cbd5e1")
            )
            return fig

        labels = [
            f"Minor Delays (<45m)<br>{format_hours(minor_total)}",
            f"Major Delays (>45m)<br>{format_hours(major_total)}",
            f"Controllable<br>{format_hours(controllable_total)}",
            f"Unavoidable<br>{format_hours(unavoidable_total)}",
            f"Airline Operations (Crew, Maintenance)<br>{format_hours(c_total)}",
            f"Previous Flight Arrived Late<br>{format_hours(l_total)}",
            f"Extreme Weather<br>{format_hours(w_total)}",
            f"Air Traffic Control & Congestion<br>{format_hours(n_total)}",
            f"Security Incident<br>{format_hours(s_total)}"
        ]
        
        # Node mapping:
        # 0: Minor, 1: Major, 2: Controllable, 3: Unavoidable
        # 4: Carrier, 5: Late Aircraft, 6: Weather, 7: NAS, 8: Security
        
        source = [
            0, 0,  # Minor -> Controllable, Unavoidable
            1, 1,  # Major -> Controllable, Unavoidable
            2, 2,  # Controllable -> Carrier, Late Aircraft
            3, 3, 3  # Unavoidable -> Weather, NAS, Security
        ]
        
        target = [
            2, 3,
            2, 3,
            4, 5,
            6, 7, 8
        ]
        
        # Divide by 60 to convert the actual flow values to hours for the tooltips
        values = [
            minor_controllable / 60, minor_unavoidable / 60,
            major_controllable / 60, major_unavoidable / 60,
            c_total / 60, l_total / 60,
            w_total / 60, n_total / 60, s_total / 60
        ]
        
        # Executive Copper & Slate Palette
        node_colors = [
            "#64748B",  # 0: Minor: Slate-500
            "#334155",  # 1: Major: Slate-700
            "#0369A1",  # 2: Controllable: Slate Blue/Ocean
            "#B45309",  # 3: Unavoidable: Dark Copper
            "#0EA5E9",  # 4: Carrier: Sky Blue
            "#38BDF8",  # 5: Late Aircraft: Light Blue
            "#F59E0B",  # 6: Weather: Amber/Copper
            "#D97706",  # 7: NAS: Dark Amber
            "#FCD34D"   # 8: Security: Light Gold
        ]
        
        link_colors = [
            "rgba(3, 105, 161, 0.45)",   # Minor -> Controllable
            "rgba(180, 83, 9, 0.45)",    # Minor -> Unavoidable
            "rgba(3, 105, 161, 0.45)",   # Major -> Controllable
            "rgba(180, 83, 9, 0.45)",    # Major -> Unavoidable
            "rgba(14, 165, 233, 0.45)",  # Controllable -> Carrier
            "rgba(56, 189, 248, 0.45)",  # Controllable -> Late Aircraft
            "rgba(245, 158, 11, 0.45)",  # Unavoidable -> Weather
            "rgba(217, 119, 6, 0.45)",   # Unavoidable -> NAS
            "rgba(252, 211, 77, 0.45)"   # Unavoidable -> Security
        ]

        fig = go.Figure(data=[go.Sankey(
            valueformat=".1f",
            valuesuffix=" Hours",
            arrangement="snap",
            node=dict(
                pad=40,
                thickness=20,
                line=dict(color="rgba(0,0,0,0)", width=0),
                label=labels,
                color=node_colors,
                hoverinfo="all"
            ),
            link=dict(
                source=source,
                target=target,
                value=values,
                color=link_colors,
                hoverinfo="all"
            )
        )])
        
        fig.update_layout(
            margin=dict(l=120, r=120, t=40, b=40),
            font_size=13,
            font_family="Inter, sans-serif",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#ffffff"), 
            hoverlabel=dict(
                bgcolor="#1e293b",
                font_size=14,
                font_family="Inter, sans-serif",
                bordercolor="#334155"
            )
        )
        
        return fig
