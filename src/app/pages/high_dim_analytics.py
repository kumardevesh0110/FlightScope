from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import duckdb
import pandas as pd
from src.pipeline.config import DB_PATH

def get_umap_data(month=None, origin_state=None, dest_state=None):
    """Fetches a sample of flights, filtered by month and state if requested."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    
    base_query = """
        SELECT UMAP_1, UMAP_2, UMAP_3, Origin_Dep_Congestion, Operating_Airline, ArrDelay, Month,
               TaxiOut, DepDelay, Distance, AirTime
        FROM flights 
        WHERE UMAP_1 IS NOT NULL AND UMAP_2 IS NOT NULL AND UMAP_3 IS NOT NULL
    """
    
    # The Month Slider filter
    if month:
        base_query += f" AND Month = {month}"
        
    # The new Global State filters
    if origin_state:
        base_query += f" AND OriginState = '{origin_state}'"
    if dest_state:
        base_query += f" AND DestState = '{dest_state}'"
        
    # Updated to 5000 to perfectly match Anushka's instructions!
    base_query += " USING SAMPLE 5000" 
    
    df = conn.execute(base_query).df()
    conn.close()
    return df

# Build the layout with the Slider and Graph placeholders
def create_layout():
    return dbc.Container([
        html.H3("High-Dimensional Analytics", className="mt-4 mb-3 text-primary"),
        html.P("Exploring complex delay topologies using UMAP and Parallel Coordinates.", className="text-muted"),
        
        # Everything goes inside a single Row to sit side-by-side
        dbc.Row([
            
            # LEFT COLUMN: Vertical Slider (Width 2 out of 12)
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Month", className="mb-4 text-center", style={"color": "#ffffff"}),
                        html.Div(
                            dcc.Slider(
                                id='month-slider',
                                min=1, max=12, step=1,
                                # Injecting the CSS colors directly into the Python marks dictionary!
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
                            style={"height": "50vh", "paddingLeft": "40%"} # Centers it and gives it height
                        )
                    ])
                ], className="shadow-sm border-0 h-100", style={"backgroundColor": "#151722"})
            ], width=2),
            
            # MIDDLE COLUMN: UMAP Graph (Width 5 out of 12)
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Delay Clusters (3D UMAP)", className="mb-3", style={"color": "#ffffff"}),
                        dcc.Graph(id="umap-scatter-plot", style={"height": "55vh"})
                    ])
                ], className="shadow-sm border-0 h-100", style={"backgroundColor": "#151722"})
            ], width=5),
            
            # RIGHT COLUMN: Parallel Coordinates Graph (Width 5 out of 12)
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Multivariate Delay Flow", className="mb-3", style={"color": "#ffffff"}),
                        dcc.Graph(id="parallel-coords-plot", style={"height": "55vh"})
                    ])
                ], className="shadow-sm border-0 h-100", style={"backgroundColor": "#151722"})
            ], width=5)
            
        ], className="mb-4 align-items-stretch") # align-items-stretch makes all 3 cards equal height
        
    ], fluid=True, id="aditi-view-container", style={"backgroundColor": "#0c0d12", "minHeight": "100vh", "padding": "20px"})

layout = create_layout()

# The Callback makes the graphs react to the slider and global dropdowns dynamically
@callback(
    Output("umap-scatter-plot", "figure"),
    Output("parallel-coords-plot", "figure"),
    Input("month-slider", "value"),
    Input("global-route-store", "data") # Tapping into the global store from app.py
)
def update_graphs(selected_month, route_data):
    # Extract states from the global store, defaulting to empty strings if None
    route_data = route_data or {}
    origin_state = route_data.get("origin_state", "")
    dest_state = route_data.get("dest_state", "")
    
    # Pass the new state filters into your data fetcher
    df = get_umap_data(selected_month, origin_state, dest_state)
    
    # 1. Update UMAP Figure to 3D (High Contrast Dark Theme)
    umap_fig = px.scatter_3d(
        df, x='UMAP_1', y='UMAP_2', z='UMAP_3',
        color='Origin_Dep_Congestion',
        hover_data=['Operating_Airline', 'ArrDelay'],
        title="Flight Delay Clusters (3D UMAP Embeddings)",
        color_continuous_scale="YlOrRd", # Swapped to a bright scale
        opacity=0.95, # Increased opacity so dots aren't washed out
        labels={'Origin_Dep_Congestion': 'Airport Congestion'},
        template="plotly_dark"
    )
    
    # Make the 3D dots slightly larger for better visibility
    umap_fig.update_traces(marker=dict(size=4))
    
    # Brighter gridlines for better spatial awareness
    umap_fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0), 
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        scene=dict(
            xaxis=dict(title="Dim 1", gridcolor="#475569", backgroundcolor="rgba(0,0,0,0)"),
            yaxis=dict(title="Dim 2", gridcolor="#475569", backgroundcolor="rgba(0,0,0,0)"),
            zaxis=dict(title="Dim 3", gridcolor="#475569", backgroundcolor="rgba(0,0,0,0)")
        )
    )
    
    # 2. Update Parallel Coordinates Figure (High Contrast Dark Theme)
    pc_fig = px.parallel_coordinates(
        df, 
        dimensions=['Distance', 'TaxiOut', 'DepDelay', 'AirTime', 'ArrDelay'],
        color='Origin_Dep_Congestion',
        color_continuous_scale="YlOrRd", # Swapped to match the 3D graph
        labels={'Origin_Dep_Congestion': 'Congestion'},
        template="plotly_dark"
    )
    
    pc_fig.update_layout(
        margin=dict(l=40, r=40, t=40, b=20), 
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0")
    )
    
    return umap_fig, pc_fig