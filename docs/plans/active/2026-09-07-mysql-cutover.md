# MySQL cutover — operational rollout

Follow-on to `2026-09-07-mysql-metadata-store.md` (code complete, verified on SQLite).
Everything here is operational: it needs the Silk MySQL credentials and an SSH
tunnel, no code changes. Report: `docs/reports/mysql-metadata-store.md`.

## Goal

Stand up the MySQL store on Silk, load the existing `metadata.parquet` into it,
backfill the installations the parquet couldn't cover, verify the dashboard, and
retire the flat files.

## Prerequisites

- Silk MySQL: username, password, database name; ability to `CREATE TABLE`.
- SSH access to the Silk host (for the tunnel; also how the deploy already works).
- The branch merged/committed (currently uncommitted on `incremental-updates`).

## Steps

### 1. Deploy prep on Silk
- `cd backend && uv sync` on Silk (new deps: `sqlalchemy==2.0.36`, `pymysql==1.1.1`).
- Set `DATABASE_URL` in Silk's environment / `backend/.env` pointing at **localhost**
  MySQL: `mysql+pymysql://<user>:<pass>@127.0.0.1:3306/<db>`.

### 2. Open the tunnel (laptop, leave running)
```
ssh -L 3306:localhost:3306 <silk-host>
```

### 3. Point the laptop at the tunnel
`backend/.env` (template already present, commented):
```
DATABASE_URL=mysql+pymysql://<user>:<pass>@127.0.0.1:3306/<db>
```

### 4. Create the schema
```
cd backend && uv run python -m services.orchestrator --cmd init-db
```
- Confirm all 18 tables created.
- Confirm MySQL accepts the composite-unique index lengths. The ≤191-char caps on
  composite-unique string columns should keep every index under the 3072-byte
  limit, but this is unverified on the live server — if `init-db` errors on an
  index length, shorten the offending column(s) in `backend/db/models.py` and
  re-run.

### 5. Initial load
```
uv run python -m services.orchestrator --cmd installations
uv run python -m services.orchestrator --cmd load-parquet
```
Sanity checks (via `mysql` client or a quick `read_sql`):
- `SELECT COUNT(*) FROM dataverse` ≈ 20,279
- `SELECT COUNT(*) FROM dataset` ≈ 521,451
- `SELECT COUNT(*) FROM pull_state` — one row per **non-capped** installation
  (~70); **no row** for `dataverse.harvard.edu` or the other ~15 capped ones.
- Spot-check a dataset's children (`dataset_author`, `dataset_keyword`, …) look
  populated.

### 6. Verify incremental
Run twice back-to-back against one small installation:
```
uv run python -m services.orchestrator --cmd metadata --incremental \
  --url-list https://dataverse.uvm.edu --page-limit 1
```
- Second run's upsert counts should be ≈0.
- `logs/metadata_fetch.log` shows whether the server-side `fq=dateSort` filter
  worked or the one-shot full-pull fallback fired.

### 7. Verify the dashboard
- Optionally capture the old responses first (from the last flat-file deploy or a
  reverted checkout): `curl -s localhost:5000/databoard/api/<route>` for
  `installations`, `dataverses`, `datasets-by-installation`,
  `installations-by-country`.
- `./run.sh`, load `/databoard` and `/databoard/detail`.
- Diff the four `/api/*` responses against the capture. Shapes must match; the
  `datasets-by-installation` / `installations-by-country` labels may differ
  slightly (now sourced from `installation.name` instead of the short slug) —
  that's expected.

### 8. Backfill the capped + missing installations
One uncapped run (long, unattended — Harvard alone is ~5.8M records):
```
uv run python -m services.orchestrator --cmd metadata --incremental \
  --page-limit 6000 --timeout 300 --page-delay 0.5
```
- Installations without a `pull_state` row get a full pull; the ~70 already
  watermarked only fetch their new tail.
- If Harvard still times out, run it alone with a higher `--timeout` /
  `--page-delay` per the "Large installations" section of `backend/README.md`.
- Re-check `SELECT COUNT(*) FROM dataset` afterwards.

### 9. Retire the flat files
Once the DB is confirmed serving the dashboard:
- Delete `backend/data/metadata/metadata.csv` / `.parquet` and
  `backend/data/dataverses.csv` (keep `installations.csv` — still the `_get_urls`
  fallback).
- `--export-parquet path/to/dump.parquet` if you want a shareable snapshot first.
- Move `2026-09-07-mysql-metadata-store.md` and this file to `docs/plans/done/`.

### 10. Schedule ongoing refresh
- Regular cadence: `--cmd metadata --incremental` (add `--cmd all` periodically to
  refresh the installation list too).
- Wire into cron / the Dagster schedule (currently commented out in
  `backend/pipeline/definitions.py`) as preferred.

## Risks / watch-items

- **Index length on live MySQL** (step 4) — the one thing that could force a small
  code change.
- **`load-parquet` transaction size** — it commits once per installation; Harvard's
  ~300k rows is the biggest single transaction. If it strains the Silk MySQL, lower
  the chunk size in `backend/db/upsert.py` (`_CHUNK`, currently 2000) or split the
  ingest.
- **Deleted upstream records** — incremental never removes rows; stale datasets
  accumulate. Tracked as a future project (`is_active` column + reconcile sweep),
  see `CONTEXT.md`.
- **Two DATABASE_URLs** — laptop (tunnel) vs Silk (localhost). Same database, but
  don't run the pull from Silk against the tunnel value or vice versa.
