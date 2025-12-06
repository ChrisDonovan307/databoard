from dash import html, dcc, callback, Output, Input
import dash
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeSwitchAIO

import json
import plotly.express as px
import pandas as pd

dash.register_page(__name__, path='/map')

df = pd.read_csv('data/installations/installations.csv')
df['launch_year'] = df['launch_year'].astype(int)
df['years_since_launch'] = 2025 - df['launch_year']

continents = list(df.continent.unique())
continents.insert(0, 'All') # insert at first position
print(continents)

content = html.Div(
    [
        html.H2('Testing Map'),
        dcc.Graph(
            id='map', # matches callback output[0]
            # figure=fig, # matches callback output[1]
            style={
                'height': '60vh',
            }
        ),
        dcc.Dropdown(
            id = 'select_continent',
            options=continents,
                # {'label': 'THIS IS A', 'value': 'a'},
            value="All", # default
            placeholder="Select a continent",
        )
    ],
    style={
        'maxWidth': '1200px', 
        'margin': '0 auto',
        'padding': '20px',
    }
)

@callback(
    Output('map', 'figure'), # figure matches nothing - convention
    Input('select_continent', 'value') # Also have to use value for some reason - convention
)
def update_map(value):
    if value == 'All' or value is None:
        dff = df
    else:
        dff = df[df.continent == value]

    fig = px.scatter_map(
        dff,
        lat="lat",
        lon="lng",
        hover_data=[
            "name", 
            "hostname",
            "launch_year",
        ],
        size='years_since_launch',
        size_max=25,
        zoom=2,
    )

    fig.update_layout(
        map_style="carto-positron",
        margin={"r":0,"t":0,"l":0,"b":0},
    )

    fig.update_traces(
        hovertemplate=
            "<b>%{customdata[0]}</b><br><br>" +
            "<b>Hostname:</b> %{customdata[1]}<br>" +
            "<b>Launch Year:</b> %{customdata[2]}<br>" +
            "<extra></extra>",
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,
            font_color="black",
            font_family="Arial"
        ),
        marker=dict(
            opacity=0.8,
        )
    )
    return fig

layout = html.Div([
    content
])
