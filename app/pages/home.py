from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeSwitchAIO

dash.register_page(__name__, path="/")

header = html.Div(
    [
        html.H1("Home Page", style={"textAlign": "center", "color": "#2c3e50"}),
        html.Hr(),
    ],
    style={"marginBottom": "30px"},
)

content = html.Div(
    [
        html.H2("Dashboard Thing in Progress"),
        html.P("Do things and stuff and other things."),
        html.Ul(
            [
                html.Li(dcc.Link("This is a link to graphs", href="/databoard/graphs")),
                html.Li(dcc.Link("And another to tables", href="/databoard/tables")),
            ]
        ),
    ],
    style={"maxWidth": "800px", "margin": "0 auto", "padding": "20px"},
)

layout = html.Div([header, content])
