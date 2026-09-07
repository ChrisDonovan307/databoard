"""Bulk upsert helpers, dialect-agnostic across MySQL (prod) and SQLite (tests).

The ORM unit-of-work is too slow for the parquet load and large incremental pulls,
so the heavy writes go through Core ``INSERT ... ON DUPLICATE KEY UPDATE`` (MySQL)
/ ``INSERT ... ON CONFLICT DO UPDATE`` (SQLite).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Table, tuple_
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection

_CHUNK = 2000


def _chunks(rows: Sequence[dict], size: int = _CHUNK) -> Iterable[Sequence[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def upsert_rows(
    conn: Connection,
    table: Table,
    rows: Sequence[dict[str, Any]],
    *,
    index_elements: Sequence[str],
    update_cols: Sequence[str] | None = None,
) -> None:
    """Insert ``rows`` into ``table``; on a conflict against ``index_elements``
    update ``update_cols`` (or do nothing if ``update_cols`` is empty/None)."""
    if not rows:
        return
    dialect = conn.dialect.name
    for chunk in _chunks(list(rows)):
        if dialect == "mysql":
            stmt = mysql_insert(table).values(list(chunk))
            if update_cols:
                stmt = stmt.on_duplicate_key_update(
                    {c: stmt.inserted[c] for c in update_cols}
                )
            else:
                # no-op update to swallow the duplicate
                first = index_elements[0]
                stmt = stmt.on_duplicate_key_update({first: stmt.inserted[first]})
        else:
            stmt = sqlite_insert(table).values(list(chunk))
            if update_cols:
                stmt = stmt.on_conflict_do_update(
                    index_elements=list(index_elements),
                    set_={c: stmt.excluded[c] for c in update_cols},
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=list(index_elements))
        conn.execute(stmt)


def get_or_create_lookup_ids(
    conn: Connection,
    table: Table,
    rows: Sequence[dict[str, Any]],
    *,
    key_cols: Sequence[str],
) -> dict[tuple, int]:
    """Upsert lookup ``rows`` (dedup on ``key_cols``), then read back a
    ``{key_tuple: id}`` map for every distinct key present in ``rows``."""
    if not rows:
        return {}

    # de-dup within the batch on the key tuple
    seen: dict[tuple, dict] = {}
    for r in rows:
        seen.setdefault(tuple(r[k] for k in key_cols), r)
    unique_rows = list(seen.values())

    upsert_rows(conn, table, unique_rows, index_elements=key_cols)

    keys = list(seen.keys())
    key_col_objs = [table.c[k] for k in key_cols]
    single = len(key_cols) == 1
    out: dict[tuple, int] = {}
    for i in range(0, len(keys), _CHUNK):
        chunk_keys = keys[i : i + _CHUNK]
        if single:
            predicate = key_col_objs[0].in_([k[0] for k in chunk_keys])
        else:
            predicate = tuple_(*key_col_objs).in_(chunk_keys)
        stmt = table.select().with_only_columns(table.c.id, *key_col_objs).where(predicate)
        for row in conn.execute(stmt):
            out[tuple(row[1:])] = row[0]
    return out


def replace_child_rows(
    conn: Connection,
    table: Table,
    dataset_ids: Sequence[int],
    rows: Sequence[dict[str, Any]],
) -> None:
    """Delete-then-reinsert a 1-to-many child table for the given dataset ids.

    Simplest correct upsert for child bags; scoped to just the datasets in the
    current batch. Churns auto-increment ids but converges on re-run.
    """
    if not dataset_ids:
        return
    conn.execute(table.delete().where(table.c.dataset_id.in_(list(dataset_ids))))
    for chunk in _chunks(list(rows)):
        if chunk:
            conn.execute(table.insert(), list(chunk))
