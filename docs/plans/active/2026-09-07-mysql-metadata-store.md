# MySQL metadata store — replace flat files, load existing data, keep incremental

## Goal

Move harvested Dataverse metadata off flat `metadata.csv`/`.parquet` (+ `dataverses.csv`,
`installations.geojson`) into **MySQL on Silk**, accessed via **SQLAlchemy 2.0**. Load the
existing `metadata.parquet` as the initial data (no full re-pull). Keep the existing
per-installation incremental pull, changing only its sink from files to database upserts.
Migrate the Flask read routes to query MySQL, response shapes unchanged.

Design settled via `/grill-with-docs`. See:
- `CONTEXT.md` — domain glossary (Installation, Dataverse, Dataset, Record, Watermark,
  Full/Incremental pull, Capped installation, Orphan reference, Lookup dedup, Canonical
  resolution, Reconcile).
- `docs/adr/0001-mysql-on-silk-for-metadata-store.md` — why MySQL-on-Silk over embedded
  DuckDB artifact / hosted analytical DB / migrating hosting.

## Current architecture / relevant findings

### Pull (`backend/services/metadata.py`)
- `Metadata` class. `_pull_combine_save()` runs `asyncio.run(self._fetch())`, concatenates
  per-installation DataFrames, then **unconditionally writes** `data/metadata/metadata.csv`
  + `.parquet` (and, with `incremental=True`, reads the existing CSV, `pd.concat`s, dedupes
  on `COALESCE(global_id, identifier) + installation_url` keeping latest `published_at`).
- Incremental machinery already exists and is **kept as-is** — only the sink changes:
  - watermark store: `data/state/last_pull.json` (`{installation_url: iso_ts}`) via
    `_load_state`/`_save_state`. → moves to a `pull_state` table.
  - `_request_metadata()` adds `&sort=date&order=desc&fq=dateSort:[{since} TO *]` when a
    watermark exists; `_split_at_watermark()` trims each page and stops at the first
    older item.
  - one-shot fallback to a full `q=*` pull if the filtered query fails structurally / HTTP
    / JSON.
  - `_get_page()` retries 429/5xx with backoff (honors `Retry-After`); exhausted retries
    return partial results flagged `complete=False`.
  - `_pull_combine_save()` computes `successful_urls = fetched ∩ complete_urls` and only
    advances the watermark for those — a PARTIAL pull's watermark is not advanced.
- Nested fields in the DataFrame are Python lists; `.astype(str)` is applied before parquet
  write, so on disk they are repr strings (`"['Economic Behaviour', 'Income']"`).
- `_get_urls()`: `url_list="installations"` (default) reads
  `data/installations/installations.csv`; otherwise a passed list.

### Existing parquet (`backend/data/metadata/metadata.parquet`, gitignored)
- 541,730 rows, 37 cols. 88 installations present (42 of ~130 returned nothing).
  521,451 `dataset` + 20,279 `dataverse`.
- **Harvard capped at exactly 300,000** (page_limit 300 × per_page 1000) vs a real
  total_count of 5,796,761. 16 installations sit at `count > 2000`; the cap signal is
  `count >= page_limit * per_page`.
- `published_at` contains junk (`min = 1000-12-26T00:00:00Z`).
- Author cells are bare name strings — the Search API returns no affiliation/ORCID.

### Installations (`backend/services/installations.py`)
- `Installation` fetches IQSS `data.json`, appends a hardcoded UVM dict, writes
  `data/installations/installations.csv` + `installations.geojson`.
- `installations.csv` is what `metadata.py` reads for URLs. `installations.geojson` is what
  `/api/installations` serves.
- `.call()` is referenced by the orchestrator but note: current `Installation` has no
  `call()` in some earlier states — verify; `pipeline/assets.py` calls `get_raw` / `process`
  / `save_geojson` granularly.

### Serve (`backend/routes/data.py`)
- Flask blueprint. Every route does `pd.read_csv(...)` / opens a file per request:
  - `/api/items` — dummy static list.
  - `/api/installations` — reads `data/installations/installations.geojson`, returns it
    (with a `": NaN" -> ": null"` string patch).
  - `/api/dataverses` — `data/dataverses.csv` → records JSON. **Nothing currently writes
    `dataverses.csv`** (pre-existing breakage).
  - `/api/datasets-by-installation` — `dataverses.csv` grouped `installation → sum(datasetCount)`,
    `nlargest(12)`.
  - `/api/installations-by-country` — `installations.csv` `country` value counts.
- Routes run CWD-relative paths; Flask must run from `backend/` (`run.sh`).
- No route reads `metadata.parquet` today.

