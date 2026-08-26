# Implementation report: rate-limit resilience for large Dataverse installations

Plan: `docs/plans/done/2026-09-04-dataverse-rate-limit-resilience.md`

## Implemented

- `backend/services/metadata.py`:
  - `_is_retryable_status(status)` / `_backoff_delay(attempt, retry_after=None, cap=30.0)` — pure helpers for deciding what's retryable and how long to wait.
  - `Metadata.__init__`: new `page_delay: float = 0.2`, `max_retries: int = 3` params.
  - `_get_page(session, url)`: new method, fetches one page, retrying up to `max_retries` times with exponential backoff (honors `Retry-After`) on HTTP 429/5xx; returns `(data, exhausted)`. Other HTTP errors still raise via `raise_for_status()` as before.
  - `_request_metadata`: now uses `_get_page`, sleeps `page_delay` seconds between successful page fetches (skipped on the terminal page), and on any unresolved failure (retry exhaustion, `ClientError`/`TimeoutError`, bad JSON) returns whatever was collected so far as `(DataFrame, complete=False)` instead of raising and discarding it. Returns `(DataFrame, complete=True)` on normal completion.
  - `_fetch`: unpacks the new `(df, complete)` tuples, logs `PARTIAL` vs `SUCCESS`, and returns `(dfs, complete_urls)`.
  - `_pull_combine_save`: `successful_urls` (which gates the incremental watermark update) is now `set(df["installation_url"].unique()) & complete_urls`, so a partial pull doesn't get its watermark advanced.
  - `probe_sizes()` / `probe_and_save_sizes()` / `_probe_sizes()` / `_probe_one()`: new ahead-of-time size check — one `per_page=1` request per installation (reusing `_get_page`'s retry logic), returns/saves a DataFrame sorted by `total_count` descending to `logs/installation_sizes.csv`.
- `backend/services/orchestrator.py`: new `--cmd sizes` choice (runs `probe_and_save_sizes()`), new `--page-delay` (default 0.2) and `--max-retries` (default 3) flags passed through to `Metadata` for the `metadata`/`all` commands.
- `backend/README.md`: added "Checking installation sizes ahead of time" and "Large installations (Harvard, etc.) and rate limiting" sections; removed the old informal "set timeout to 60s" note in favor of the actual mechanism.
- `backend/tests/test_metadata_resilience.py`: new pytest covering `_is_retryable_status`, `_backoff_delay` (exponential, capped, `Retry-After` override), and the complete/partial intersection logic used for watermark gating.

## Checks run

- `python -c "import services.metadata, services.orchestrator"` — imports cleanly.
- `uv run pytest tests/ -q` — 8 passed (5 pre-existing + 3 new... actually 5 new resilience tests + 3 existing incremental tests = 8).
- `uvx ruff check` on changed files — 7 warnings, all confirmed (via `git diff`) to be on pre-existing, untouched lines (import order, naive `datetime.now()`, `list(...)[0]` idiom, aliased `TimeoutError`); no new issues from added code.
- Live sanity checks (hit real Dataverse APIs):
  - `python -m services.orchestrator --cmd sizes --url-list https://dataverse.uvm.edu,https://dataverse.harvard.edu` — correctly reported Harvard at ~5.8M records vs UVM's 232, saved to `logs/installation_sizes.csv`.
  - `python -m services.orchestrator --cmd metadata --url-list https://dataverse.uvm.edu --page-limit 2 --page-delay 0.1` — normal full pull still works end-to-end with the new delay/retry code path in place.

## Remaining / deviations

- None from the approved plan. The plan's noted open questions (default `page_delay`/backoff constants are guesses pending real-world tuning; no cross-installation concurrency cap added; `probe_sizes()` is a point-in-time estimate) still stand as documented risks, not implementation gaps.
- Not yet verified: a live run against Harvard actually triggering a 429/5xx to exercise the retry-with-backoff path (would require either an unlucky real rate-limit event or an intentionally aggressive `page_limit`/`page_delay=0` run, which wasn't done here to avoid actually hammering Harvard's API). The retry logic itself is exercised indirectly by the pure-function tests and by code review of `_get_page`.
