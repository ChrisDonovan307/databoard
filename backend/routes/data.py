from flask import Blueprint, jsonify
import json
import math
import pandas as pd

# api.py is imported by Flask as ``backend.api``, so this module is
# ``backend.routes.data`` and needs the package-qualified import (the
# services/ and pipeline/ code runs with backend/ on sys.path and uses ``db``).
from backend.db import get_engine

data = Blueprint("data", __name__)


def _prop(value):
    """JSON-safe scalar for GeoJSON properties (NaN -> None)."""
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


@data.route("/api/items")
def get_items():
    """Test Data"""
    return jsonify([{"id": 1, "name": "Jeff"}, {"id": 2, "name": "Bill"}])


@data.route("/api/installations")
def get_installations():
    """Installations and locations for the map, as a GeoJSON FeatureCollection."""
    df = pd.read_sql(
        "SELECT name, hostname, url, lat, lng, country, launch_year, "
        "description, doi_authority, dv_hub_id, metrics FROM installation",
        get_engine(),
    )
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [_prop(row["lng"]), _prop(row["lat"])],
            },
            "properties": {
                "name": _prop(row["name"]),
                "hostname": _prop(row["hostname"]),
                "metrics": _prop(row["metrics"]),
                "url": _prop(row["url"]),
                "about": None,
                "country": _prop(row["country"]),
                "launch_year": _prop(row["launch_year"]),
                "description": _prop(row["description"]),
                "doi_authority": _prop(row["doi_authority"]),
                "dv_hub_id": _prop(row["dv_hub_id"]),
            },
        }
        for _, row in df.iterrows()
    ]
    return jsonify({"type": "FeatureCollection", "features": features})


@data.route("/api/dataverses")
def get_dataverses():
    df = pd.read_sql(
        """
        SELECT dv.name,
               'dataverse'          AS type,
               NULL                 AS url,
               dv.identifier,
               dv.published_at      AS publishedAt,
               i.name               AS installation,
               i.url                AS installationUrl,
               dv.image_url         AS imageUrl,
               dv.affiliation,
               parent.name          AS parentDataverseName,
               dv.parent_dataverse_identifier AS parentDataverseIdentifier,
               dv.dataset_count     AS datasetCount
        FROM dataverse dv
        JOIN installation i ON i.id = dv.installation_id
        LEFT JOIN dataverse parent
               ON parent.installation_id = dv.installation_id
              AND parent.identifier = dv.parent_dataverse_identifier
        """,
        get_engine(),
    )
    json_str = df.to_json(orient="records") or "[]"
    return jsonify(json.loads(json_str))


@data.route("/api/datasets-by-installation")
def get_datasets_by_installation():
    df = pd.read_sql(
        """
        SELECT COALESCE(i.name, i.hostname) AS installation,
               SUM(dv.dataset_count)        AS count
        FROM dataverse dv
        JOIN installation i ON i.id = dv.installation_id
        GROUP BY COALESCE(i.name, i.hostname)
        ORDER BY count DESC
        LIMIT 12
        """,
        get_engine(),
    )
    return jsonify(
        [
            {"installation": r["installation"], "count": int(r["count"] or 0)}
            for _, r in df.iterrows()
        ]
    )


@data.route("/api/installations-by-country")
def get_installations_by_country():
    df = pd.read_sql(
        "SELECT country, COUNT(*) AS count FROM installation "
        "WHERE country IS NOT NULL GROUP BY country ORDER BY count DESC",
        get_engine(),
    )
    return df.to_dict(orient="records")


blueprints = [data]
