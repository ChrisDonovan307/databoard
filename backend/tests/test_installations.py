import json
from unittest.mock import patch

import pandas as pd

from services.installations import Installation

RAW = {
    "installations": [
        {
            "name": "Yale Dataverse",
            "description": "",
            "lat": 41.311,
            "lng": -72.926,
            "hostname": "dataverse.yale.edu",
            "metrics": True,
            "launch_year": 2015,
            "country": "USA",
        }
    ]
}


def test_process_adds_uvm_and_url_column():
    df = Installation().process(RAW)
    assert len(df) == 2  # Yale + UVM
    assert set(df["hostname"]) == {"dataverse.yale.edu", "dataverse.uvm.edu"}
    assert (df["url"] == "https://" + df["hostname"]).all()


def test_save_csv_writes_readable_csv(tmp_path):
    inst = Installation()
    inst.data_dir = tmp_path
    df = inst.process(RAW)

    inst.save_csv(df)

    out = pd.read_csv(tmp_path / "installations.csv")
    assert len(out) == 2
    assert "url" in out.columns


def test_save_geojson_writes_valid_feature_collection(tmp_path):
    inst = Installation()
    inst.data_dir = tmp_path
    df = inst.process(RAW)

    inst.save_geojson(df)

    geojson = json.loads((tmp_path / "installations.geojson").read_text())
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2
    yale = next(
        f for f in geojson["features"] if f["properties"]["hostname"] == "dataverse.yale.edu"
    )
    assert yale["geometry"] == {"type": "Point", "coordinates": [-72.926, 41.311]}
    assert yale["properties"]["url"] == "https://dataverse.yale.edu"


def test_call_pulls_processes_and_saves_both_files(tmp_path):
    inst = Installation()
    inst.data_dir = tmp_path

    with patch.object(inst, "get_raw", return_value=RAW):
        inst.call()

    assert (tmp_path / "installations.csv").exists()
    assert (tmp_path / "installations.geojson").exists()
    assert len(pd.read_csv(tmp_path / "installations.csv")) == 2
