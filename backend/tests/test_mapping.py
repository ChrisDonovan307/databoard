from datetime import datetime

from services.mapping import (
    map_dataset_item,
    map_dataverse_item,
    parse_dt,
    parse_int,
    parse_list,
    parse_scalar,
)


def test_parse_scalar_nullish():
    for v in (None, float("nan"), "nan", "NaN", "", "  ", "None", "<NA>"):
        assert parse_scalar(v) is None
    assert parse_scalar("  hi ") == "hi"
    assert parse_scalar(0) == "0"


def test_parse_int():
    assert parse_int("18.0") == 18
    assert parse_int("5703.0") == 5703
    assert parse_int(1.0) == 1
    assert parse_int("nan") is None
    assert parse_int(None) is None
    assert parse_int("not a number") is None


def test_parse_dt_tolerates_junk():
    assert parse_dt("2011-01-13T08:00:00Z") == datetime(2011, 1, 13, 8, 0, 0)
    assert parse_dt("1000-12-26T00:00:00Z") == datetime(1000, 12, 26, 0, 0, 0)
    assert parse_dt("") is None
    assert parse_dt("nan") is None
    assert parse_dt("garbage") is None


def test_parse_list_forms():
    import numpy as np

    assert parse_list(["a", "b"]) == ["a", "b"]
    assert parse_list("['Economic Behaviour', 'Income']") == ["Economic Behaviour", "Income"]
    assert parse_list("[{'name': 'X', 'affiliation': ''}]") == [{"name": "X", "affiliation": ""}]
    assert parse_list("nan") == []
    assert parse_list(None) == []
    assert parse_list(float("nan")) == []
    assert parse_list("not-a-list") == ["not-a-list"]
    # parquet list columns round-trip as numpy arrays
    assert parse_list(np.array(["a", "b"])) == ["a", "b"]
    assert parse_list(np.array([], dtype=object)) == []


def test_map_dataverse_item_needs_identifier():
    assert map_dataverse_item({"identifier": "nan", "name": "X"}, 1) is None
    row = map_dataverse_item(
        {"identifier": "icpsr", "name": "ICPSR", "published_at": "2020-06-23T19:18:10Z"}, 7
    )
    assert row["installation_id"] == 7
    assert row["identifier"] == "icpsr"
    assert row["published_at"] == datetime(2020, 6, 23, 19, 18, 10)


def test_map_dataset_item_natural_key_and_children():
    item = {
        "type": "dataset",
        "global_id": "hdl:11272.1/AB2/PY4W8B",
        "identifier": "nan",
        "name": "Canada Revenue Tax Statistics",
        "published_at": "2011-01-13T08:00:00Z",
        "fileCount": "18.0",
        "versionId": "5703.0",
        "majorVersion": "1.0",
        "minorVersion": "0.0",
        "keywords": "['Economic Behaviour', 'Income']",
        "subjects": "['Other']",
        "authors": "['Canada Revenue Agency']",
        "contacts": "[{'name': 'Abacus support', 'affiliation': ''}]",
        "producers": "['Canada Revenue Agency']",
        "relatedMaterial": "['http://hdl.handle.net/10573/42429']",
        "geographicCoverage": "[{'other': 'Canada (CA)'}, {'country': 'Canada'}]",
        "identifier_of_dataverse": "abacus-licensed",
    }
    row, children = map_dataset_item(item, 3)
    assert row["natural_key"] == "hdl:11272.1/AB2/PY4W8B"
    assert row["global_id"] == "hdl:11272.1/AB2/PY4W8B"
    assert row["identifier"] is None
    assert row["file_count"] == 18
    assert row["version_id"] == 5703
    assert row["major_version"] == 1
    assert row["parent_dataverse_identifier"] == "abacus-licensed"

    assert [a["name"] for a in children["authors"]] == ["Canada Revenue Agency"]
    assert children["authors"][0]["ordinal"] == 0
    assert children["authors"][0]["name_norm"] == "canada revenue agency"
    assert {k["term"] for k in children["keywords"]} == {"Economic Behaviour", "Income"}
    assert children["subjects"] == [{"term": "Other"}]
    assert children["contacts"] == [{"name": "Abacus support", "affiliation": None}]
    assert children["related_material"] == [{"text": "http://hdl.handle.net/10573/42429"}]
    covs = {c["coverage"] for c in children["geographic_coverage"]}
    assert covs == {"Canada (CA)", "Canada"}


def test_map_dataset_item_falls_back_to_identifier():
    row, _ = map_dataset_item(
        {"type": "dataset", "global_id": "nan", "identifier": "abc123", "name": "X"}, 1
    )
    assert row["natural_key"] == "abc123"


def test_map_dataset_item_unkeyable_is_none():
    assert map_dataset_item({"type": "dataset", "global_id": "nan", "identifier": "nan"}, 1) is None
