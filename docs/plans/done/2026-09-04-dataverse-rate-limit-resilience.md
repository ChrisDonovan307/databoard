# Rate-limit resilience for large Dataverse installations

## Goal

Large installations (Harvard, millions of records) fail entire pulls when throttled, and lose all pages already fetched. Add: (1) a delay between paginated requests to a single installation, (2) retry-with-backoff specifically for rate-limit/server errors, (3) return partial results instead of discarding them on an unrecoverable failure, and (4) a way to know ahead of time which installations are large, so `--page-limit`/`--timeout` can be tuned per-run without guessing.

## Current architecture / relevant findings

- `backend/services/metadata.py::Metadata._request_metadata()` (line 280) does per-installation pagination in a `while True` loop: fetch page → extend `all_items` → compute next `start` → loop, stopping at `total_count` or `page_limit`. There is **no delay** between iterations — for Harvard-scale installations this fires hundreds/thousands of requests back-to-back against one host.
- On `aiohttp.ClientError`, `asyncio.TimeoutError`, or `json.JSONDecodeError` (lines 347-367), if the incremental filter fallback has already been used (or isn't in play), the exception is **re-raised**, discarding `all_items` entirely — a failure on page 500 loses the 499 pages already collected in that call's local variable.
- `_fetch()` (line 221) runs one `_request_metadata` task per installation via `asyncio.gather(..., return_exceptions=True)` on a single shared `aiohttp.TCPConnector` with no `limit=` set (aiohttp default is 100 total connections) — all installations are queried concurrently, each internally looping with no backoff.
- `response.raise_for_status()` (line 304) turns a 429 into a generic `aiohttp.ClientResponseError`, which is caught by the same `except aiohttp.ClientError` as any other network failure (line 347) — no distinction between "rate limited, back off and retry" and "installation is actually down."
- Success/failure is currently binary per installation: `_fetch()` classifies each result as success (non-empty DataFrame), empty, or exception (lines 248-267); there is no "partial" state. The incremental feature (`docs/plans/active/incremental-metadata-updates.md`, already implemented) uses `successful_urls = set(df["installation_url"].unique())` (line 168) to decide which installations get their watermark advanced — a partial pull must NOT be treated as fully successful, or the next incremental run would wrongly believe it has everything up to "now" and skip the un-fetched tail.
- The installations list (`data/installations/installations.geojson`, sourced from the public `dataverse-installations` GitHub JSON) has a `metrics` field, but it's a **boolean** (`"metrics": true`) meaning "this installation exposes a metrics API" — it is not a record count. Confirmed by fetching the live JSON: Harvard's entry has no count field at all.
- The Dataverse Search API response already includes `total_count` in `data.data.total_count` on every page, including the very first one (`_request_metadata`, line 332). A `per_page=1` request against `/api/search?q=*&start=0&per_page=1` gets the total count for one installation for the cost of one tiny request — this is the cheapest available way to learn installation size ahead of a real pull, and reuses the exact query shape already in use (no new endpoint, no new dependency).
- `README.md` already documents the Harvard timeout issue informally ("Having issues with Harvard... Just set timeout to 60s") — this plan replaces that guesswork with actual backoff/delay handling and an ahead-of-time size check.
- No existing retry/backoff logic anywhere in the codebase to reuse; `aiohttp`/`asyncio` stdlib primitives (`asyncio.sleep`) are sufficient, no new dependency needed.

## Proposed approach

### 1. Delay between pages — `page_delay` param
Add `page_delay: float = 0.2` to `Metadata.__init__`, threaded into `_request_metadata`. `await asyncio.sleep(self.page_delay)` at the end of each successful loop iteration (skip on the final page, no point sleeping after the last request). Small, per-installation, no shared rate limiter needed since pagination within one installation is already sequential.

### 2. Retry with backoff on rate-limit / transient errors
In `_request_metadata`, before the generic `except aiohttp.ClientError` fallback: check `response.status` explicitly for `429` and `5xx` and retry that *page* (not the whole installation) with exponential backoff (e.g. up to `max_retries=3` attempts, `2 ** attempt` seconds, capped), honoring a `Retry-After` header if present. Only after retries are exhausted does the existing raise/fallback path kick in. Non-retryable errors (4xx other than 429, malformed JSON that isn't transient) fail fast as today.

### 3. Return partial results instead of discarding
Change `_request_metadata` so that once retries are exhausted on a page, instead of raising, it returns what's collected so far: `(pd.DataFrame(all_items), complete: bool)` — `complete=False` when it stopped early due to an unresolved error, `True` when it stopped because it reached `total_count`, `page_limit`, or the incremental watermark. Propagate this tuple through `_fetch()`: partial DataFrames still get included in the combined result (better than losing hundreds of already-fetched records), logged distinctly (`PARTIAL: {url} - N records, stopped early`), and **excluded from `successful_urls`** in `_pull_combine_save` so an incremental run's watermark isn't advanced past what was actually fetched — the next incremental run will naturally retry from the old watermark and pick up the missing tail.

### 4. Ahead-of-time size check
Add `Metadata.probe_sizes()`: for each URL in `self.urls`, fire one `per_page=1&start=0` request (reusing the existing session/connector setup), pull `total_count` from the response, and return/save a DataFrame of `{installation, url, total_count}` sorted descending. Wire a new `--cmd sizes` choice into `orchestrator.py` that runs this and writes `logs/installation_sizes.csv` (mirrors the existing `logs/failed_installations.csv` convention). This lets you run `--cmd sizes` first, see Harvard etc. are outliers, and set `--page-limit`/`--timeout`/`--page-delay` accordingly before committing to a full pull — no automatic behavior change, just visibility.

### Edge cases covered
- Installation that's fully down (connection refused, DNS failure): fails immediately, no wasted retries — only 429/5xx get the backoff treatment.
- `--incremental` + partial pull: watermark not advanced for that URL (per #3), so next incremental run re-fetches from the same `since` and fills the gap; today's dedupe-on-`global_id`+`installation_url` (already implemented) absorbs any overlap.
- `probe_sizes()` itself getting rate-limited: it's one request per installation, not paginated, so the existing retry-on-429 (#2) is sufficient without extra handling.

## Files to add/change

- `backend/services/metadata.py` — `page_delay`/`max_retries` params, retry/backoff in `_request_metadata`, partial-result tuple return, `successful_urls` filtering in `_pull_combine_save`, new `probe_sizes()` method.
- `backend/services/orchestrator.py` — `--page-delay`, `--max-retries` args passed through; new `--cmd sizes` choice.
- `backend/tests/test_metadata_incremental.py` (or a new `test_metadata_resilience.py`, matching existing per-feature test file naming) — pure-function tests for the backoff delay calculation and for the "partial pulls excluded from successful_urls" logic.
- `README.md` — replace the informal "set timeout to 60s" Harvard note with `--page-delay`/`--cmd sizes` guidance.

## Implementation steps

1. Add `page_delay` and `max_retries` params to `Metadata.__init__`, default `0.2` and `3`.
2. In `_request_metadata`, add explicit status-code check before `raise_for_status()`; on 429/5xx, sleep with exponential backoff (respecting `Retry-After` if present) and retry the same page up to `max_retries` times.
3. Change `_request_metadata`'s return type to `(DataFrame, complete: bool)`; on retry exhaustion, return partial `all_items` with `complete=False` instead of raising.
4. Add `await asyncio.sleep(self.page_delay)` between page iterations (skip after the terminal page).
5. Update `_fetch()` to unpack the new tuple, log `PARTIAL` distinctly from `SUCCESS`, and still include partial DataFrames in `dfs`.
6. Update `_pull_combine_save()` so `successful_urls` only includes installations whose result was `complete=True`.
7. Add `Metadata.probe_sizes()` and wire `--cmd sizes` into `orchestrator.py`.
8. Update README's Harvard note.
9. Extend/add pytest coverage for backoff calculation and the partial/complete watermark-exclusion logic.

## Testing strategy

- `cd backend && pytest tests/ -q` — new unit tests for backoff delay math (pure function, no network) and for `successful_urls` excluding incomplete pulls (can reuse the existing dedupe test's DataFrame-construction style).
- Manual: `python -m services.orchestrator --cmd sizes` against the full installation list, confirm Harvard and other known-large installations sort near the top of `logs/installation_sizes.csv`.
- Manual: `python -m services.orchestrator --cmd metadata --url-list https://dataverse.harvard.edu --page-limit 5 --page-delay 0.5` and watch `logs/metadata_fetch.log` for whether any 429s occur and whether backoff/retry log lines appear.

## Risks and open questions

- Default `page_delay` (0.2s) and `max_retries`/backoff constants are guesses without a documented Dataverse rate-limit policy — may need tuning after the manual Harvard test.
- No per-run cap on concurrent installations exists today (`_fetch` gathers all URLs at once); this plan doesn't add one since the reported problem is single-installation pagination, not cross-installation concurrency — worth revisiting if a future full run (`--cmd metadata` over all ~150 installations) shows contention, but out of scope here.
- `probe_sizes()` gives a live count but a Dataverse installation's data can change between the probe and the real pull; treat it as planning guidance, not an exact pre-allocation.
- The pre-existing `Installation().call()` bug (noted in `docs/plans/active/incremental-metadata-updates.md`) is unrelated and out of scope for this plan.
