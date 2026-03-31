from flask import Blueprint, jsonify

data = Blueprint('data', __name__)

@data.route("/api/items")
def get_items():
    return jsonify([
        {"id": 1, "name": "Jeff"},
        {"id": 2, "name": "Bill"}
    ])

blueprints = [data]