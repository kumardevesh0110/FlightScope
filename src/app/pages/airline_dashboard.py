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


df = pd.read_parquet(
    FLIGHT_FILE.replace(".csv", ".parquet"),
    columns=[
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
        "Dest"
    ]
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
    template="plotly_dark"
)



# Delay cause chart

cause_df = pd.DataFrame(

    {

    "Cause":[
        "Carrier",
        "Weather",
        "NAS",
        "Security",
        "Late Aircraft"
    ],

    "Minutes":[

        df["CarrierDelay"].sum(),

        df["WeatherDelay"].sum(),

        df["NASDelay"].sum(),

        df["SecurityDelay"].sum(),

        df["LateAircraftDelay"].sum()

    ]

    }

)



cause_fig = px.pie(

    cause_df,

    names="Cause",

    values="Minutes",

    hole=0.5,

    color_discrete_sequence=
    px.colors.qualitative.Set3,

    title="Delay Causes"

)


cause_fig.update_layout(
    template="plotly_dark"
)


cause_fig = px.pie(

    cause_df,

    names="Cause",

    values="Minutes",

    hole=0.5,

    color_discrete_sequence=
    px.colors.qualitative.Set3,

    title="Delay Causes"

)


cause_fig.update_layout(
    template="plotly_dark"
)



# Scatter

scatter_data = (
    df.groupby("Airline")
    .agg(
        Flights=("Flights", "count"),
        AverageDelay=("ArrDelay", "mean")
    )
    .reset_index()
)

scatter_data = scatter_data.dropna()






scatter_fig = px.scatter(

    scatter_data,

    x="Flights",

    y="AverageDelay",

    size="Flights",

    color="Airline",

    title="Flight Volume vs Average Delay"

)


scatter_fig.update_layout(
    template="plotly_dark",
    height=450
)




# =====================================================
# MONTHLY TREND
# =====================================================

monthly_data = (

    df.groupby("Month")
    .agg(

        Flights=("Flights","sum"),

        Delay=("ArrDelay","mean")

    )

    .reset_index()

)



monthly_fig = px.line(

    monthly_data,

    x="Month",

    y="Flights",

    markers=True,

    color_discrete_sequence=["cyan"],

    title="Monthly Flight Volume Trend"

)


monthly_fig.update_layout(
    template="plotly_dark"
)



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



heatmap_fig = px.imshow(

    [heatmap_data["Delay Minutes"].values],

    labels={
        "x":"Delay Cause",
        "y":""
    },

    x=heatmap_data["Cause"],

    color_continuous_scale="Plasma",

    title="Delay Cause Heatmap"

)


heatmap_fig.update_layout(
    template="plotly_dark"
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
# LAYOUT (CORRECTED)
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

                        options=[
                            {
                                "label": x,
                                "value": x
                            }
                            for x in airlines
                        ],

                        value=airlines[0],
                        clearable=False
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
                            html.H5("Flights"),
                            html.H2(id="kpi_flights")
                        ],

                        color="primary",
                        inverse=True,
                        body=True
                    ),

                    width=3
                ),



                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Average Delay"),
                            html.H2(id="kpi_delay")
                        ],

                        color="danger",
                        inverse=True,
                        body=True
                    ),

                    width=3
                ),



                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("On Time"),
                            html.H2(id="kpi_ontime")
                        ],

                        color="success",
                        inverse=True,
                        body=True
                    ),

                    width=3
                ),



                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Cancelled"),
                            html.H2(id="kpi_cancel")
                        ],

                        color="warning",
                        inverse=True,
                        body=True
                    ),

                    width=3
                )

            ],

            className="mb-4"

        ),




        # ================= BAR + PIE =================


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
                                    "height":"380px"
                                }
                            )

                        )
                    ),

                    width=6

                ),



                dbc.Col(

                    dbc.Card(
                        dbc.CardBody(

                            dcc.Graph(
                                figure=cause_fig,

                                config={
                                    "responsive": True,
                                    "displayModeBar": False
                                },

                                style={
                                    "height":"380px"
                                }
                            )

                        )
                    ),

                    width=6

                )

            ],

            className="mb-4"

        ),




        # ================= SCATTER =================


        dbc.Row(

            [

                dbc.Col(

                    dbc.Card(

                        dbc.CardBody(

                            dcc.Graph(

                                figure=scatter_fig,

                                config={
                                    "responsive":True,
                                    "displayModeBar":False
                                },

                                style={
                                    "height":"420px"
                                }

                            )

                        )

                    ),

                    width=12

                )

            ],

            className="mb-4"

        ),




        # ================= MONTHLY + HEATMAP =================


        dbc.Row(

            [

                dbc.Col(

                    dbc.Card(

                        dbc.CardBody(

                            dcc.Graph(

                                figure=monthly_fig,

                                config={
                                    "responsive":True,
                                    "displayModeBar":False
                                },

                                style={
                                    "height":"380px"
                                }

                            )

                        )

                    ),

                    width=6

                ),



                dbc.Col(

                    dbc.Card(

                        dbc.CardBody(

                            dcc.Graph(

                                figure=heatmap_fig,

                                config={
                                    "responsive":True,
                                    "displayModeBar":False
                                },

                                style={
                                    "height":"380px"
                                }

                            )

                        )

                    ),

                    width=6

                )

            ],

            className="mb-4"

        ),




        # ================= MAP =================


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
                                    "height":"450px"
                                }

                            )

                        )

                    ),

                    width=12

                )

            ]

        )

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
        )

        ],


        Input(
            "airline_dropdown",
            "value"
        )

    )


    def update_cards(selected):


        temp=df[
            df["Airline"]==selected
        ]


        flights=len(temp)


        delay=round(

            temp["ArrDelay"]
            .mean(),

            2

        )


        ontime=round(

            (

            temp["Delayed"]
            .mean()

            ),

            2

        )


        cancel=round(

            temp["Cancelled"]
            .mean()*100,

            2

        )



        return (

            f"{flights:,}",

            f"{delay} min",

            f"{100-ontime}%",

            f"{cancel}%"

        )