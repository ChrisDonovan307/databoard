from dash import Dash, html, dcc, callback, Output, Input
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import datetime

dash.register_page(__name__, path='/graphs')

dat = pd.read_csv('data/iris.csv')

hist_graph = px.histogram(
    dat,
    x='Petal.Width',
)

df = dat.groupby('Species')['Petal.Width'].mean().reset_index()
bar_graph = px.bar(
    df,
    x='Species',
    y='Petal.Width',
)
bar_graph.update_layout(
    xaxis_title="Species", 
    yaxis_title="Mean Petal Width"
)

# Example components
dropdown = dcc.Dropdown(options=['NYC', 'MTL', 'SF'])
slider = dcc.Slider(min=0, max=10, step=1)

# app = Dash()
# app = Dash(__name__)
# app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# app.layout = html.Div([
#     html.H1(children='Flat Dash App', style={'textAlign': 'center'}),
#     html.Span(children=[
#         f"Prepared: {datetime.datetime.now().strftime('%Y-%m-%d')}",
#         html.Br(),
#         " by ",
#         html.B("John Doe, "),
#         html.Br(),
#         html.I("Mediocre Guy")
#     ]),
#     html.H2(children='Histogram', style={'textAlign': 'center'}),
#     dcc.Graph(id='test', figure=hist_graph),
#     html.H2(children='Bar', style={'textAlign': 'center'}),
#     html.Div(
#         dcc.Graph(id='test2', figure=bar_graph, style={'width': '60%'}),
#         style={'display': 'flex','justifyContent': 'center'}
#     )
# ])

layout = dbc.Container([
    dbc.Row(html.H1(children='Bootstrap Dash App', style={'textAlign': 'center'})),
    html.Span(children=[
        f"Prepared: {datetime.datetime.now().strftime('%Y-%m-%d')}",
        html.Br(),
        " by ",
        html.B("John Doe, "),
        html.Br(),
        html.I("Mediocre Guy")
    ]),
    html.H2(children='Histogram', style={'textAlign': 'center'}),
    dcc.Graph(id='test', figure=hist_graph),
    html.H2(children='Bar', style={'textAlign': 'center'}),
    html.Div(
        dcc.Graph(id='test2', figure=bar_graph, style={'width': '60%'}),
        style={'display': 'flex','justifyContent': 'center'}
    ),

    # Test bootstrap columns
    # Still not appearing in columns like we want - they are just even
    html.H2(children='Bootstrap Rows', style={'textAlign': 'center'}),
    dbc.Row(
        [
            dbc.Col(dcc.Graph(id='test3', figure=hist_graph), width=2),
            dbc.Col(dcc.Graph(id='test4', figure=bar_graph), width=10)
        ]
        # style={'display': 'flex'}
        # Remove justify content center to get this to work
    )
])
# ], fluid=True) # not sure if this matters
# Id doesn't matter if we aren't calling back apparently
# figure specifies the graph

# if __name__ == '__main__':
#     app.run(debug=True)
