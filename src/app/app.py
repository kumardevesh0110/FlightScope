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
    high_dim_analytics,
    compare_mode,
    predictor
)

# Initialize Dash application with CYBORG theme and explicit assets folder
app = dash.Dash(
    __name__,
    assets_folder=os.path.join(os.path.dirname(__file__), "assets"),
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "FlightScope: US Flight Operations & Delay Analytics"

# Main Layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="global-route-store", data={}),

    # Navigation Bar
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Network Explorer", href="/network-explorer", active="exact")),
            dbc.NavItem(dbc.NavLink("Delay Heatmap", href="/delay-heatmap", active="exact")),
            dbc.NavItem(dbc.NavLink("Airline Dashboard", href="/airline-dashboard", active="exact")),
            dbc.NavItem(dbc.NavLink("Delay Flow Sankey", href="/delay-cause-sankey", active="exact")),
            dbc.NavItem(dbc.NavLink("High-Dim Analytics", href="/high-dim-analytics", active="exact")),
            dbc.NavItem(dbc.NavLink("Compare Mode", href="/compare-mode", active="exact")),
            dbc.NavItem(dbc.NavLink("Delay Predictor", href="/predictor", active="exact")),
        ],
        brand="✈️ FlightScope Dashboard",
        brand_href="/",
        color="dark",
        dark=True,
        sticky="top",
        className="mb-4 shadow"
    ),
    
    # Page Content Container
    dbc.Container(
        id="page-content",
        fluid=True,
        className="px-2",
        style={
            "minHeight": "100vh",
            "overflowY": "auto",
            "overflowX": "hidden"
        }
    )
])

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
    elif pathname == "/airline-dashboard":
        return get_module_layout(airline_dashboard, "Airline Dashboard")
    elif pathname == "/delay-cause-sankey":
        return get_module_layout(delay_cause_sankey, "Delay Cause Flow Sankey")
    elif pathname == "/high-dim-analytics":
        return get_module_layout(high_dim_analytics, "High-Dimensional Analytics")
    elif pathname == "/compare-mode":
        return get_module_layout(compare_mode, "Compare Mode")
    elif pathname == "/predictor":
        return get_module_layout(predictor, "Delay Predictor")
    elif pathname in ["/network-explorer", "/", ""]:
        return get_module_layout(network_explorer, "Network Explorer")
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
for module in [network_explorer, delay_heatmap, airline_dashboard, delay_cause_sankey, high_dim_analytics, compare_mode, predictor]:
    if hasattr(module, "register_callbacks"):
        module.register_callbacks(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    print(f"Starting FlightScope Dash server on http://127.0.0.1:{port} ...")
    app.run(debug=False, port=port)


