"""One-time initial load: existing metadata.parquet -> MySQL.

Uses the same ``ingest_installation`` path as the live pull. Seeds each
installation's watermark to its max ``published_at`` **unless** the dump was
capped for that installation (row count >= page_limit * per_page), in which case
it is left un-watermarked so the next incremental run does a full pull for it.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from db import get_session
from db.models import Installation as InstallationRow, PullState
from db.upsert import upsert_rows
from services.ingest import ingest_installation
from services.mapping import parse_dt

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARQUET = ROOT / "data" / "metadata" / "metadata.parquet"


def load_parquet_dump(
    parquet_path: str | Path = DEFAULT_PARQUET,
    dump_page_limit: int = 300,
    per_page: int = 1000,
) -> None:
    cap = dump_page_limit * per_page
    df = pd.read_parquet(parquet_path)
    logger.info(f"Loaded {len(df)} rows from {parquet_path}")

    with get_session() as s:
        id_by_url = dict(
            s.execute(select(InstallationRow.url, InstallationRow.id)).all()
        )
    if not id_by_url:
        raise RuntimeError(
            "installation table is empty - run `--cmd installations` before load-parquet"
        )

    watermark_rows: list[dict] = []
    skipped = 0

    for url, group in df.groupby("installation_url"):
        iid = id_by_url.get(url)
        if iid is None:
            logger.warning(f"{url}: not in installation table; skipping {len(group)} rows")
            skipped += len(group)
            continue

        items = group.to_dict("records")
        with get_session() as sess:
            counts = ingest_installation(sess.connection(), iid, items)
        logger.info(f"{url}: {counts} ({len(group)} source rows)")

        capped = len(group) >= cap
        if capped:
            logger.info(
                f"{url}: capped dump ({len(group)} >= {cap}); leaving un-watermarked "
                "so the next incremental run does a full pull"
            )
            continue
        published = [parse_dt(v) for v in group["published_at"]]
        published = [p for p in published if p is not None]
        if published:
            watermark_rows.append(
                {"installation_id": iid, "last_pulled_at": max(published)}
            )

    if watermark_rows:
        with get_session() as sess:
            upsert_rows(
                sess.connection(),
                PullState.__table__,
                watermark_rows,
                index_elements=["installation_id"],
                update_cols=["last_pulled_at"],
            )
    logger.info(
        f"Seeded {len(watermark_rows)} watermarks; "
        f"{len(df.groupby('installation_url')) - len(watermark_rows)} left un-watermarked; "
        f"{skipped} rows skipped (unknown installation)"
    )
