import os
import sys
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import dash_bootstrap_components as dbc

# Ensure project root is on PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.app.pages import (
    network_explorer,
    delay_heatmap,
    airline_dashboard,
    delay_cause_sankey,
    high_dim_analytics
)
from src.app.db import get_states, get_airport_list

# Initialize Dash application with CYBORG theme and explicit assets folder
app = dash.Dash(
    __name__,
    assets_folder=os.path.join(os.path.dirname(__file__), "assets"),
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "FlightScope: US Flight Operations & Delay Analytics"

# Load options for global filters
states = get_states()
state_options = [{"label": "Any State", "value": ""}] + [
    {"label": name, "value": code} for code, name in states
]

airports_df = get_airport_list()
airport_options = [{"label": "Any Airport", "value": ""}] + [
    {"label": f"{row.faa} – {row.name}", "value": row.faa} for row in airports_df.itertuples()
]

# Main Layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    
    # Navigation Bar with Global Filters
    dbc.Navbar(
        dbc.Container(
            [
                # Left side: Brand + Sentence Filters
                html.Div(
                    [
                        dbc.NavbarBrand("✈️ FlightScope", href="/", style={"fontWeight": "bold", "fontSize": "1.7rem", "marginRight": "15px", "color": "#ffffff", "transform": "translateY(-12px)"}),
                        
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id="global-origin-dropdown", options=state_options, value="", 
                                    placeholder="Origin", className="header-dropdown",
                                    style={"width": "220px"}
                                ),
                                dcc.RadioItems(
                                    id="origin-mode",
                                    options=[{"label": "State", "value": "state"}, {"label": "Airport", "value": "airport"}],
                                    value="state",
                                    inline=True,
                                    inputStyle={"marginRight": "5px"},
                                    labelStyle={"display": "inline-block", "marginRight": "15px", "color": "#94a3b8", "fontSize": "0.75rem", "fontWeight": "bold"},
                                    style={"marginTop": "8px", "display": "flex", "justifyContent": "center"}
                                )
                            ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"}
                        ),
                        
                        html.Div(" ────> ", style={"color": "#ffffff", "fontSize": "1.5rem", "fontWeight": "bold", "margin": "0 10px", "transform": "translateY(-12px)"}),
                        
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id="global-dest-dropdown", options=state_options, value="", 
                                    placeholder="Destination", className="header-dropdown",
                                    style={"width": "220px"}
                                ),
                                dcc.RadioItems(
                                    id="dest-mode",
                                    options=[{"label": "State", "value": "state"}, {"label": "Airport", "value": "airport"}],
                                    value="state",
                                    inline=True,
                                    inputStyle={"marginRight": "5px"},
                                    labelStyle={"display": "inline-block", "marginRight": "15px", "color": "#94a3b8", "fontSize": "0.75rem", "fontWeight": "bold"},
                                    style={"marginTop": "8px", "display": "flex", "justifyContent": "center"}
                                )
                            ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"}
                        )
                    ],
                    style={"display": "flex", "alignItems": "center", "marginTop": "10px"}
                ),
                
                # Right side: Navigation Links
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Network Explorer", href="/network-explorer", active="exact")),
                        dbc.NavItem(dbc.NavLink("Delay Heatmap", href="/delay-heatmap", active="exact")),
                        dbc.NavItem(dbc.NavLink("Delay Flow Sankey", href="/delay-cause-sankey", active="exact")),
                        dbc.NavItem(dbc.NavLink("High-Dim Analytics", href="/high-dim-analytics", active="exact")),
                    ],
                    className="ms-auto", navbar=True
                )
            ],
            fluid=True
        ),
        color="#1a1d2b",
        dark=True,
        sticky="top",
        className="shadow",
        style={"borderBottom": "1px solid #242938", "padding": "10px 20px"}
    ),
    
    # Global State Store
    dcc.Store(id="global-route-store", storage_type="session", data={
        "origin_state": "",
        "dest_state": "",
        "origin_airport": "",
        "dest_airport": ""
    }),
    
    # Page Content Container
    dbc.Container(
        id="page-content",
        fluid=True,
        className="px-2 pt-4",
        style={
            "minHeight": "100vh",
            "overflowY": "auto",
            "overflowX": "hidden"
        }
    )
])

# Option update callbacks
@app.callback(
    [Output("global-origin-dropdown", "options"),
     Output("global-origin-dropdown", "value")],
    Input("origin-mode", "value")
)
def update_origin_options(mode):
    if mode == "state":
        return state_options, ""
    return airport_options, ""

@app.callback(
    [Output("global-dest-dropdown", "options"),
     Output("global-dest-dropdown", "value")],
    Input("dest-mode", "value")
)
def update_dest_options(mode):
    if mode == "state":
        return state_options, ""
    return airport_options, ""

# Global Filter Store Callback
@app.callback(
    Output("global-route-store", "data"),
    [
        Input("global-origin-dropdown", "value"),
        Input("origin-mode", "value"),
        Input("global-dest-dropdown", "value"),
        Input("dest-mode", "value"),
    ]
)
def update_global_store(orig_val, orig_mode, dest_val, dest_mode):
    return {
        "origin_state": orig_val if orig_mode == "state" and orig_val else "",
        "dest_state": dest_val if dest_mode == "state" and dest_val else "",
        "origin_airport": orig_val if orig_mode == "airport" and orig_val else "",
        "dest_airport": dest_val if dest_mode == "airport" and dest_val else ""
    }

# Page Routing Callback
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    def get_module_layout(module, name):
        if hasattr(module, "layout"):
            return module.layout
        return html.Div([
            dbc.Alert([
                html.H4(f"{name} Page Under Construction", className="alert-heading"),
                html.P("This view is currently empty. Add the visual analytics code to its file to render it.")
            ], color="warning", className="mt-4")
        ])

    if pathname == "/delay-heatmap":
        return get_module_layout(delay_heatmap, "Delay Heatmap")
    elif pathname == "/delay-cause-sankey":
        return get_module_layout(delay_cause_sankey, "Delay Cause Flow Sankey")
    elif pathname == "/high-dim-analytics":
        return get_module_layout(high_dim_analytics, "High-Dimensional Analytics")
    elif pathname == "/network-explorer":
        return get_module_layout(network_explorer, "Network Explorer")
    elif pathname in ["/", "", "/airline-dashboard"]:
        return get_module_layout(airline_dashboard, "Airline Dashboard")
    else:
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H2("404: Page Not Found", className="text-danger mt-5"),
                    html.P(f"The path '{pathname}' was not recognized.")
                ], className="text-center")
            ])
        ])

# Register callbacks from all page views dynamically
for module in [network_explorer, delay_heatmap, airline_dashboard, delay_cause_sankey, high_dim_analytics]:
    if hasattr(module, "register_callbacks"):
        module.register_callbacks(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    print(f"Starting FlightScope Dash server on http://127.0.0.1:{port} ...")
    app.run(debug=True, port=port)


