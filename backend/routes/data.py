from flask import Blueprint, jsonify
import pandas as pd
import json

data = Blueprint('data', __name__)

@data.route("/api/items")
def get_items():
    """Test Data"""
    return jsonify([
        {"id": 1, "name": "Jeff"},
        {"id": 2, "name": "Bill"}
    ])

@data.route("/api/installations")
def get_installations():
    """Installations and locations for map"""
    with open('data/installations/installations.geojson') as f:
        text = f.read().replace(': NaN', ': null')
    return jsonify(json.loads(text))

@data.route("/api/dataverses")
def get_dataverses():
    df = pd.read_csv('data/dataverses.csv')
    return jsonify(json.loads(df.to_json(orient='records')))

@data.route("/api/datasets-by-installation")
def get_datasets_by_installation():
    df = pd.read_csv('data/dataverses.csv', usecols=['installation', 'datasetCount'])
    result = df.groupby('installation')['datasetCount'].sum().nlargest(12)
    return jsonify([{'installation': k, 'count': int(v)} for k, v in result.items()])

@data.route("/api/installations-by-country")
def get_installations_by_country():
    df = pd.read_csv('data/installations/installations.csv', usecols=['country'])
    result = df['country'].value_counts().reset_index()
    result.columns = ['country', 'count']
    result.sort_values('count', ascending=False, inplace=True)
    return result.to_dict(orient='records')

blueprints = [data]
