from dash import Dash, html, dcc
import dash

PREFIX = '/databoard/'

app = dash.Dash(
    __name__, 
    use_pages=True,
    requests_pathname_prefix=PREFIX,
    routes_pathname_prefix=PREFIX
)
server = app.server #

app.layout = html.Div([
	html.H1('Multi-page app with Dash Pages'),

    html.Div([
        html.Div(
            dcc.Link(
                 f"{page['name']} - {page['relative_path']}", href=f"{page["relative_path"]}"
            )
        )
        for page in dash.page_registry.values()
    ]),

	dash.page_container
])

if __name__ == '__main__':
	app.run(debug=False) #

