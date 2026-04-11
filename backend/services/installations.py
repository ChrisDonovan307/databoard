import pandas as pd
import requests
import json
from requests_cache import CachedSession

def get_installations():
    """
    Returns raw response
    """
    session = CachedSession()
    from app.services.config import config
    url = config['installations_url']
    return session.get(url)

def save_installations_json(response):
    with open("app/data/installations/response.json", "w") as f:
        f.write(response.text)

def get_installations_df(response):
    """Download installation list

    Returns
    -------
    df : pd.DataFrame
        DataFrame that includes installation names, urls, lat, lng, etc.
    """

    data = response.json()
    df = pd.DataFrame(data['installations'])
    df = add_uvm(df)
    df["url"] = "https://" + df["hostname"]
    return df

def add_uvm(df):
    """Add UVM to installation list

    UVM is not included in list at Dataverse site. Adding it here
    """
    df.loc[len(df)] = {
        'name': 'University of Vermont Dataverse',
        'description': '',
        'lat': 44.478385,
        'lng': -73.200558,
        'hostname': 'dataverse.uvm.edu',
        'launch_year': 2025,
        'country': 'USA'
    }
    return df

def save_installations_csv(df):
    df.to_csv('app/data/installations/installations.csv')

def save_installations_geojson(df):
    """
    Take a DF of installations data and saves a GeoJSON. Returns nothing
    """
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
    with open("app/data/installations/installations.geojson", "w") as f:
        f.write(json.dumps(geojson))

def save_installations_parquet(df):
    # Convert to consistent types for parquet
    df_copy = df.copy()
    if 'launch_year' in df_copy.columns:
        # First convert to numeric (coercing errors to NaN), then Int64
        df_copy['launch_year'] = pd.to_numeric(df_copy['launch_year'], errors='coerce').astype('Int64')
    df_copy.to_parquet("app/data/installations/installations.parquet", index=False)

def read_installations_response():
    with open("data/installations/response.json", "r") as f:
        res = json.load(f)
    return res

def get_installations_df_from_file():
    """
    Read installations from saved JSON file and return as DataFrame
    """
    data = read_installations_response()
    df = pd.DataFrame(data['installations'])
    df["url"] = "https://" + df["hostname"]
    return df
