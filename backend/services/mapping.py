"""Pure Record -> table-rows mapping.

One code path for both the parquet loader (fields arrive as ``repr``-strings such
as ``"['a', 'b']"`` and the literal string ``"nan"``) and the live Search API pull
(fields arrive as real ``list`` / ``dict`` / ``None``). No I/O here.
"""

from __future__ import annotations

import ast
import math
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import numpy as np

_NULLISH = {"", "nan", "none", "null", "<na>"}


def parse_scalar(value: Any) -> str | None:
    """Return a trimmed string, or None for any nullish/missing input."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    s = str(value).strip()
    if s.lower() in _NULLISH:
        return None
    return s


def parse_int(value: Any) -> int | None:
    s = parse_scalar(value)
    if s is None:
        return None
    try:
        return int(float(s))
    except (ValueError, OverflowError):
        return None


def parse_dt(value: Any) -> datetime | None:
    """Tolerant ISO-8601 parse. Bad/absent values -> None. Returns a naive
    datetime (the DB columns are naive)."""
    s = parse_scalar(value)
    if s is None:
        return None
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt.replace(tzinfo=None)


def parse_list(value: Any) -> list:
    """Coerce to a list. Real lists / numpy arrays (parquet list columns come
    back as ndarrays) pass through; ``repr``-strings are ``literal_eval``-ed;
    anything nullish or unparseable -> []."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple, set)):
        return list(value)
    s = parse_scalar(value)
    if s is None:
        return []
    if s and s[0] in "[(":
        try:
            parsed = ast.literal_eval(s)
        except (ValueError, SyntaxError):
            return []
        return list(parsed) if isinstance(parsed, (list, tuple)) else [parsed]
    return [s]


def norm(value: Any) -> str:
    s = parse_scalar(value)
    return s.lower().strip() if s else ""


def _name_affil(entry: Any) -> tuple[str | None, str | None]:
    """A person-ish entry is either a bare name string or ``{name, affiliation}``."""
    if isinstance(entry, Mapping):
        return parse_scalar(entry.get("name")), parse_scalar(entry.get("affiliation"))
    return parse_scalar(entry), None


def _coverage_str(entry: Any) -> str | None:
    if isinstance(entry, Mapping):
        parts = [parse_scalar(v) for v in entry.values()]
        joined = ", ".join(p for p in parts if p)
        return joined or None
    return parse_scalar(entry)


def map_dataverse_item(item: Mapping, installation_id: int) -> dict | None:
    """Row for the ``dataverse`` table, or None if it has no usable identifier."""
    identifier = parse_scalar(item.get("identifier"))
    if identifier is None:
        return None
    return {
        "installation_id": installation_id,
        "identifier": identifier[:191],
        "name": parse_scalar(item.get("name")),
        "description": parse_scalar(item.get("description")),
        "published_at": parse_dt(item.get("published_at")),
        "affiliation": parse_scalar(item.get("affiliation")),
        "parent_dataverse_identifier": parse_scalar(
            item.get("parentDataverseIdentifier")
        ),
        "image_url": parse_scalar(item.get("image_url")),
        "dataset_count": parse_int(item.get("datasetCount")),
    }


def map_dataset_item(
    item: Mapping, installation_id: int
) -> tuple[dict, dict[str, list[dict]]] | None:
    """(dataset row, {child_table_key: [rows]}), or None if unkeyable."""
    global_id = parse_scalar(item.get("global_id"))
    identifier = parse_scalar(item.get("identifier"))
    natural_key = global_id or identifier
    if natural_key is None:
        return None

    row = {
        "installation_id": installation_id,
        "parent_dataverse_identifier": parse_scalar(
            item.get("identifier_of_dataverse")
        ),
        "global_id": global_id,
        "identifier": identifier,
        "natural_key": natural_key[:255],
        "name": parse_scalar(item.get("name")),
        "description": parse_scalar(item.get("description")),
        "published_at": parse_dt(item.get("published_at")),
        "created_at": parse_dt(item.get("createdAt")),
        "updated_at": parse_dt(item.get("updatedAt")),
        "publisher": parse_scalar(item.get("publisher")),
        "citation": parse_scalar(item.get("citation")),
        "citation_html": parse_scalar(item.get("citationHtml")),
        "storage_identifier": parse_scalar(item.get("storageIdentifier")),
        "file_count": parse_int(item.get("fileCount")),
        "version_id": parse_int(item.get("versionId")),
        "version_state": parse_scalar(item.get("versionState")),
        "major_version": parse_int(item.get("majorVersion")),
        "minor_version": parse_int(item.get("minorVersion")),
    }

    authors = []
    for i, entry in enumerate(parse_list(item.get("authors"))):
        name, affil = _name_affil(entry)
        if not name:
            continue
        authors.append(
            {
                "name": name,
                "affiliation": affil,
                "identifier": "",
                "name_norm": norm(name)[:191],
                "affiliation_norm": norm(affil)[:191],
                "ordinal": i,
            }
        )

    keywords = [
        {"term": t, "term_norm": norm(t)[:255]}
        for t in (parse_scalar(x) for x in parse_list(item.get("keywords")))
        if t
    ]
    subjects = [
        {"term": t[:255]}
        for t in (parse_scalar(x) for x in parse_list(item.get("subjects")))
        if t
    ]

    publications = []
    for entry in parse_list(item.get("publications")):
        if isinstance(entry, Mapping):
            citation = parse_scalar(entry.get("citation"))
            url = parse_scalar(entry.get("url")) or ""
            id_type = parse_scalar(entry.get("idType"))
            id_number = parse_scalar(entry.get("idNumber")) or ""
        else:
            citation = parse_scalar(entry)
            url, id_type, id_number = "", None, ""
        if not (citation or url or id_number):
            continue
        publications.append(
            {
                "citation": citation,
                "citation_norm": norm(citation)[:255],
                "url": url[:255],
                "id_type": id_type,
                "id_number": id_number[:128],
            }
        )

    contacts = []
    for entry in parse_list(item.get("contacts")):
        name, affil = _name_affil(entry)
        if name or affil:
            contacts.append({"name": name, "affiliation": affil})

    producers = []
    for entry in parse_list(item.get("producers")):
        name, affil = _name_affil(entry)
        if name or affil:
            producers.append({"name": name, "affiliation": affil})

    related_material = [
        {"text": t}
        for t in (parse_scalar(x) for x in parse_list(item.get("relatedMaterial")))
        if t
    ]
    data_sources = [
        {"text": t}
        for t in (parse_scalar(x) for x in parse_list(item.get("dataSources")))
        if t
    ]
    geographic_coverage = [
        {"coverage": c[:512]}
        for c in (_coverage_str(x) for x in parse_list(item.get("geographicCoverage")))
        if c
    ]
    publication_statuses = [
        {"status": s[:64]}
        for s in (parse_scalar(x) for x in parse_list(item.get("publicationStatuses")))
        if s
    ]

    children = {
        "authors": authors,
        "keywords": keywords,
        "subjects": subjects,
        "publications": publications,
        "contacts": contacts,
        "producers": producers,
        "related_material": related_material,
        "data_sources": data_sources,
        "geographic_coverage": geographic_coverage,
        "publication_statuses": publication_statuses,
    }
    return row, children