### Frontend (unchanged by this plan)
- `frontend/src/routes/+page.server.ts` fetches `/api/installations`,
  `/api/datasets-by-installation`, `/api/installations-by-country`.
- `frontend/src/routes/detail/+page.server.ts` fetches `/api/dataverses` (ag-grid table).
- Response JSON shapes must stay identical.

### Entry points
- `backend/services/orchestrator.py` — argparse CLI (`--cmd installations|metadata|sizes|all`),
  passes flags straight to `Metadata(...)`. **This owns all writes going forward.**
- `backend/pipeline/` — Dagster; assets are thin wrappers over `services/`. **Left alone
  this effort** (inherits DB writes through the service methods).

### Deps / config
- `backend/pyproject.toml` — uv-managed, `requires-python >=3.12`. Has `pandas`, `pyarrow`,
  `fastparquet`, `flask`, `dagster`, `python-dotenv`, `pytest`. **No SQLAlchemy, no MySQL
  driver.** `[tool.pytest.ini_options] pythonpath = ["."]` already set.
- `backend/requirements.txt` is empty.
- `.env` gitignored and empty. `backend/.env` exists.
- `.gitignore` already ignores `backend/data/metadata/*`, `backend/data/state/`, `.env`.

## Proposed approach

### 1. Dependencies + config
- Add to `backend/pyproject.toml`: `sqlalchemy>=2.0`, `pymysql`. Keep `pandas`/`pyarrow`
  (loader + `--export-parquet` still use them). `uv sync`.
- `backend/.env`: `DATABASE_URL=mysql+pymysql://<user>:<pass>@127.0.0.1:3306/<db>`.
  Same value on the laptop (pointed at the SSH tunnel) and on Silk (localhost MySQL).
- SSH tunnel doc in `backend/README.md`: `ssh -L 3306:localhost:3306 <silk-host>` before
  running any pull from the laptop.

### 2. DB layer — `backend/db/` (new package)
- `backend/db/__init__.py` — `engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)`,
  `SessionLocal = sessionmaker(engine)`, `@contextmanager get_session()`. No Flask-SQLAlchemy.
- `backend/db/models.py` — SQLAlchemy 2.0 `DeclarativeBase`, typed `Mapped[]`:

  | table | key columns | unique |
  |---|---|---|
  | `installation` | id, hostname, url, name, description, lat, lng, country, launch_year, doi_authority, dv_hub_id | `url` |
  | `dataverse` | id, installation_id→installation, identifier, name, description, published_at, affiliation, parent_dataverse_identifier, image_url, dataset_count, is_active(=1) | `(installation_id, identifier)` |
  | `dataset` | id, installation_id→installation, dataverse_id→dataverse NULL, parent_dataverse_identifier, global_id, identifier, natural_key, name, description, published_at, created_at, updated_at, publisher, citation, citation_html, storage_identifier, file_count, version_id, version_state, major_version, minor_version, is_active(=1) | `(installation_id, natural_key)` |
  | `author` | id, name, affiliation NULL, identifier NULL, name_norm, affiliation_norm | `(name_norm, affiliation_norm, identifier)` |
  | `keyword` | id, term, term_norm | `term_norm` |
  | `subject` | id, term | `term` |
  | `publication` | id, citation, url, id_type, id_number, citation_norm | `(url, id_number, citation_norm)` |
  | `dataset_author` | dataset_id, author_id, ordinal | PK `(dataset_id, author_id)` |
  | `dataset_keyword` | dataset_id, keyword_id | PK `(dataset_id, keyword_id)` |
  | `dataset_subject` | dataset_id, subject_id | PK `(dataset_id, subject_id)` |
  | `dataset_publication` | dataset_id, publication_id | PK `(dataset_id, publication_id)` |
  | `dataset_contact` | id, dataset_id, name, affiliation | — |
  | `dataset_producer` | id, dataset_id, name, affiliation | — |
  | `dataset_related_material` | id, dataset_id, text | — |
  | `dataset_data_source` | id, dataset_id, text | — |
  | `dataset_geographic_coverage` | id, dataset_id, coverage | — |
  | `dataset_publication_status` | id, dataset_id, status | — |
  | `pull_state` | installation_id (PK), last_pulled_at | — |

  - All entity tables: surrogate `id BIGINT AUTO_INCREMENT` PK.
  - `dataset.natural_key` = `COALESCE(global_id, identifier)`, populated in Python before
    insert (not a generated column — keep it portable/simple).
  - `*_norm` columns = lowercased/trimmed, populated in Python.
  - Datetimes: `DateTime`, nullable; unparseable input → `None`.
  - Soft FKs: `parent_dataverse_identifier` always stored; `dataverse_id` resolved when a
    matching `(installation_id, identifier)` exists, else `NULL`.
  - Indexes: every FK column, junction PKs cover their own lookups, plus
    `installation.country`, `dataset.published_at`, `dataverse.published_at`.
