from pathlib import Path
from typing import Dict
import pandas as pd
import json
import os
from requests_cache import CachedSession


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
