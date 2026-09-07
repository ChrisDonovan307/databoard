"""Upsert one installation's harvested records into the normalised schema.

Shared by the parquet loader and the live pull. Everything for a single
installation runs inside one transaction supplied by the caller.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import select, update
from sqlalchemy.engine import Connection

from db.models import (
    Dataset,
    DatasetAuthor,
    DatasetContact,
    DatasetDataSource,
    DatasetGeographicCoverage,
    DatasetKeyword,
    DatasetProducer,
    DatasetPublication,
    DatasetPublicationStatus,
    DatasetRelatedMaterial,
    DatasetSubject,
    Dataverse,
    Author,
    Keyword,
    Publication,
    Subject,
)
from db.upsert import get_or_create_lookup_ids, replace_child_rows, upsert_rows
from services.mapping import map_dataset_item, map_dataverse_item, parse_scalar

_DATAVERSE_UPDATE = [
    "name",
    "description",
    "published_at",
    "affiliation",
    "parent_dataverse_identifier",
    "image_url",
    "dataset_count",
]
_DATASET_UPDATE = [
    "parent_dataverse_identifier",
    "global_id",
    "identifier",
    "name",
    "description",
    "published_at",
    "created_at",
    "updated_at",
    "publisher",
    "citation",
    "citation_html",
    "storage_identifier",
    "file_count",
    "version_id",
    "version_state",
    "major_version",
    "minor_version",
]


def ingest_installation(
    conn: Connection,
    installation_id: int,
    items: Sequence[Mapping],
) -> dict[str, int]:
    """Upsert a batch of Search API records (mixed dataverse/dataset) for one
    installation. Returns simple counts for logging."""
    dv_rows = []
    ds_rows = []
    ds_children: dict[str, dict[str, list[dict]]] = {}

    for item in items:
        itype = parse_scalar(item.get("type")) or ""
        if itype == "dataverse":
            row = map_dataverse_item(item, installation_id)
            if row:
                dv_rows.append(row)
        elif itype == "dataset":
            mapped = map_dataset_item(item, installation_id)
            if mapped:
                row, children = mapped
                ds_rows.append(row)
                ds_children[row["natural_key"]] = children

    upsert_rows(
        conn,
        Dataverse.__table__,
        dv_rows,
        index_elements=["installation_id", "identifier"],
        update_cols=_DATAVERSE_UPDATE,
    )
    upsert_rows(
        conn,
        Dataset.__table__,
        ds_rows,
        index_elements=["installation_id", "natural_key"],
        update_cols=_DATASET_UPDATE,
    )

    if not ds_rows:
        return {"dataverses": len(dv_rows), "datasets": 0}

    # resolve soft FK dataset -> dataverse for rows that don't have one yet
    conn.execute(
        update(Dataset)
        .where(
            Dataset.installation_id == installation_id,
            Dataset.dataverse_id.is_(None),
            Dataset.parent_dataverse_identifier.is_not(None),
        )
        .values(
            dataverse_id=select(Dataverse.id)
            .where(
                Dataverse.installation_id == installation_id,
                Dataverse.identifier == Dataset.parent_dataverse_identifier,
            )
            .scalar_subquery()
        )
    )

    natural_keys = [r["natural_key"] for r in ds_rows]
    ds_id: dict[str, int] = {}
    for i in range(0, len(natural_keys), 2000):
        chunk = natural_keys[i : i + 2000]
        rows = conn.execute(
            select(Dataset.natural_key, Dataset.id).where(
                Dataset.installation_id == installation_id,
                Dataset.natural_key.in_(chunk),
            )
        )
        ds_id.update({nk: _id for nk, _id in rows})

    dataset_ids = list(ds_id.values())

    # --- shared lookups ---
    all_authors, all_keywords, all_subjects, all_pubs = [], [], [], []
    for children in ds_children.values():
        all_authors += children["authors"]
        all_keywords += children["keywords"]
        all_subjects += children["subjects"]
        all_pubs += children["publications"]

    author_ids = get_or_create_lookup_ids(
        conn,
        Author.__table__,
        [
            {k: a[k] for k in ("name", "affiliation", "identifier", "name_norm", "affiliation_norm")}
            for a in all_authors
        ],
        key_cols=["name_norm", "affiliation_norm", "identifier"],
    )
    keyword_ids = get_or_create_lookup_ids(
        conn, Keyword.__table__, all_keywords, key_cols=["term_norm"]
    )
    subject_ids = get_or_create_lookup_ids(
        conn, Subject.__table__, all_subjects, key_cols=["term"]
    )
    publication_ids = get_or_create_lookup_ids(
        conn, Publication.__table__, all_pubs, key_cols=["url", "id_number", "citation_norm"]
    )

    # --- junctions + flat child bags (delete-then-reinsert per dataset) ---
    j_author, j_keyword, j_subject, j_pub = [], [], [], []
    c_contact, c_producer, c_related, c_source, c_geo, c_status = [], [], [], [], [], []

    for nk, children in ds_children.items():
        did = ds_id.get(nk)
        if did is None:
            continue
        seen_a = set()
        for a in children["authors"]:
            aid = author_ids.get((a["name_norm"], a["affiliation_norm"], a["identifier"]))
            if aid and aid not in seen_a:
                seen_a.add(aid)
                j_author.append({"dataset_id": did, "author_id": aid, "ordinal": a["ordinal"]})
        for k in children["keywords"]:
            kid = keyword_ids.get((k["term_norm"],))
            if kid:
                j_keyword.append({"dataset_id": did, "keyword_id": kid})
        for s in children["subjects"]:
            sid = subject_ids.get((s["term"],))
            if sid:
                j_subject.append({"dataset_id": did, "subject_id": sid})
        for p in children["publications"]:
            pid = publication_ids.get((p["url"], p["id_number"], p["citation_norm"]))
            if pid:
                j_pub.append({"dataset_id": did, "publication_id": pid})
        c_contact += [{"dataset_id": did, **r} for r in children["contacts"]]
        c_producer += [{"dataset_id": did, **r} for r in children["producers"]]
        c_related += [{"dataset_id": did, **r} for r in children["related_material"]]
        c_source += [{"dataset_id": did, **r} for r in children["data_sources"]]
        c_geo += [{"dataset_id": did, **r} for r in children["geographic_coverage"]]
        c_status += [{"dataset_id": did, **r} for r in children["publication_statuses"]]

    # dedup junction rows (composite PK)
    j_keyword = list({(r["dataset_id"], r["keyword_id"]): r for r in j_keyword}.values())
    j_subject = list({(r["dataset_id"], r["subject_id"]): r for r in j_subject}.values())
    j_pub = list({(r["dataset_id"], r["publication_id"]): r for r in j_pub}.values())

    replace_child_rows(conn, DatasetAuthor.__table__, dataset_ids, j_author)
    replace_child_rows(conn, DatasetKeyword.__table__, dataset_ids, j_keyword)
    replace_child_rows(conn, DatasetSubject.__table__, dataset_ids, j_subject)
    replace_child_rows(conn, DatasetPublication.__table__, dataset_ids, j_pub)
    replace_child_rows(conn, DatasetContact.__table__, dataset_ids, c_contact)
    replace_child_rows(conn, DatasetProducer.__table__, dataset_ids, c_producer)
    replace_child_rows(conn, DatasetRelatedMaterial.__table__, dataset_ids, c_related)
    replace_child_rows(conn, DatasetDataSource.__table__, dataset_ids, c_source)
    replace_child_rows(conn, DatasetGeographicCoverage.__table__, dataset_ids, c_geo)
    replace_child_rows(conn, DatasetPublicationStatus.__table__, dataset_ids, c_status)

    return {"dataverses": len(dv_rows), "datasets": len(ds_rows)}