- `backend/db/upsert.py` — helpers built on
  `sqlalchemy.dialects.mysql.insert(Table).values(rows).on_duplicate_key_update(...)`:
  - `upsert_rows(conn, table, rows, update_cols)` — bulk, chunked (~5k/stmt).
  - `get_or_create_lookup_ids(conn, table, norm_key_cols, rows)` — upsert lookup rows, then
    `SELECT` back the ids keyed by the norm tuple. Used for author/keyword/subject/publication.
- `backend/db/schema_init.py` — `Base.metadata.create_all(engine)`. Alembic deferred to
  first post-deploy schema change.

### 3. Record → rows mapper — `backend/services/mapping.py` (new)
- Pure functions, no I/O, unit-testable:
  - `parse_list(cell) -> list` — accepts a real list, a `repr`-string list (`ast.literal_eval`
    with a safe fallback to `[]`), `None`/`nan` → `[]`.
  - `parse_dt(value) -> datetime | None` — tolerates `1000-12-26...`, empty, `nan`.
  - `norm(s) -> str` — lowercase/strip for `*_norm`.
  - `map_dataverse_item(item, installation_id) -> dict` (row for `dataverse`).
  - `map_dataset_item(item, installation_id) -> (dataset_row, {authors, keywords, subjects,
    publications, contacts, producers, related_material, data_sources,
    geographic_coverage, publication_statuses})`.
- One code path shared by the loader (step 4) and the live pull (step 5): both hand raw
  Search-API-shaped dicts to these mappers. The parquet loader reconstructs dicts from
  parquet columns first (`parse_list` on the stringified nested columns).

### 4. Initial load — `orchestrator --cmd load-parquet`
- New function `load_parquet_dump()` (in `services/metadata.py` or a small
  `services/loader.py`):
  1. Ensure installations exist: run the installations refresh (step 6) first, or load from
     `data/installations/installations.csv` if present, into `installation`.
  2. `pd.read_parquet("data/metadata/metadata.parquet")` + `pd.read_csv("data/dataverses.csv")`.
  3. Group rows by `installation_url` → resolve `installation_id`.
  4. Per installation: split `type == "dataverse"` vs `"dataset"`; run mappers; bulk-upsert
     `dataverse`, then `dataset`, then resolve `dataset.dataverse_id` from
     `parent_dataverse_identifier`, then lookups + junctions + flat child tables.
  5. Delete-and-reinsert child/junction rows for each dataset touched (simplest correct
     upsert for 1-to-many) — scoped to the `dataset_id`s in the batch.
  6. **Watermark seed**: for each installation, `count = len(rows)`;
     `capped = count >= (page_limit * per_page)` (use the values that produced the dump —
     default 300 × 1000; make it a CLI arg `--dump-page-limit`, default 300).
     If not capped: `pull_state.last_pulled_at = max(parse_dt(published_at))`.
     If capped: **no `pull_state` row** → next incremental run does a full pull for it.
  7. Installations absent from the parquet get no `pull_state` row automatically.
- Idempotent: re-running upserts the same rows, child-table delete+reinsert converges.

### 5. Live pull sink swap — `backend/services/metadata.py`
- Replace the file-writing tail of `_pull_combine_save()` with `_upsert_to_db()`:
  - Instead of concatenating to one DataFrame and writing CSV/parquet, iterate the
    per-installation results; for each `successful`/`partial` installation open one
    transaction and run the same step-4.4 upsert sequence via `db/upsert.py`.
  - Drop the `pd.read_csv(existing) + concat + drop_duplicates` block entirely — the DB
    unique keys + `on_duplicate_key_update` do the dedupe.
- Replace `_load_state`/`_save_state` (JSON) with reads/writes of `pull_state`
  (`installation_id` resolved from `installation.url`). Keep the exact rule: only
  `successful_urls` (fetched ∩ complete) advance `last_pulled_at`, set to current UTC.
- `--no-save` semantics: skip the DB writes and the watermark update (log one line), same
  as today.
- New `--export-parquet PATH` flag: after a pull (or standalone), run one denormalised
  `SELECT` join and `to_parquet(PATH)`. Opt-in; not part of the normal pipeline.
