from flask import Flask
from backend.routes import blueprints
from dotenv import load_dotenv
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = "change-me"

    load_dotenv()
    url_prefix = '/databoard' if os.getenv('ENV') == 'development' else ''

    for blueprint in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    return app

app = create_app()

if __name__ == '__main__':
	app.run(debug=False)
