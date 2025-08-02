from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
import datetime

import os
os.getcwd()

dat = pd.read_csv('iris.csv')

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

app = Dash()

# app.layout = html.Div([
#     html.H1(children='Flat Dash App', style={'textAlign':'center'}),
#     html.H2(children='Histogram', style={'textAlign':'center'}),
#     dcc.Graph(id='test', figure=hist_graph),
#     html.H2(children='Bar', style={'textAlign':'center'}),
#     dcc.Graph(id='test2', figure=bar_graph, style={'width':'50%', 'display':'flex', 'justify-content':'center'}),
# ])
app.layout = html.Div([
    html.H1(children='Flat Dash App', style={'textAlign': 'center'}),
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
    )
])
# Id doesn't matter if we aren't calling back apparently
# figure specifies the graph


if __name__ == '__main__':
    app.run(debug=True)
