# Project

Databoard is a work-in-progress dashboard for exploring dataset and installation metadata from the [Dataverse Project](https://dataverse.org/) (an open-source research data repository platform). It pulls data from Dataverse APIs, serves it via a Flask API, and renders it as a map/chart dashboard in SvelteKit.

## Architecture

- `backend/api.py` — Flask app entry point (`flask --app api run`). `backend/routes/data.py` — API routes that read flat files under `backend/data/` (CSV/GeoJSON) and return JSON. Routes are prefixed `/databoard` when `ENV=development`.
- `backend/services/` — actual business logic (`installations.py`, `metadata.py`) that fetches from Dataverse APIs and writes to `backend/data/`.
- `backend/pipeline/` — Dagster project (run with `dg dev` from `backend/`). `assets.py` defines `raw_installations` → `clean_installations` → `installation_geojson`, plus `uvm_meta_datasets`; `definitions.py` wires them into the `refresh_all` job. Assets are thin wrappers that call into `services/`.
- `backend/services/orchestrator.py` — an older, more complete CLI (`python -m services.orchestrator --cmd all|installations|metadata`) that overlaps with the Dagster pipeline; not yet fully superseded (see Gotchas).
- No database — persistence is flat files in `backend/data/` (`dataverses.csv`, `installations/installations.geojson`, `metadata/metadata.csv|parquet`). The `requests_cache`/`aiohttp_client_cache` sqlite files are just HTTP response caches, not application data.
- `frontend/` — SvelteKit (Svelte 5). `+page.server.ts` fetches server-side from Flask via `FLASK_URL` (default `http://localhost:5000/databoard`); `+page.svelte` renders `Map.svelte` (svelte-maplibre) and `BarChart.svelte` (chart.js); `detail/` route uses ag-grid for tabular data. Styled with Tailwind v4 + daisyui.

## Rules

- Flask routes read data files via CWD-relative paths (e.g. `"data/dataverses.csv"`) — always run Flask from `backend/` (use `run.sh`, or `cd backend` first).
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
- Backend: no real test suite exists yet. `pytest` is a listed dependency but unused — the only test file (`.dev/test_installations.py`) lives in disowned scratch code, not the real codebase.

## Agent skills

### Issue tracker

Issues live in GitHub Issues (ChrisDonovan307/databoard), managed via `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Gotchas

- `backend/.tmp_dagster_home_*/` (untracked) is a Dagster ephemeral instance directory, created because `DAGSTER_HOME` isn't set and `backend/pipeline/dagster.yaml` is empty. It's a harmless local artifact, but `.gitignore` doesn't currently match this path (only `backend/pipeline/*` is ignored) — worth adding.
- `.env` exists but is empty. `ENV=development` controls whether Flask serves routes under the `/databoard` prefix.
- Two overlapping data-refresh entry points exist (orchestrator CLI vs. Dagster pipeline) — see Rules above.
- Generated data files under `backend/data/metadata/` are gitignored and must be produced locally by running the pipeline or orchestrator before the app has real metadata to serve.
