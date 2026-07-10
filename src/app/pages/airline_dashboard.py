import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc


# =====================================================
# DATA PATH
# =====================================================

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.pipeline.config import PROCESSED_DIR

FLIGHT_FILE = os.path.join(PROCESSED_DIR, "Flights_2022_sampled_1.8M.csv")

AIRPORT_FILE = os.path.join(PROCESSED_DIR, "airports.csv")

# =====================================================
# LOAD DATA
# =====================================================

print("Loading Airline Dashboard Data...")


df = pd.read_csv(
    FLIGHT_FILE,
    usecols=[
        "Month",
        "Operating_Airline ",
        "Marketing_Airline_Network",
        "ArrDelay",
        "Cancelled",
        "Flights",
        "CarrierDelay",
        "WeatherDelay",
        "NASDelay",
        "SecurityDelay",
        "LateAircraftDelay",
        "Origin",
        "Dest",
        "OriginState",
        "DestState",
        "AirTime"
    ],
    low_memory=False
)

airports = pd.read_csv(
    AIRPORT_FILE
)


# =====================================================
# CLEAN DATA
# =====================================================

df["Airline"] = (
    df["Operating_Airline "]
    .fillna(
        df["Marketing_Airline_Network"]
    )
)


df["ArrDelay"] = df["ArrDelay"].fillna(0)



df["Delayed"] = (
    df["ArrDelay"] > 15
).astype(int)



airlines = sorted(
    df["Airline"]
    .dropna()
    .unique()
)



# =====================================================
# INITIAL GRAPHS
# =====================================================


ranking_data = (

    df.groupby("Airline")
    .size()
    .reset_index(
        name="Flights"
    )
    .sort_values(
        "Flights",
        ascending=False
    )

)




ranking_fig = px.bar(

    ranking_data.head(15),

    x="Airline",

    y="Flights",

    color="Flights",

    color_continuous_scale="Viridis",

    title="Top Airlines by Flight Volume"

)


ranking_fig.update_layout(
    template="plotly_dark",
    margin=dict(l=20, r=20, t=30, b=20),
    height = 200
)



# Delay cause chart and scatter removed for layout restructure




# =====================================================
# GLOBAL MAX FOR RADAR
# =====================================================

grouped = df.groupby("Airline")
MAX_FLIGHTS = grouped.size().max()
MAX_DELAY = grouped["ArrDelay"].mean().max()
MAX_CANCEL = grouped["Cancelled"].mean().max() * 100

# =====================================================
# DELAY HEATMAP
# =====================================================


heatmap_data = pd.DataFrame(

    {

    "Cause":[
        "Carrier",
        "Weather",
        "NAS",
        "Security",
        "Late Aircraft"
    ],


    "Delay Minutes":[

        df["CarrierDelay"].sum(),

        df["WeatherDelay"].sum(),

        df["NASDelay"].sum(),

        df["SecurityDelay"].sum(),

        df["LateAircraftDelay"].sum()

    ]

    }

)


box_plot_data = df


# Box Plot showing distribution of Arrival Delays per Airline
box_fig = px.box(
    box_plot_data,
    x="Airline",
    y="ArrDelay",
    color="Airline",
    title="Distribution of Arrival Delays by Airline"
)

box_fig.update_layout(
    template="plotly_dark",
    height=250,
    margin=dict(l=20, r=20, t=30, b=20),
    showlegend=False # Set to False to keep the UI clean
)






# =====================================================
# AIRPORT MAP
# =====================================================


route_airports = (

    df["Origin"]

    .value_counts()

    .head(30)

    .reset_index()

)



route_airports.columns=[

    "faa",

    "Flights"

]



route_map_data = route_airports.merge(

    airports,

    on="faa",

    how="left"

)



map_fig = px.scatter_mapbox(

    route_map_data,

    lat="lat",

    lon="lon",

    size="Flights",

    hover_name="name",

    color="Flights",

    color_continuous_scale="Turbo",

    zoom=3,

    height=600,

    title="Top Airports by Flight Activity"

)



map_fig.update_layout(

    mapbox_style="carto-darkmatter",

    template="plotly_dark"

)





