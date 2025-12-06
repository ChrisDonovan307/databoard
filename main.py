import os
from dash import Dash, html, dcc, page_registry
import dash
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeSwitchAIO
import pdb

PREFIX = '/databoard/'
ROOT = os.path.dirname(os.path.abspath(__file__))

app = dash.Dash(
    __name__, 
    use_pages=True,
    pages_folder=os.path.join(ROOT, "app", "pages"), # specify path to pages from root
    requests_pathname_prefix=PREFIX,
    routes_pathname_prefix=PREFIX,
    external_stylesheets=[dbc.themes.DARKLY]
)

#$ Theme
theme_toggle = ThemeSwitchAIO(
    aio_id="theme",
    themes=[dbc.themes.DARKLY, dbc.themes.FLATLY],
    icons={"left": "fa fa-sun", "right": "fa fa-moon"},
)

#$ Footer
footer = html.Div(
    [
        html.Hr(style={'margin': '0'}),
        html.P(
            '© 2025 Databoard', 
            style={
                'textAlign': 'center', 
                'fontSize': '14px', 
                'color': '#6c757d', 
                'padding': '20px 0'
            }
        )
    ], style={'width': '100%', 'marginTop': 'auto'}
)

#$ Server
server = app.server

#$ Header
header = dbc.Navbar(
    dbc.Container(
        [
            html.A(
                dbc.Row([dbc.Col(dbc.NavbarBrand("The Dashboard"))], align="center"),
                href="/databoard/",
                style={"textDecoration": "none"},
            ),
            theme_toggle,
            dbc.Row(
                [
                    dbc.NavbarToggler(id="navbar-toggler"),
                    dbc.Nav(
                        [
                            dbc.NavLink(page["name"], href="/databoard" + page["path"])
                            for page in dash.page_registry.values()
                            if page["module"] != "pages.not_found_404"
                        ]
                    ),
                ]
            ),
        ],
        fluid=True,
    ),
    dark=True,
    color="dark"
)

#$ Layout
app.layout = html.Div([
    header,
    html.Div(dash.page_container, style={'flex': '1'}),
    footer
], style={'minHeight': '100vh', 'display': 'flex', 'flexDirection': 'column'})


print([p['module'] for p in dash.page_registry.values()])

if __name__ == '__main__':
	app.run(debug=False)
