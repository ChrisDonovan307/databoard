from dash import html, dcc, callback, Output, Input, State
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
        html.Div(
            dcc.Graph(
                id='map', # matches callback output[0]
                # figure=fig, # matches callback output[1]
                style={
                    'height': '70vh',
                }
            ),
            id='map-container',
            style={
                'position': 'relative',
            }
        ),
        dcc.Store(id='popup-data', data=None),
        html.Div(
            id="popup",
            children=[
                html.Button(
                    "×",
                    id='popup-close-btn',
                    style={
                        'position': 'absolute',
                        'top': '5px',
                        'right': '5px',
                        'background': 'none',
                        'border': 'none',
                        'fontSize': '20px',
                        'cursor': 'pointer',
                        'color': '#666',
                        'padding': '0',
                        'width': '25px',
                        'height': '25px',
                    }
                ),
                html.Div(id='popup-content')
            ],
            style={
                "display": "none",
                "position": "fixed",
                "bottom": "20px",
                "right": "20px",
                "border": "2px solid #333",
                "backgroundColor": "white",
                "color": "black",
                "borderRadius": "8px",
                "padding": "15px",
                "zIndex": "9999",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
                "maxWidth": "300px",
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
        clickmode='event',
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

# Store popup data when map is clicked
@callback(
    Output('popup-data', 'data'),
    Input("map", "clickData"),
    Input("popup-close-btn", "n_clicks"),
    prevent_initial_call=True
)
def update_popup_data(clickData, close_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return None

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'popup-close-btn':
        return None
    elif trigger_id == 'map' and clickData:
        pt = clickData["points"][0]
        return {
            'name': pt['customdata'][0],
            'hostname': pt['customdata'][1],
            'launch_year': pt['customdata'][2],
            'lat': pt['lat'],
            'lon': pt['lon']
        }
    return None

# Update popup display based on stored data
@callback(
    Output("popup", "style"),
    Output("popup-content", "children"),
    Input('popup-data', 'data'),
)
def display_popup(data):
    if not data:
        return {"display": "none"}, ""

    popup_style = {
        "display": "block",
        "position": "fixed",
        "bottom": "20px",
        "right": "20px",
        "border": "2px solid #333",
        "backgroundColor": "white",
        "color": "black",
        "borderRadius": "8px",
        "padding": "15px",
        "zIndex": "9999",
        "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
        "maxWidth": "300px",
    }

    popup_content = html.Div([
        html.H4(data['name'], style={'marginTop': '0', 'marginBottom': '10px', 'paddingRight': '25px'}),
        html.Div([html.Strong("Hostname: "), data['hostname']], style={'marginBottom': '8px'}),
        html.Div([html.Strong("Launch Year: "), str(data['launch_year'])], style={'marginBottom': '8px'}),
        html.Div([html.Strong("Coordinates: "), f"{data['lat']:.5f}, {data['lon']:.5f}"]),
    ])

    return popup_style, popup_content


layout = html.Div([
    content
])
