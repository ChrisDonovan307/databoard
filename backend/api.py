from flask import Flask
# from flask_cors import CORS
from routes import blueprints

def create_app():
    app = Flask(__name__)
    app.secret_key = "change-me"
    # CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}}) # svelte dev server

    for blueprint in blueprints:
        app.register_blueprint(blueprint, url_prefix="/databoard")

    return app

app = create_app()

if __name__ == '__main__':
	app.run(debug=False)