- `_get_urls()` "installations" branch: read from the `installation` table instead of
  `installations.csv` (fallback to the CSV if the table is empty, to keep first-run
  bootstrapping simple).

### 6. Installations sink swap — `backend/services/installations.py`
- Add `save_db(df)` — upsert into `installation` (unique on `url`).
- `call()` (or the orchestrator `installations` branch): fetch → process → `save_db`.
- Keep `save_geojson`/`save_csv` as **opt-in** exports (or drop `save_csv` once
  `_get_urls()` reads the table). Decide during implementation; default to keeping them
  callable but not called by the pipeline.

### 7. Flask read routes — `backend/routes/data.py`
- Module-level `from backend.db import get_session` (or a shared `engine`); one session per
  request via a helper / `teardown_appcontext`.
- Rewrite each route as SQL, **same response JSON**:
  - `/api/installations` — `SELECT` all `installation` rows, assemble the GeoJSON
    `FeatureCollection` (`geometry.coordinates = [lng, lat]`, `properties` = the columns the
    current geojson exposes).
  - `/api/dataverses` — `SELECT` from `dataverse` (join `installation` for `installation`
    name + url), shaped to the columns the detail ag-grid expects (`name, type, url,
    identifier, publishedAt, installation, installationUrl, imageUrl, affiliation,
    parentDataverseName, parentDataverseIdentifier, datasetCount`). `type` is the constant
    `"dataverse"`.
  - `/api/datasets-by-installation` — `SELECT i.name/key, SUM(dv.dataset_count) ... GROUP BY
    ... ORDER BY 2 DESC LIMIT 12` (or `COUNT(dataset.id)` grouped by installation — pick to
    match current meaning: current code sums `datasetCount` from `dataverses.csv`, so keep
    `SUM(dataverse.dataset_count)`).
  - `/api/installations-by-country` — `SELECT country, COUNT(*) FROM installation GROUP BY
    country ORDER BY 2 DESC`.
  - `/api/items` — leave as-is or delete (dummy; out of scope).
- `frontend/` untouched.

### 8. Cleanup / docs
- Stop writing `metadata.csv`/`.parquet`, `dataverses.csv`, `installations.geojson` from
  the pipeline.
- `.gitignore`: the metadata dir is already ignored; add `backend/data/*.parquet` export
  location if it lands elsewhere.
- Update `AGENTS.md` ("No database" line, the flat-file bullets) and `backend/README.md`
  (tunnel setup, `--cmd load-parquet`, `--export-parquet`, `pull_state` replaces
  `last_pull.json`).

## Files to add/change

**Add**
- `backend/db/__init__.py`, `backend/db/models.py`, `backend/db/upsert.py`,
  `backend/db/schema_init.py`
- `backend/services/mapping.py`
- `backend/services/loader.py` (or `load_parquet_dump()` inside `metadata.py`)
- `backend/tests/test_mapping.py`, `backend/tests/test_upsert_idempotency.py`
- `docs/plans/active/2026-09-07-mysql-metadata-store.md` (this file)
- `CONTEXT.md`, `docs/adr/0001-mysql-on-silk-for-metadata-store.md` (already written)

**Change**
- `backend/pyproject.toml` — add `sqlalchemy`, `pymysql`
- `backend/.env` — `DATABASE_URL`
- `backend/services/metadata.py` — sink swap, `pull_state`, `--export-parquet`,
  `_get_urls` from table
- `backend/services/installations.py` — `save_db`
- `backend/services/orchestrator.py` — `--cmd init-db`, `--cmd load-parquet`,
  `--export-parquet`, `--dump-page-limit`
- `backend/routes/data.py` — all routes to SQL
- `AGENTS.md`, `backend/README.md`

**Not touched**
- `backend/pipeline/**` (Dagster), `frontend/**`, `.dev/**`

## Implementation steps

1. Deps (`sqlalchemy`, `pymysql`), `uv sync`, `backend/.env` `DATABASE_URL`, tunnel note in
   `backend/README.md`.
2. `backend/db/models.py` + `db/__init__.py` + `db/schema_init.py`; wire
   `orchestrator --cmd init-db` → `create_all`. Run against Silk MySQL over the tunnel;
   confirm all tables created.
3. `backend/services/mapping.py` (`parse_list`, `parse_dt`, `norm`, `map_dataverse_item`,
   `map_dataset_item`) + `backend/tests/test_mapping.py`.
4. `backend/db/upsert.py` (`upsert_rows`, `get_or_create_lookup_ids`) +
   `backend/tests/test_upsert_idempotency.py`.
