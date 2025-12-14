from dash import Dash, html, dcc, callback, Output, Input
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import datetime

dash.register_page(__name__, path="/graphs")

dat = pd.read_csv("app/data/iris.csv")

hist_graph = px.histogram(
    dat,
    x="Petal.Width",
)

df = dat.groupby("Species")["Petal.Width"].mean().reset_index()
bar_graph = px.bar(
    df,
    x="Species",
    y="Petal.Width",
)
bar_graph.update_layout(xaxis_title="Species", yaxis_title="Mean Petal Width")

# Example components
dropdown = dcc.Dropdown(options=["NYC", "MTL", "SF"])
slider = dcc.Slider(min=0, max=10, step=1)

SIDEBAR_STYLE = {
    "position": "fixed",
    "width": "16rem",
    "padding": "2rem 1rem",
    "border-right": "1px solid #dee2e6",
}

CONTENT_STYLE = {
    "flex": "1",
    "padding": "2rem 1rem",
    "margin-right": "2rem",
    "margin-left": "18rem",
    "min-height": "calc(100vh - 100px)",
}

sidebar = html.Div(
    [
        html.H2("Sidebar"),
        # dbc.Row([theme_toggle])
        html.Hr(),
        html.Ul(
            [
                html.Li("Something"),
                html.Li("Something"),
                html.Li("Something"),
            ]
        ),
    ],
    style=SIDEBAR_STYLE,
)

layout = html.Div(
    [
        html.Div(
            [
                html.H1(
                    "Iris Dataset Visualizations",
                    style={"textAlign": "center", "paddingTop": "20px"},
                ),
                html.Hr(),
            ],
            style={"marginBottom": "20px"},
        ),
        html.Div(
            [
                sidebar,
                html.Div(
                    [
                        html.H2(
                            "Petal Width Distribution", style={"textAlign": "center"}
                        ),
                        dcc.Graph(
                            id="test", figure=hist_graph, style={"height": "400px"}
                        ),
                        html.H2(
                            "Mean Petal Width by Species",
                            style={"textAlign": "center", "marginTop": "30px"},
                        ),
                        html.Div(
                            dcc.Graph(
                                id="test2",
                                figure=bar_graph,
                                style={"width": "60%", "height": "400px"},
                            ),
                            style={"display": "flex", "justifyContent": "center"},
                        ),
                    ],
                    style=CONTENT_STYLE,
                ),
            ]
        ),
    ]
)
