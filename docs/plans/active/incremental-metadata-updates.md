# Incremental metadata updates for Dataverse pull

## Goal

`Metadata._pull_combine_save()` always does a full `q=*` Dataverse Search API pull across every installation and overwrites `data/metadata/metadata.csv`/`.parquet` from scratch every run. Add an "update" path that remembers the last successful pull timestamp per installation and, on request, only fetches items newer than that watermark, appending/deduping into the existing files instead of re-pulling and overwriting everything.

Decided with user:
- Entry point: `backend/services/orchestrator.py` (the actively-used CLI), not the Dagster pipeline.
- Filter strategy: server-side date filter against the Dataverse Search API, with a fallback to a full pull if that doesn't behave as expected on a given installation (behavior may vary across Dataverse versions/installations — unverified against live servers).

## Current architecture / relevant findings

- `backend/services/metadata.py` — `Metadata` class:
  - `_get_urls()` (line 70): default `url_list="installations"` reads URLs from `data/installations/installations.csv`.
  - `_pull_combine_save()` (line 89): calls `asyncio.run(self._fetch())`, combines the returned `dfs` dict into one DataFrame, and unconditionally overwrites `data/metadata/metadata.csv`/`.parquet` (lines 134-150). No append/merge logic exists anywhere today.
  - `_fetch()` (line 152): builds a shared `aiohttp_client_cache.CachedSession` (SQLite, 1hr TTL — an HTTP response cache only, not usable as pull-state), fires one `_request_metadata` task per URL via `asyncio.gather`, and splits results into `dfs` (success, keyed by `url_to_name(url)`, with `installation_url` column stamped onto each row) and `failures` (logged to `logs/failed_installations.csv`, overwritten each run). This success/failure split is exactly the granularity needed to know which installations to advance a watermark for.
  - `_request_metadata()` (line 209): hits `{base}/api/search?q=*&type=dataverse&type=dataset&start={start}&per_page={per_page}`, paginating by `per_page` until `start >= total_count` or `page > page_limit` (default 2). No date filtering exists; always starts at `start=0`.
- `backend/services/orchestrator.py` — CLI (`python -m services.orchestrator --cmd installations|metadata|all`), argparse-based, passes `--start`, `--per-page`, `--page-limit`, `--url-list`, `--no-save`, `--timeout`, `--file-type` straight through to `Metadata(...)`. Boolean flags follow the `--no-save` pattern (`action="store_true"`).
- No state store exists anywhere for "last successful pull" — nothing to reuse; this is new.
- Search API items are heterogeneous by `type`: `dataverse` items carry `identifier`; `dataset` items add `global_id`. `published_at` is present on items and is the natural sort/filter field.
- `backend/tests/` doesn't exist yet; no test suite exists for the backend (pytest is a listed dependency but unused).

## Proposed approach

### 1. State store — `backend/data/state/last_pull.json`
Flat JSON, `{installation_url: iso_timestamp}`, read/write via two small stdlib-`json` helpers in `metadata.py`. No new dependency.

### 2. `Metadata` — add `incremental: bool = False`
- `_fetch()`: load state (`{}` if not incremental), pass `since=state.get(url)` per URL into `_request_metadata`.
- `_request_metadata()`: when `since` is set, add `&sort=date&order=desc&fq=dateSort:[{since} TO *]` to the query; trim each page to items newer than `since` via a new `_split_at_watermark(items, since)` helper (compares `published_at`), stopping pagination as soon as an older item appears. If the filtered request fails structurally on the first page (bad/missing `data.items`, HTTP error, JSON error), log a warning and retry that installation once with a plain full `q=*` pull — one fallback attempt, not a retry loop. Existing `page_limit` still applies as the hard ceiling if the watermark is never hit.
- `_pull_combine_save()`: capture `successful_urls` from `dfs` right after `_fetch()` returns, before any merge. If `self.incremental` and the existing CSV exists, load it, concat with new `df`, dedupe on `global_id` (fallback `identifier`) + `installation_url`, keeping the row with the latest `published_at`. Otherwise keep today's full-overwrite path unchanged. After a successful save, if `self.incremental`, update state timestamps (current UTC) only for `successful_urls`.

### 3. `orchestrator.py` — new flag
Add `--incremental` (`action="store_true"`, matches `--no-save` style) to the metadata arg group; pass through as `Metadata(..., incremental=args.incremental)`.

### Edge cases covered by this design (no extra code needed)
- No state file / installation never succeeded → `since=None` → full pull, same as today.
- `--no-save` + `--incremental` → save block skipped entirely, so no merge and no state update (log one line noting state wasn't updated, to avoid silent confusion).
- No `metadata.csv` yet → incremental run just writes fresh, same as a first non-incremental run.

## Files to add/change

- `backend/services/metadata.py` — state helpers, `_split_at_watermark`, `incremental` param, changes to `_fetch`/`_request_metadata`/`_pull_combine_save`.
- `backend/services/orchestrator.py` — `--incremental` flag, pass-through.
- `backend/data/state/last_pull.json` — new, created at runtime; add to `.gitignore` alongside the other generated `data/` outputs.
- `backend/tests/test_metadata_incremental.py` — new, minimal pytest for `_split_at_watermark` and the dedupe-keep-latest logic (pure functions, no network mocking).

## Implementation steps

1. Add `STATE_PATH`, `_load_state`, `_save_state`, `_split_at_watermark` to `metadata.py`.
2. Add `incremental` param to `Metadata.__init__`.
3. Thread `since` through `_fetch()` → `_request_metadata()`; implement the filtered query + client-side watermark stop + one-shot fallback.
4. Update `_pull_combine_save()`: capture `successful_urls`, add the incremental merge/dedupe branch, add the post-save state update.
5. Add `--incremental` to `orchestrator.py` and pass it through.
6. Add `backend/data/state/` to `.gitignore`.
7. Write `backend/tests/test_metadata_incremental.py`.

## Testing strategy

- `cd backend && pytest tests/test_metadata_incremental.py -q` — covers `_split_at_watermark` and the dedupe-keep-latest merge logic directly.
- Manual sanity check against a real installation (the `fq`/`sort` server-side behavior is unverified live): run `python -m services.orchestrator --cmd metadata --incremental --url-list https://dataverse.harvard.edu --page-limit 1` twice back-to-back — the second run's added-row count should be ~0, and `logs/metadata_fetch.log` should show whether the fallback-to-full-pull path fired.

## Risks and open questions

- Dataverse Solr schema support for `dateSort`/`fq` may not be consistent across installations/versions — the one-shot fallback-to-full-pull exists specifically to contain this risk, but hasn't been verified against a real installation yet.
- Using "now" as the new watermark (rather than the max `published_at` actually fetched) is simpler but assumes installations don't backdate `published_at`; revisit if that assumption breaks in practice.
- `backend/data/dataverses.csv` and `data/installations/installations.csv` are read by other code but nothing in the current pipeline writes them (pre-existing issue, out of scope here, but the `--cmd installations` path this feature doesn't touch is already broken — `Installation().call()` doesn't exist).