5. `orchestrator --cmd load-parquet` (loader): installations first, then dataverses, then
   datasets, then FK resolution, then lookups/junctions/child tables, then watermark seed
   with the cap guard. Run it; spot-check row counts vs the parquet
   (`dataverse` ≈ 20,279, `dataset` ≈ 521,451, `pull_state` has no Harvard row).
6. Swap `services/installations.py` to `save_db`; wire the orchestrator `installations`
   branch.
7. Swap `services/metadata.py` sink to DB upsert; replace JSON watermark with `pull_state`;
   `_get_urls` reads the table; add `--export-parquet`. Run
   `--cmd metadata --incremental --url-list <one small installation> --page-limit 1` twice;
   second run adds ~0 rows.
8. Rewrite `routes/data.py` routes as SQL; run `./run.sh`, load the dashboard + `/detail`,
   diff the JSON against a pre-change capture.
9. Run one uncapped incremental for the capped + missing installations
   (`--cmd metadata --incremental --page-limit 6000 --timeout 300 --page-delay 0.5`, or
   per-installation for Harvard). Long-running; unattended.
10. Remove flat-file writes; update `AGENTS.md` + `backend/README.md`; move this plan to
    `docs/plans/done/`.

## Testing strategy

- `cd backend && uv run pytest -q`:
  - `test_mapping.py` — `parse_list` on real list / repr-string / `nan` / `None`;
    `parse_dt` on `1000-12-26...` / `""` / valid; `map_dataset_item` produces the expected
    row + child dict from a sample Search API item; `natural_key` falls back
    `global_id → identifier`.
  - `test_upsert_idempotency.py` — against **SQLite in-memory** (`create_all` on the same
    metadata; `on_duplicate_key_update` path guarded so the test uses
    `sqlite_on_conflict` / a dialect-agnostic upsert helper, OR mark MySQL-only and skip
    without a DB): insert a batch of dataset rows + children twice → identical row counts,
    no duplicate-key errors, child rows not multiplied.
- Manual (documented, hits live services / real MySQL):
  - `--cmd load-parquet` then `SELECT COUNT(*)` per table vs parquet expectations.
  - Incremental double-run on one small installation → ~0 new rows; check
    `logs/metadata_fetch.log` for the fallback path.
  - `./run.sh`, compare `/api/*` JSON before/after.
- No MySQL fixture framework, no per-function suites (ponytail: one runnable check per
  non-trivial unit).

## Risks and open questions

- **Credentials / connectivity unverified**: need the Silk MySQL user, password, db name,
  and confirmation that its MySQL is reachable through an SSH tunnel (localhost-only is
  fine; remote-open is not required). Blocks steps 2+.
- **`--dump-page-limit` assumption**: the on-disk parquet's cap is inferred as 300×1000
  from Harvard's exact 300,000. If the dump was actually produced with a different
  `--page-limit`, the cap guard misclassifies installations. Mitigation: CLI arg with a
  sane default; the step-9 uncapped run repairs any missed installation anyway.
- **Watermark backfill gap for capped installations**: by design they get a full pull on
  the next run (step 9), which is the hours-long Harvard pull. Acceptable per ADR-0001;
  "Reconcile" (deletion sweep) remains a separate future project.
- **`on_duplicate_key_update` is MySQL-dialect-specific** — the idempotency test can't run
  it on SQLite unchanged. Either write a tiny dialect-agnostic upsert wrapper or gate that
  test on a `DATABASE_URL` being set. Prefer the wrapper.
- **Child-table upsert = delete-then-reinsert per touched dataset**: simple and correct,
  but churns auto-increment ids and writes more rows than a diff. Fine at incremental
  volumes; revisit only if a pull's child-table write time becomes a problem.
- **Author data is name-only** from the Search API — `author.affiliation`/`identifier` stay
  NULL. Columns exist for a future native-API enrichment project; not in scope.
- **`Installation.call()`** may not exist in the current code (orchestrator references it;
  `pipeline/assets.py` calls granular methods). Verify and reconcile when doing step 6.
- **`dataverses.csv` currently unwritten** — the loader depends on it existing for the
  initial load's dataverse rows. If it's stale/absent, the `type=="dataverse"` rows in
  `metadata.parquet` (20,279 of them) are the real source; prefer those and treat
  `dataverses.csv` as optional supplementary.
- **Dagster drift**: `pipeline/assets.py` still calls `Installation().save_geojson()` etc.;
  after the sink swap those assets write nothing useful. Left alone per scope, but flag in
  `AGENTS.md` so it isn't mistaken for the live path.
