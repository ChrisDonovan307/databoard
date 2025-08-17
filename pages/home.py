from dash import Dash, html, dcc
import dash

dash.register_page(__name__, path='/home')

layout = html.Div(children=[
    html.H1(children='This is our Home page'),

    html.Div(children='''
        This is our Home page content.
    '''),

])
