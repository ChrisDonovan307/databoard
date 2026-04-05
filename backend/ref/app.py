from flask import Flask

app = Flask(__name__)

@app.route("/flask_test/")
def hello_world():
    return "<p>Hello, World! This is a Flask app</p>"

if __name__ == "__main__":
    app.run()