# =====================================================
# LAYOUT 
# =====================================================

layout = html.Div(

    style={
        "backgroundColor": "#0B132B",
        "minHeight": "100vh",
        "padding": "20px"
    },

    children=[

        html.H1(
            "✈ Airline Performance Dashboard",
            style={
                "textAlign": "center",
                "color": "white",
                "marginBottom": "30px"
            }
        ),


 # ================= DROPDOWN =================
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(
                        id="airline_dropdown",
                        options=[{"label": "All Airlines", "value": "ALL"}] + [
                            {"label": x, "value": x} for x in airlines
                        ],
                        value="ALL",
                        clearable=False,
                        placeholder="Select an Airline...",
                        style={
                            "color": "#000000",
                            "backgroundColor": "#FFFFFF"
                        }
                    ),
                    width=4
                )
            ],
            className="mb-4"
        ),

        # ================= KPI CARDS =================

        dbc.Row(
            [

                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Flights", style={"fontSize": "14px", "fontWeight": "600", "color": "#0ea5e9"}),
                            html.H2(id="kpi_flights", style={"color": "#0ea5e9", "fontWeight": "bold"})
                        ],
                        style={"backgroundColor": "#1a1d2b", "border": "1px solid #0ea5e9", "borderRadius": "8px"},
                        body=True
                    ),
                    width=3
                ),



                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Average Delay", style={"fontSize": "14px", "fontWeight": "600", "color": "#ef4444"}),
                            html.H2(id="kpi_delay", style={"color": "#ef4444", "fontWeight": "bold"})
                        ],
                        style={"backgroundColor": "#1a1d2b", "border": "1px solid #ef4444", "borderRadius": "8px"},
                        body=True
                    ),
                    width=3
                ),



                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("On Time", style={"fontSize": "14px", "fontWeight": "600", "color": "#22c55e"}),
                            html.H2(id="kpi_ontime", style={"color": "#22c55e", "fontWeight": "bold"})
                        ],
                        style={"backgroundColor": "#1a1d2b", "border": "1px solid #22c55e", "borderRadius": "8px"},
                        body=True
                    ),
                    width=3
                ),



                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Cancelled", style={"fontSize": "14px", "fontWeight": "600", "color": "#f97316"}),
                            html.H2(id="kpi_cancel", style={"color": "#f97316", "fontWeight": "bold"})
                        ],
                        style={"backgroundColor": "#1a1d2b", "border": "1px solid #f97316", "borderRadius": "8px"},
                        body=True
                    ),
                    width=3
                ),

            ],

            className="mb-4"

        ),




        # ================= BAR + MONTHLY + HEATMAP =================


        dbc.Row(

            [

                dbc.Col(

                    dbc.Card(
                        dbc.CardBody(

                            dcc.Graph(
                                figure=ranking_fig,

                                config={
                                    "responsive": True,
                                    "displayModeBar": False
                                },
                                

                                style={
                                    "height":"300px"
                                }
                            )

                        )
                    ),

                    width=4

                ),

                dbc.Col(

                    dbc.Card(

                        dbc.CardBody(

                            dcc.Graph(

                                id="radar_fig",

                                config={
                                    "responsive":True,
                                    "displayModeBar":False
                                },

                                style={
                                    "height":"300px"
                                }

                            )


                        )

                    ),

                    width=4

                ),



                dbc.Col(

                    dbc.Card(

                        dbc.CardBody(

                            dcc.Graph(

                                figure=box_fig,

                                config={
                                    "responsive":True,
                                    "displayModeBar":False
                                },

                                style={
                                    "height":"300px"
                                }

                            )

                        )

                    ),

                    width=4

                )

            ],

            className="mb-4"

        ),




        # ================= MAP + PIE =================


        dbc.Row(

            [

                dbc.Col(

                    dbc.Card(

                        dbc.CardBody(

                            dcc.Graph(

                                figure=map_fig,

                                config={
                                    "responsive":True,
                                    "displayModeBar":False
                                },

                                style={
                                    "height":"300px"
                                }

                            )

                        )

                    ),

                    width=8

                ),

                dbc.Col(

                    dbc.Card(
                        dbc.CardBody(

                            dcc.Graph(
                                id="duration_fig",

                                config={
                                    "responsive": True,
                                    "displayModeBar": False
                                },

                                style={
                                    "height":"300px"
                                }
                            )

                        )
                    ),

                    width=4

                ),

            ],

            className="mb-4"

        ),







        # ================= SCATTER REMOVED =================

    ]

)




