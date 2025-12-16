from dash import html, dash_table
import dash

import pandas as pd
from sklearn.datasets import load_iris
import dash_ag_grid as dag

dash.register_page(__name__, path="/tables")

# Load iris dataset
# iris = load_iris()
# df = pd.DataFrame(iris.data, columns=iris.feature_names)
# df["species"] = pd.Categorical.from_codes(iris.target, iris.target_names)

# column_defs = [
#     {
#         'field': 'sepal length (cm)', 
#         'headerName': 'Sepal Length (cm)',
#         'filter': 'agNumberColumnFilter', 
#     },
#     {
#         'field': 'sepal width (cm)', 
#         'filter': 'agNumberColumnFilter'
#     },
#     {   
#         'field': 'petal length (cm)', 
#         'filter': 'agNumberColumnFilter'
#     },
#     {
#         'field': 'petal width (cm)', 
#         'filter': 'agNumberColumnFilter'
#     },
#     {
#         'field': 'species',
#         'headerName': 'Species',
#         'filter': 'agTextColumnFilter'
#     },
# ]

# grid_options={'animateRows': False}

df = pd.read_parquet('app/data/metadata/metadata.parquet')

grid = dag.AgGrid(
    id='table',
    rowData=df.to_dict('records'),
    columnDefs=[{"field": i} for i in df.columns], # shortcut 
    # columnDefs=column_defs,
    columnSize='sizeToFit', # widths
    dashGridOptions=grid_options
)

layout = html.Div(
    [
        # Header
        html.Div(
            [
                html.H1(
                    "Interactive Data Tables",
                    style={"textAlign": "center", "color": "#2c3e50"},
                ),
                html.P(
                    "Explore and filter the iris dataset",
                    style={"textAlign": "center", "color": "#7f8c8d"},
                ),
                html.Hr(),
            ],
            style={"marginBottom": "30px"},
        ),
        # Main Content
        html.Div(
            [
                html.H2("Iris Dataset Table"),
                grid,
            ],
            style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px"},
        ),
    ]
)
