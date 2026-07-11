from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import duckdb
import pandas as pd
from functools import lru_cache
from src.pipeline.config import DB_PATH

@lru_cache(maxsize=32)
def get_umap_data(month=None, origin_state=None, dest_state=None, origin_airport=None, dest_airport=None):
    """Fetches a sample of flights, filtered by month, state, and airport."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    
    # We select rowid as flight_id so we can track specific points across callbacks
    # We select an analytical row_number window function to use as a flight_id since rowid isn't stable across parquet reads
    base_query = """
        SELECT row_number() OVER () AS flight_id, UMAP_1, UMAP_2, UMAP_3, Origin_Dep_Congestion, 
               Operating_Airline, ArrDelay, Month, TaxiOut, DepDelay, Distance, AirTime
        FROM read_parquet('data/processed/processed_flights_with_umap.parquet')
        WHERE UMAP_1 IS NOT NULL AND UMAP_2 IS NOT NULL AND UMAP_3 IS NOT NULL
    """
    
    if month:
        base_query += f" AND Month = {month}"
    if origin_state:
        base_query += f" AND OriginState = '{origin_state}'"
    if dest_state:
        base_query += f" AND DestState = '{dest_state}'"
    if origin_airport:
        base_query += f" AND Origin = '{origin_airport}'"
    if dest_airport:
        base_query += f" AND Dest = '{dest_airport}'"
        
    final_query = f"SELECT * FROM ({base_query}) USING SAMPLE 5000"
    
    df = conn.execute(final_query).df()
    conn.close()
    return df

def create_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("High-Dimensional Analytics", 
                         style={"color": "#ffffff", "fontWeight": "700", "fontSize": "2.2rem", "letterSpacing": "-0.025em"}, className="mb-1"),
                html.P("Exploring complex delay topologies using UMAP and Parallel Coordinates.", 
                        style={"color": "#64748b", "fontSize": "1rem"}, className="mb-3"),
            ], width=12)
        ], className="mb-3 mt-1"),
        
        # NEW: KPI Cards Row
        dbc.Row([
            dbc.Col(dbc.Card([dbc.CardBody([
                html.H6("Flights in View", className="text-muted mb-1"),
                html.H3(id="hd-kpi-flights", className="text-primary mb-0")
            ])], className="shadow-sm border-0", style={"backgroundColor": "#151722"}), width=3),
            dbc.Col(dbc.Card([dbc.CardBody([
                html.H6("Avg Arrival Delay", className="text-muted mb-1"),
                html.H3(id="hd-kpi-arr-delay", className="text-warning mb-0")
            ])], className="shadow-sm border-0", style={"backgroundColor": "#151722"}), width=3),
            dbc.Col(dbc.Card([dbc.CardBody([
                html.H6("Avg Taxi-Out", className="text-muted mb-1"),
                html.H3(id="hd-kpi-taxi-out", className="text-info mb-0")
            ])], className="shadow-sm border-0", style={"backgroundColor": "#151722"}), width=3),
            dbc.Col(dbc.Card([dbc.CardBody([
                html.H6("Max Delay in Cluster", className="text-muted mb-1"),
                html.H3(id="hd-kpi-max-delay", className="text-danger mb-0")
            ])], className="shadow-sm border-0", style={"backgroundColor": "#151722"}), width=3),
        ], className="mb-4"),
        
        dbc.Row([
            # LEFT COLUMN: Vertical Slider
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Month", className="mb-4 text-center", style={"color": "#ffffff"}),
                        html.Div(
                            dcc.Slider(
                                id='month-slider',
                                min=1, max=12, step=1,
                                marks={
                                    i: {
                                        'label': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i-1],
                                        'style': {'color': '#94a3b8', 'fontSize': '14px', 'paddingLeft': '15px'}
                                    } for i in range(1, 13)
                                },
                                value=1, 
                                included=False,
                                vertical=True
                            ),
                            style={"height": "50vh", "paddingLeft": "40%"} 
                        )
                    ])
                ], className="shadow-sm border-0 h-100", style={"backgroundColor": "#151722"})
            ], width=2),
            
            # MIDDLE COLUMN: UMAP Graph
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H5("Delay Clusters (3D UMAP)", className="mb-0", style={"color": "#ffffff"}),
                            # NEW: Color By Dropdown for Interactive recoloring
                            dcc.Dropdown(
                                id="color-by-dropdown",
                                options=[
                                    {"label": "Airport Congestion", "value": "Origin_Dep_Congestion"},
                                    {"label": "Arrival Delay", "value": "ArrDelay"},
                                    {"label": "Distance", "value": "Distance"},
                                    {"label": "Operating Airline", "value": "Operating_Airline"}
                                ],
                                value="Origin_Dep_Congestion",
                                clearable=False,
                                style={"width": "200px", "color": "#111111"}
                            )
                        ], className="d-flex justify-content-between align-items-center mb-3"),
                        dcc.Graph(id="umap-scatter-plot", style={"height": "55vh"})
                    ])
                ], className="shadow-sm border-0 h-100", style={"backgroundColor": "#151722"})
            ], width=5),
            
            # RIGHT COLUMN: Parallel Coordinates Graph
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Multivariate Delay Flow", className="mb-3", style={"color": "#ffffff"}),
                        dcc.Graph(id="parallel-coords-plot", style={"height": "55vh"})
                    ])
                ], className="shadow-sm border-0 h-100", style={"backgroundColor": "#151722"})
            ], width=5)
            
        ], className="mb-4 align-items-stretch") 
        
    ], fluid=True, id="aditi-view-container", style={"backgroundColor": "#0c0d12", "minHeight": "100vh", "padding": "20px"})

layout = create_layout()

@callback(
    [
        Output("umap-scatter-plot", "figure"),
        Output("parallel-coords-plot", "figure"),
        Output("hd-kpi-flights", "children"),
        Output("hd-kpi-arr-delay", "children"),
        Output("hd-kpi-taxi-out", "children"),
        Output("hd-kpi-max-delay", "children")
    ],
    [
        Input("month-slider", "value"),
        Input("global-route-store", "data"),
        Input("color-by-dropdown", "value"),
        Input("umap-scatter-plot", "clickData")
    ]
)
def update_graphs(selected_month, route_data, color_by, clickData):
    try:
        route_data = route_data or {}
        origin_state = route_data.get("origin_state", "")
        dest_state = route_data.get("dest_state", "")
        origin_airport = route_data.get("origin_airport", "")
        dest_airport = route_data.get("dest_airport", "")
        
        # We use .copy() so that modifying sizes/colors doesn't permanently modify the cached dataframe
        df = get_umap_data(selected_month, origin_state, dest_state, origin_airport, dest_airport).copy()
        
        if df.empty:
            empty_fig = px.scatter_3d(title="No Data Available")
            empty_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
            return empty_fig, empty_fig, "0", "0m", "0m", "0m"

        # Compute KPIs
        kpi_flights = f"{len(df):,}"
        kpi_arr_delay = f"{df['ArrDelay'].mean():.1f}m"
        kpi_taxi = f"{df['TaxiOut'].mean():.1f}m"
        kpi_max = f"{df['ArrDelay'].max():.0f}m"

        # Cross-Filtering logic
        selected_flight_id = None
        if clickData and "points" in clickData and len(clickData["points"]) > 0:
            point = clickData["points"][0]
            if "customdata" in point:
                selected_flight_id = point["customdata"][0]

        # Map sizes directly in the dataframe to avoid multi-trace order bugs
        df['marker_size'] = 4
        if selected_flight_id is not None:
            df.loc[df['flight_id'] == selected_flight_id, 'marker_size'] = 15

        # 1. Update UMAP Figure
        umap_fig = px.scatter_3d(
            df, x='UMAP_1', y='UMAP_2', z='UMAP_3',
            color=color_by,
            size='marker_size',
            size_max=15,
            hover_data=['Operating_Airline', 'ArrDelay'],
            custom_data=['flight_id'], 
            color_continuous_scale="YlOrRd",
            opacity=0.95,
            labels={'Origin_Dep_Congestion': 'Congestion'},
            template="plotly_dark"
        )
            
        umap_fig.update_layout(
            margin=dict(l=0, r=0, t=20, b=0), 
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            scene=dict(
                xaxis=dict(title="Dim 1", gridcolor="#475569", backgroundcolor="rgba(0,0,0,0)"),
                yaxis=dict(title="Dim 2", gridcolor="#475569", backgroundcolor="rgba(0,0,0,0)"),
                zaxis=dict(title="Dim 3", gridcolor="#475569", backgroundcolor="rgba(0,0,0,0)")
            ),
            showlegend=(color_by != "Operating_Airline")
        )
        
        # 2. Update Parallel Coordinates Figure
        # If a point was clicked, filter the Parallel Coords df to just that point
        pc_df = df
        if selected_flight_id is not None:
            pc_df = df[df['flight_id'] == selected_flight_id]
            
        # Parallel coordinates requires numerical data for colors
        pc_color = color_by if color_by != "Operating_Airline" else "ArrDelay"
        
        pc_fig = px.parallel_coordinates(
            pc_df, 
            dimensions=['Distance', 'TaxiOut', 'DepDelay', 'AirTime', 'ArrDelay'],
            color=pc_color,
            color_continuous_scale="YlOrRd",
            labels={'Origin_Dep_Congestion': 'Congestion'},
            template="plotly_dark"
        )
        
        pc_fig.update_layout(
            margin=dict(l=40, r=40, t=40, b=20), 
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0")
        )
        
        return umap_fig, pc_fig, kpi_flights, kpi_arr_delay, kpi_taxi, kpi_max
    except Exception as e:
        import traceback
        with open("C:/Users/Chait/FlightScope/callback_error.log", "w") as f:
            f.write(traceback.format_exc())
        raise e