# =====================================================
# CALLBACKS
# =====================================================


def register_callbacks(app):


    @app.callback(

        [

        Output(
            "kpi_flights",
            "children"
        ),

        Output(
            "kpi_delay",
            "children"
        ),

        Output(
            "kpi_ontime",
            "children"
        ),

        Output(
            "kpi_cancel",
            "children"
        ),

        Output(
            "radar_fig",
            "figure"
        ),

        Output(
            "duration_fig",
            "figure"
        )

        ],

        [
            Input("airline_dropdown", "value"),
            Input("global-route-store", "data")
        ]

    )


    def update_cards(selected, route_data):
        
        # Apply Global Filters
        temp = df.copy()
        if route_data:
            o_state = route_data.get("origin_state")
            d_state = route_data.get("dest_state")
            o_airport = route_data.get("origin_airport")
            d_airport = route_data.get("dest_airport")
            
            if o_state: temp = temp[temp["OriginState"] == o_state]
            if d_state: temp = temp[temp["DestState"] == d_state]
            if o_airport: temp = temp[temp["Origin"] == o_airport]
            if d_airport: temp = temp[temp["Dest"] == d_airport]

        # Compute dynamic maxes for the current route
        if len(temp) > 0:
            route_grouped = temp.groupby("Airline")
            dyn_max_flights = route_grouped.size().max()
            dyn_max_delay = route_grouped["ArrDelay"].mean().max()
            dyn_max_cancel = route_grouped["Cancelled"].mean().max() * 100
        else:
            dyn_max_flights = MAX_FLIGHTS
            dyn_max_delay = MAX_DELAY
            dyn_max_cancel = MAX_CANCEL

        if selected != "ALL":
            temp = temp[temp["Airline"] == selected]

        flights = len(temp)

        if flights == 0:
            delay = 0
            delayed_pct = 0
            cancel = 0
        else:
            delay = round(temp["ArrDelay"].mean(), 2)
            delayed_pct = round(temp["Delayed"].mean() * 100, 2)
            cancel = round(temp["Cancelled"].mean() * 100, 2)
            
        ontime_pct = round(100 - delayed_pct, 2)

        # Compute Radar Scores
        if selected == "ALL":
            f_score = 100
        else:
            f_score = (flights / dyn_max_flights) * 100 if dyn_max_flights > 0 else 0
            
        d_score = max(0, 100 - (delay / dyn_max_delay * 100)) if dyn_max_delay > 0 else 100
        o_score = ontime_pct
        c_score = max(0, 100 - (cancel / dyn_max_cancel * 100)) if dyn_max_cancel > 0 else 100

        radar_fig = go.Figure()
        radar_fig.add_trace(go.Scatterpolar(
            r=[f_score, d_score, o_score, c_score],
            theta=['Volume', 'Timeliness', 'On-Time', 'Completion'],
            fill='toself',
            name=selected,
            line_color="cyan"
        ))
        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#334155"),
                angularaxis=dict(gridcolor="#334155")
            ),
            showlegend=False,
            template="plotly_dark",
            margin=dict(l=30, r=30, t=40, b=30),
            title="Performance Radar",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        # Duration Histogram
        if not temp.empty and not temp["AirTime"].isna().all():
            duration_fig = px.histogram(
                temp, 
                x="AirTime", 
                nbins=30, 
                title=f"Flight Duration Distribution",
                color_discrete_sequence=["#eab308"]
            )
            duration_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Air Time (Mins)",
                yaxis_title="Count"
            )
        else:
            duration_fig = go.Figure()
            duration_fig.update_layout(template="plotly_dark", title="No Flight Data")

        return (

            f"{flights:,}",

            f"{delay} min",

            f"{ontime_pct}%",

            f"{cancel}%",
            
            radar_fig,
            
            duration_fig

        )