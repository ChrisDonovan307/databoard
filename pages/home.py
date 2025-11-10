from dash import html, dcc
import dash

dash.register_page(__name__, path='/')

layout = html.Div([
    # Header
    html.Div([
        html.H1('Home Page', style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.Hr()
    ], style={'marginBottom': '30px'}),

    # Main Content
    html.Div([
        html.H2('Dashboard Thing in Progress'),
        html.P('Do things and stuff and other things.'),
        html.Ul([
            html.Li(html.A("This is a link to graphs", href="https://cdonov12.w3.uvm.edu/databoard/graphs")),
            html.Li(dcc.Link('And another to tables', href="/databoard/tables"))
        ])
    ], style={'maxWidth': '800px', 'margin': '0 auto', 'padding': '20px'}),

    # Footer
    html.Div([
        html.Hr(),
        html.P('© 2025 Databoard', style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '14px'})
    ], style={'marginTop': '50px'})
])
