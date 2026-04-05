from flask import Blueprint, jsonify
import pandas as pd
import json
import os

data = Blueprint('data', __name__)

def _load_installations():
    path = 'data/installations/installations.geojson'
    with open(path) as f:
        text = f.read().replace(': NaN', ': null')
    return json.loads(text)

def _load_dataverses():
    df = pd.read_csv('data/dataverses.csv')
    return json.loads(df.to_json(orient='records'))

def _load_datasets_by_installation():
    df = pd.read_csv('data/dataverses.csv', usecols=['installation', 'datasetCount'])
    result = df.groupby('installation')['datasetCount'].sum().nlargest(12)

    return [{'installation': k, 'count': int(v)} for k, v in result.items()]

_installations_cache = _load_installations()
_dataverses_cache = _load_dataverses()
_datasets_by_installation_cache = _load_datasets_by_installation()

@data.route("/api/items")
def get_items():
    return jsonify([
        {"id": 1, "name": "Jeff"},
        {"id": 2, "name": "Bill"}
    ])

@data.route("/api/installations")
def get_installations():
    return jsonify(_installations_cache)

@data.route("/api/dataverses")
def get_dataverses():
    return jsonify(_dataverses_cache)

@data.route("/api/datasets-by-installation")
def get_datasets_by_installation():
    return jsonify(_datasets_by_installation_cache)

@data.route("/api/installations-by-country")
def get_installations_by_country():
    df = pd.read_csv('data/installations/installations.csv', usecols=['country'])
    result = df['country'].value_counts().reset_index()
    result.columns = ['country', 'count']
    result.sort_values('count', ascending=False, inplace=True)
    return result.to_dict(orient='records')
    
blueprints = [data]