from dagster import asset
from services.installations import Installation
from services.metadata import Metadata
import pandas as pd


@asset(group_name="installations")
def raw_installations() -> dict:
    return Installation().get_raw()


@asset(group_name="installations")
def clean_installations(raw_installations: dict) -> pd.DataFrame:
    return Installation().process(raw_installations)


@asset(group_name="installations")
def installation_geojson(clean_installations: pd.DataFrame):
    Installation().save_geojson(clean_installations)


@asset(group_name="metadata")
def metadata():
    Metadata().call()
