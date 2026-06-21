from dagster import asset
from services.installations import Installation
from services.metadata import Metadata


@asset
def installations():
    Installation().call()


@asset
def metadata():
    Metadata().call()
