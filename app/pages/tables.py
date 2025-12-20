from dash import html, dash_table, callback, Input, Output
import dash

import pandas as pd
from sklearn.datasets import load_iris
import dash_ag_grid as dag
from dash_bootstrap_templates import ThemeSwitchAIO

dash.register_page(__name__, path="/tables")


# df = pd.read_parquet('app/data/metadata/metadata.parquet')
df = pd.read_parquet('app/data/clean/installation_stats.parquet')
keep = [
    'name',
    'url',
    'launch_year',
    'country',
    'n_datasets',
    'n_files',
    'n_authors',
    'n_subjects',
    'n_keywords',
    'n_publishers',
    'metrics',
]
df = df[keep]
df.columns = df.columns.str.replace('_', ' ').str.title().str.replace('Url', 'URL')

# column_defs = [
#     {
#         'field': 'Name',
#     },
# ]

default_col_def = {
    "headerClass": "center-aligned-header", # defined in css
    "filter": True,
    "cellClass": "center-aligned-cell", # defined in css
}

grid_options = {
    # "pagination": True,
    # "paginationAutoPageSize": True,
}

grid = dag.AgGrid(
    id='table',
    rowData=df.to_dict('records'),
    columnDefs=[{"field": i} for i in df.columns], # shortcut
    defaultColDef=default_col_def,
    columnSize='autoSize',
    dashGridOptions=grid_options,
    style={"height": "100%", "width": "100%"}  # fill parent container
)

layout = html.Div([
        html.Div(
            [
                html.H2("Iris Dataset Table", style={"marginBottom": "15px"}),
                html.P("Note that we are missing records for some of the biggest installations, including Harvard, UNC, and others."),
                grid,
            ],
            style={
                "height": "calc(100vh - 200px)", # leave room for footer
                "width": "100%",
                "padding": "20px",
                "display": "flex",
                "flexDirection": "column"
            },
        ),
    ]
)


# make table theme match global theme
@callback(
    Output('table', 'className'),
    Input(ThemeSwitchAIO.ids.switch("theme"), "value")
)
def update_table_theme(theme_switch):
    if theme_switch:
        return "ag-theme-balham-dark"
    else:
        return "ag-theme-balham"
