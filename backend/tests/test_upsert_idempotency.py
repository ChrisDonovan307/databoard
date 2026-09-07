"""Ingest the same batch twice against an in-memory SQLite DB and assert row
counts don't grow and child rows don't multiply."""

import pytest
from sqlalchemy import create_engine, func, select

from db.models import (
    Base,
    Dataset,
    DatasetAuthor,
    DatasetKeyword,
    Dataverse,
    Installation,
)
from services.ingest import ingest_installation


ITEMS = [
    {
        "type": "dataverse",
        "identifier": "root-collection",
        "name": "Root Collection",
        "published_at": "2020-01-01T00:00:00Z",
        "datasetCount": "2.0",
    },
    {
        "type": "dataset",
        "global_id": "doi:10.5072/FK2/AAA",
        "identifier": "nan",
        "name": "First dataset",
        "published_at": "2021-05-01T00:00:00Z",
        "identifier_of_dataverse": "root-collection",
        "keywords": "['climate', 'ice']",
        "authors": "['Smith, J.', 'Doe, A.']",
        "subjects": "['Earth and Environmental Sciences']",
        "contacts": "[{'name': 'Help Desk', 'affiliation': 'Uni'}]",
    },
    {
        "type": "dataset",
        "global_id": "doi:10.5072/FK2/BBB",
        "identifier": "nan",
        "name": "Second dataset",
        "published_at": "2021-06-01T00:00:00Z",
        "identifier_of_dataverse": "root-collection",
        "keywords": "['ice']",
        "authors": "['Smith, J.']",
    },
]


@pytest.fixture
def conn():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        c.execute(Installation.__table__.insert().values(id=1, url="https://ex.test"))
        yield c


def _counts(conn):
    return {
        "dataverse": conn.execute(select(func.count()).select_from(Dataverse)).scalar(),
        "dataset": conn.execute(select(func.count()).select_from(Dataset)).scalar(),
        "dataset_author": conn.execute(
            select(func.count()).select_from(DatasetAuthor)
        ).scalar(),
        "dataset_keyword": conn.execute(
            select(func.count()).select_from(DatasetKeyword)
        ).scalar(),
    }


def test_ingest_is_idempotent(conn):
    ingest_installation(conn, 1, ITEMS)
    first = _counts(conn)
    assert first == {
        "dataverse": 1,
        "dataset": 2,
        "dataset_author": 3,  # (Smith,Doe) on ds1 + (Smith) on ds2
        "dataset_keyword": 3,  # (climate,ice) on ds1 + (ice) on ds2
    }

    ingest_installation(conn, 1, ITEMS)
    assert _counts(conn) == first

    # shared lookups were reused, not duplicated
    assert conn.execute(select(func.count()).select_from(__keyword_table())).scalar() == 2
    assert conn.execute(select(func.count()).select_from(__author_table())).scalar() == 2

    # soft FK resolved
    ds = conn.execute(select(Dataset.dataverse_id)).scalars().all()
    assert all(v is not None for v in ds)


def test_ingest_updates_changed_fields(conn):
    ingest_installation(conn, 1, ITEMS)
    changed = [dict(ITEMS[1], name="First dataset (revised)")]
    ingest_installation(conn, 1, changed)
    name = conn.execute(
        select(Dataset.name).where(Dataset.natural_key == "doi:10.5072/FK2/AAA")
    ).scalar()
    assert name == "First dataset (revised)"


def __keyword_table():
    from db.models import Keyword

    return Keyword


def __author_table():
    from db.models import Author

    return Author
