# Project

Databoard is a work-in-progress dashboard for exploring dataset and installation metadata from the [Dataverse Project](https://dataverse.org/) (an open-source research data repository platform). It pulls data from Dataverse APIs, serves it via a Flask API, and renders it as a map/chart dashboard in SvelteKit.

## Architecture

- `backend/api.py` — Flask app entry point (`flask --app api run`). `backend/routes/data.py` — API routes that query MySQL (via `backend/db/`) and return JSON. Routes are prefixed `/databoard` when `ENV=development`.
- `backend/db/` — SQLAlchemy 2.0 layer: `models.py` (normalised schema), `__init__.py` (`get_engine`/`get_session` from `DATABASE_URL`), `upsert.py` (dialect-agnostic bulk upserts), `schema_init.py` (`create_all`). No Flask-SQLAlchemy. Note the import split: `services/` and `pipeline/` run with `backend/` on `sys.path` and import `db`; `api.py` is loaded by Flask as `backend.api`, so `routes/data.py` imports `backend.db`.
- `backend/services/` — business logic. `installations.py`/`metadata.py` fetch from Dataverse APIs; `mapping.py` (pure Record→rows), `ingest.py` (per-installation upsert into the normalised schema, shared by loader + live pull), `loader.py` (one-time parquet→MySQL initial load).
- `backend/pipeline/` — Dagster project (run with `dg dev` from `backend/`). Thin wrappers over `services/`; inherits the MySQL writes through those service methods. `installation_geojson` asset is now redundant with the `/api/installations` route building GeoJSON from the table.
- `backend/services/orchestrator.py` — the actively-used CLI and the owner of all DB writes: `--cmd init-db | load-parquet | installations | metadata | sizes | all`, plus `--export-parquet PATH`.
- Persistence is **MySQL** (on Silk; laptop writes over an SSH tunnel — see ADR-0001 and `backend/README.md`). The per-installation harvest watermark lives in the `pull_state` table (replaced `data/state/last_pull.json`). The `requests_cache`/`aiohttp_client_cache` sqlite files are just HTTP response caches. Flat files under `backend/data/` are legacy inputs only (`installations.csv` is a fallback URL source; `metadata.parquet` feeds `load-parquet`); the pipeline no longer writes them.
- `frontend/` — SvelteKit (Svelte 5). `+page.server.ts` fetches server-side from Flask via `FLASK_URL` (default `http://localhost:5000/databoard`); `+page.svelte` renders `Map.svelte` (svelte-maplibre) and `BarChart.svelte` (chart.js); `detail/` route uses ag-grid for tabular data. Styled with Tailwind v4 + daisyui.

## Rules

- Flask still runs from `backend/` (use `run.sh`, or `cd backend` first) — the `installations.csv` fallback path and `load-parquet` input are CWD-relative.
- `backend/.env` must define `DATABASE_URL` (`mysql+pymysql://user:pass@127.0.0.1:3306/databoard`). On a laptop this points at an SSH tunnel to Silk's MySQL; on Silk, localhost. `db.get_engine()` is lazy, so the Flask app still boots without it (routes 500 until it's set).
- Dagster asset logic belongs in `backend/services/`, not inline in `backend/pipeline/assets.py` — keep assets as thin wrappers calling service classes.
- Don't assume the Dagster pipeline replaces the orchestrator CLI — it currently only covers a subset (hardcoded UVM-only metadata asset vs. the orchestrator's configurable installation list, page limits, and timeouts).
- `.dev/` is disowned WIP/scratch code, not part of the real system — don't build on it without checking with the user first.

## Commands

```sh
cd backend && uv sync          # install backend deps
cd frontend && npm install     # install frontend deps
./run.sh                       # run both dev servers (Flask :5000, Vite :5173)
cd backend && dg dev           # run Dagster dev UI/pipeline
uvx ruff check                 # lint/format backend (Python)
cd frontend && npm run lint    # lint frontend
cd frontend && npm run format  # format frontend
```

## Testing

- Frontend: `cd frontend && npm run test` (runs `test:unit` via vitest and `test:e2e` via playwright). Run a single test with the usual vitest/playwright CLI args.
- Backend: `cd backend && uv run pytest -q`. Covers `services/mapping.py` (Record→rows parsing) and `services/ingest.py` idempotency (against in-memory SQLite; the upsert layer branches on dialect), plus `services/installations.py`. No MySQL fixture — DB-integration checks are manual (see `backend/README.md`).

## Agent skills

### Issue tracker

Issues live in GitHub Issues (ChrisDonovan307/databoard), managed via `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Gotchas

- `backend/.tmp_dagster_home_*/` (untracked) is a Dagster ephemeral instance directory, created because `DAGSTER_HOME` isn't set and `backend/pipeline/dagster.yaml` is empty. It's a harmless local artifact, but `.gitignore` doesn't currently match this path (only `backend/pipeline/*` is ignored) — worth adding.
- `backend/.env` needs `DATABASE_URL` (see Rules); `ENV=development` controls the `/databoard` route prefix.
- Two overlapping data-refresh entry points exist (orchestrator CLI vs. Dagster pipeline) — the CLI owns DB writes; Dagster is left in place but not the primary path.
- First-time setup order: `--cmd init-db` → `--cmd installations` → `--cmd load-parquet` (seeds from `backend/data/metadata/metadata.parquet`, which is gitignored) → `--cmd metadata --incremental` for ongoing updates. Capped/missing installations (Harvard etc.) need one uncapped `--cmd metadata` run.
