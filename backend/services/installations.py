from pathlib import Path
from typing import Dict
import pandas as pd
import requests
import json
import os
from requests_cache import CachedSession

class Installation:
    def __init__(self):
        self.data_dir: str = Path('data/installations')
        self.url: str = 'https://raw.githubusercontent.com/IQSS/dataverse-installations/main/data/data.json'
        self.uvm: Dict = {
            'name': 'University of Vermont Dataverse',
            'description': '',
            'lat': 44.478385,
            'lng': -73.200558,
            'hostname': 'dataverse.uvm.edu',
            'launch_year': 2025,
            'country': 'USA'
        }
    

    def call(self):
        self._get()
        df = self._process()
        self._to_geojson(df)
    

    def _get(self):
        session = CachedSession()
        response = session.get(self.url)
        with open(os.path.join(self.data_dir, 'response.json'), "w") as f:
            f.write(response.text)


    def _process(self):
        """Make a clean df of installations"""

        # Read from json file
        with open(os.path.join(self.data_dir, "response.json"), "r") as f:
            res = json.load(f)
        df = pd.DataFrame(res['installations'])

        # Add UVM to list
        df.loc[len(df)] = self.uvm
        
        # Add url column
        df["url"] = "https://" + df["hostname"]
        
        return df
    

    def _to_geojson(self, df: pd.DataFrame):
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
                    "url": row['url'],
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
