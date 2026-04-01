from flask import Blueprint, jsonify
import json
import os

data = Blueprint('data', __name__)

@data.route("/api/items")
def get_items():
    return jsonify([
        {"id": 1, "name": "Jeff"},
        {"id": 2, "name": "Bill"}
    ])

@data.route("/api/installations")
def get_installations():
    path = 'data/installations/installations.geojson'
    with open(path) as f:
        text = f.read().replace(': NaN', ': null')
    return jsonify(json.loads(text))

blueprints = [data]