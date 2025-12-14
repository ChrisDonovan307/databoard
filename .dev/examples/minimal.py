from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd

import os
os.getcwd()

dat = pd.read_csv('iris.csv')

app = Dash()

app.layout = [
    html.H1(children='Minimal Dash App', style={'textAlign':'center'}),
    dcc.Dropdown(
        dat.Species.unique(), 
        value='setosa',
        # placeholder='Select Species',
        id='dropdown-selection'
    ),
    dcc.Graph(id='graph-content')
]

@callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value')
)

# Histogram of petal width of given species
def update_graph(value):
    df = dat[dat.Species == value]['Petal.Width']
    df.info()
    graph = px.histogram(
        df,
        x='Petal.Width',
    )
    graph.update_layout(
        xaxis_title="Petal Width", 
        yaxis_title="Count",
    )
    return(graph)

if __name__ == '__main__':
    app.run(debug=True)


# dat.info()
# df = dat[dat.Species == 'virginica']['Petal.Width']
# df.info()
# graph = px.histogram(
#     df,
#     x='Petal.Width',
#     nbins=20
# )
# graph.show()


# df = dat.groupby('Species')['Petal.Width'].mean().reset_index()
# df

# out = dat[dat.Species=='virginica']