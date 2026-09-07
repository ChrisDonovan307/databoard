from pathlib import Path
from typing import Dict
import math
import pandas as pd
import json
import os
from requests_cache import CachedSession

from db import get_session
from db.models import Installation as InstallationRow
from db.upsert import upsert_rows

_DB_COLS = [
    "hostname",
    "url",
    "name",
    "description",
    "lat",
    "lng",
    "country",
    "launch_year",
    "doi_authority",
    "dv_hub_id",
    "metrics",
]


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


class Installation:
    def __init__(self):
        self.data_dir: Path = Path("data/installations")
        self.url: str = "https://raw.githubusercontent.com/IQSS/dataverse-installations/main/data/data.json"
        self.uvm: Dict = {
            "name": "University of Vermont Dataverse",
            "description": "",
            "lat": 44.478385,
            "lng": -73.200558,
            "hostname": "dataverse.uvm.edu",
            "launch_year": 2025,
            "country": "USA",
        }

    def call(self, export_files: bool = False):
        """Pull installations, process, and upsert into the ``installation`` table.

        Set ``export_files=True`` to also drop the legacy CSV + GeoJSON.
        """
        raw = self.get_raw()
        df = self.process(raw)
        self.save_db(df)
        if export_files:
            self.save_csv(df)
            self.save_geojson(df)

    def save_db(self, df: pd.DataFrame):
        """Upsert installations into MySQL, keyed on ``url``."""
        rows = []
        for _, r in df.iterrows():
            row = {c: _clean(r.get(c)) for c in _DB_COLS}
            if not row.get("url"):
                continue
            if row.get("metrics") is not None:
                row["metrics"] = bool(row["metrics"])
            if row.get("launch_year") is not None:
                try:
                    row["launch_year"] = int(row["launch_year"])
                except (ValueError, TypeError):
                    row["launch_year"] = None
            rows.append(row)
        with get_session() as session:
            upsert_rows(
                session.connection(),
                InstallationRow.__table__,
                rows,
                index_elements=["url"],
                update_cols=[c for c in _DB_COLS if c != "url"],
            )

    def get_raw(self) -> dict:
        session = CachedSession()
        response = session.get(self.url)
        return response.json()

    def process(self, raw: dict) -> pd.DataFrame:
        """Make a clean df of installations"""
        df = pd.DataFrame(raw["installations"])
        # Add UVM to list
        df.loc[len(df)] = self.uvm
        # Add url column
        df["url"] = "https://" + df["hostname"]
        return df

    def save_csv(self, df: pd.DataFrame):
        """Save installations DF as CSV (this is what services.metadata reads for URLs)"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.data_dir / "installations.csv", index=False)

    def save_geojson(self, df: pd.DataFrame):
        """Take a DF of installations data and saves a GeoJSON"""
        features = []
        for _, row in df.iterrows():
            feature = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row["lng"], row["lat"]]},
                "properties": {
                    "name": row["name"],
                    "hostname": row["hostname"],
                    "metrics": row["metrics"],
                    "url": row["url"],
                    "about": row.get("about"),
                    "country": row.get("country"),
                    "launch_year": row.get("launch_year"),
                    "description": row.get("description"),
                    "doi_authority": row.get("doi_authority"),
                    "dv_hub_id": row.get("dv_hub_id"),
                },
            }
            features.append(feature)

        geojson = {"type": "FeatureCollection", "features": features}
        with open(os.path.join(self.data_dir, "installations.geojson"), "w") as f:
            f.write(json.dumps(geojson))
