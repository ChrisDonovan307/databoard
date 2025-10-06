from dash import html, dash_table
import dash
import pandas as pd
from sklearn.datasets import load_iris

dash.register_page(__name__, path='/tables')

# Load iris dataset
iris = load_iris()
df = pd.DataFrame(iris.data, columns=iris.feature_names)
df['species'] = pd.Categorical.from_codes(iris.target, iris.target_names)

layout = html.Div([
    # Header
    html.Div([
        html.H1('Interactive Data Tables', style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.P('Explore and filter the iris dataset', style={'textAlign': 'center', 'color': '#7f8c8d'}),
        html.Hr()
    ], style={'marginBottom': '30px'}),

    # Main Content
    html.Div([
        html.H2('Iris Dataset Table'),
        html.P('Click column headers to sort, use filters to search. Showing 10 rows per page.'),

        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            page_size=10,
            sort_action='native',
            filter_action='native',
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px'
            },
            style_header={
                'backgroundColor': 'rgb(210, 210, 210)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(220, 220, 220)'
                }
            ]
        )
    ], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px'}),

    # Footer
    html.Div([
        html.Hr(),
        html.P('© 2025 Databoard', style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '14px'})
    ], style={'marginTop': '50px'})
])
