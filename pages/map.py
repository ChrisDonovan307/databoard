from dash import html, dcc
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

header = html.Div(
    [
        html.H1('Map', style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.Hr()
    ],
    style={'marginBottom': '30px'}
)

fig = px.scatter_map(
    df,
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

content = html.Div(
    [
        html.H2('Testing Map'),
        dcc.Graph(
            id='test', 
            figure=fig,
            style={
                'height': '60vh',
            }
        )
    ],
    style={
        'maxWidth': '1200px', 
        'margin': '0 auto',
        'padding': '20px',
    }
)

layout = html.Div([
    header,
    content
])
