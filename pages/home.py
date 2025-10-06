from dash import html
import dash

dash.register_page(__name__, path='/home')

layout = html.Div([
    # Header
    html.Div([
        html.H1('Welcome to Databoard', style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.Hr()
    ], style={'marginBottom': '30px'}),

    # Main Content
    html.Div([
        html.H2('Data Visualization Dashboard'),
        html.P('Explore interactive visualizations and data tables using the navigation above.'),
        html.Ul([
            html.Li('Graphs - View iris dataset visualizations'),
            html.Li('Tables - Browse interactive data tables')
        ])
    ], style={'maxWidth': '800px', 'margin': '0 auto', 'padding': '20px'}),

    # Footer
    html.Div([
        html.Hr(),
        html.P('© 2025 Databoard', style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '14px'})
    ], style={'marginTop': '50px'})
])
