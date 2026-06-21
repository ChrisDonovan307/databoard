from dagster import asset, Config
from services.installations import Installation
from services.metadata import Metadata
import pandas as pd


class DatasetConfigUvm(Config):
    url_list: list[str] = ["https://dataverse.uvm.edu"]
    file_type: list[str] = ["dataset"]  # dataset or dataverse


@asset(group_name="installations")
def raw_installations() -> dict:
    return Installation().get_raw()


@asset(group_name="installations")
def clean_installations(raw_installations: dict) -> pd.DataFrame:
    return Installation().process(raw_installations)


@asset(group_name="installations")
def installation_geojson(clean_installations: pd.DataFrame):
    Installation().save_geojson(clean_installations)


@asset(group_name="datasets")
def uvm_meta_datasets(config: DatasetConfigUvm):
    Metadata(**config.model_dump()).call()
