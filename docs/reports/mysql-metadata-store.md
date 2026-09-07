# Implementation report: MySQL metadata store

Plan: `docs/plans/active/2026-09-07-mysql-metadata-store.md`
Design: `CONTEXT.md`, `docs/adr/0001-mysql-on-silk-for-metadata-store.md`

Replaces the flat `metadata.csv`/`.parquet` (+ `dataverses.csv`, `installations.geojson`)
with a normalised MySQL store, loads the existing parquet as the initial data, and
keeps the per-installation incremental pull (changing only its sink).

## Implemented

- **`backend/db/`** (new): SQLAlchemy 2.0 layer, no Flask-SQLAlchemy.
  - `models.py` — normalised schema: `installation`, `dataverse`, `dataset`; shared
    lookups `author` / `keyword` / `subject` / `publication` with junctions
    (`dataset_author` carries `ordinal`); flat parent-keyed child tables
    (`dataset_contact` / `_producer` / `_related_material` / `_data_source` /
    `_geographic_coverage` / `_publication_status`); `pull_state`. Surrogate
    `BigInteger` PKs (`with_variant(Integer, "sqlite")` for the test DB), composite
    unique natural keys, `is_active` server-default, nullable soft-FK `dataverse_id`,
    composite-unique string parts capped ≤191 chars for the MySQL index limit.
  - `__init__.py` — lazy `get_engine()` / `get_session()` from `DATABASE_URL` (so the
    Flask app still boots without a DB).
  - `upsert.py` — dialect-agnostic `upsert_rows` (MySQL `ON DUPLICATE KEY UPDATE` /
    SQLite `ON CONFLICT`), `get_or_create_lookup_ids`, `replace_child_rows`.
  - `schema_init.py` — `create_all()`.
- **`backend/services/`** (new): `mapping.py` (pure Record→rows: `parse_scalar` /
  `parse_int` / `parse_dt` tolerating `1000-12-26`/`"nan"`/empty / `parse_list`
  handling real lists, numpy arrays from parquet, `repr`-strings, nullish / `norm`;
  `map_dataverse_item`, `map_dataset_item` with `natural_key = global_id or identifier`);
  `ingest.py` (`ingest_installation` — one transaction per installation, shared by the
  loader and the live pull); `loader.py` (`load_parquet_dump` — groups the parquet by
  installation, ingests, seeds `pull_state` to max `published_at` **except** where the
  row count hit `dump_page_limit * per_page`, which is left un-watermarked).
- **`backend/services/metadata.py`**: sink swapped from CSV/parquet to
  `_upsert_to_db(dfs)`; `_load_state` reads `pull_state`, `_advance_watermarks`
  replaces the JSON write (only completed installations advance — unchanged rule);
  `_get_urls` reads the `installation` table, falls back to `installations.csv` when
  empty; `--no-save` skips DB writes + watermark advance; added
  `Metadata.export_parquet(path)`. Server-side `fq=dateSort` filtering,
  `_split_at_watermark`, one-shot full-pull fallback, retry/backoff and PARTIAL
  handling all untouched.
- **`backend/services/installations.py`**: `call(export_files=False)` upserts via new
  `save_db(df)` into the `installation` table; CSV/GeoJSON only when
  `export_files=True`.
- **`backend/services/orchestrator.py`**: `--cmd init-db`, `--cmd load-parquet`,
  `--export-parquet PATH`, `--dump-page-limit`.
- **`backend/routes/data.py`**: all four data routes query MySQL via `pd.read_sql`
  (same response JSON); `/api/installations` builds the GeoJSON `FeatureCollection`
  from a `SELECT`; `/api/dataverses` self-joins for `parentDataverseName`. Imports
  `backend.db` (Flask loads `api` as `backend.api`).
- **`backend/pyproject.toml`**: `+sqlalchemy==2.0.36`, `+pymysql==1.1.1`.
  **`backend/.env`**: commented `DATABASE_URL` template.
- **`AGENTS.md`, `backend/README.md`**: architecture, DB setup / SSH tunnel,
  first-time-load order, `pull_state` replaces `last_pull.json`.
- **Tests**: `tests/test_mapping.py` (parsing + item mappers); `tests/test_upsert_idempotency.py`
  (ingest a mixed batch twice on in-memory SQLite — counts stable, lookups reused,
  soft FK resolved, changed field updated); `tests/test_installations.py` updated for
  the new `call()` contract.

## Checks run

- `cd backend && uv run pytest -q` — **23 passed**.
- End-to-end smoke on SQLite (`DATABASE_URL=sqlite:///…`): `init-db` →
  `Installation.save_db` → `load_parquet_dump` twice (idempotent) → correct row counts
  (author/keyword dedup across datasets, soft FK resolved, watermark = max
  `published_at`, capped-installation guard) → all four Flask routes 200 with expected
  shapes → `export_parquet` writes a flat dump. Run with both the real-`list` field
  shape (live pull) and the `repr`-string shape (real parquet dump).
- `uvx ruff check` — 58 repo-wide (was 59); new files add only `I001` import-ordering,
  which the repo doesn't enforce. `DTZ005` hits in `metadata.py` are pre-existing
  `datetime.now()` timing lines.
- `uv run flask --app api routes` — app imports, routes registered.

## Remaining / deviations

- **Live-MySQL steps not run** (need Silk credentials + `ssh -L 3306:localhost:3306`):
  real `init-db` (confirm 18 tables + index lengths accepted), `installations`,
  `load-parquet` (expect `dataverse` ≈ 20,279, `dataset` ≈ 521,451, no `pull_state`
  row for `dataverse.harvard.edu`), incremental double-run sanity check, `./run.sh`
  dashboard JSON diff, and one uncapped `--cmd metadata` pull for Harvard + the ~15
  other capped installations + the 42 absent from the parquet. Then delete the legacy
  `data/metadata/*` and `data/dataverses.csv` and move the plan to `done/`.
- `--export-parquet` dumps `SELECT * FROM dataverse` + `dataset` (core entities only),
  not a full denormalised 16-table join — lazy version of the plan's export helper.
- `routes/data.py` imports `backend.db`, not `db` — the repo already splits import
  roots (`services/`/`pipeline/` use `backend/` on `sys.path`; Flask loads
  `backend.api`). Documented in a comment and `AGENTS.md` rather than adding a third
  convention.
- Loader reads only `metadata.parquet` (its 20,279 `type=="dataverse"` rows are in the
  API column shape) and ignores `dataverses.csv` — one code path instead of two.
- `BigInteger` PKs use `with_variant(Integer, "sqlite")` — needed for autoincrement in
  the test DB; MySQL still gets `BIGINT`. Not in the plan.
- `backend/pipeline/**` (Dagster) untouched — inherits MySQL writes via the service
  methods; `installation_geojson` asset is now redundant with the route.
