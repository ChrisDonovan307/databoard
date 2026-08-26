from pathlib import Path
import json
import pandas as pd

import requests_cache
import asyncio
import aiohttp

from aiohttp_client_cache import CachedSession, SQLiteBackend
import logging
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]  # backend/

# Set up logger
_log_path = ROOT / "logs" / "metadata_fetch.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(_log_path),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def url_to_name(url):
    return url.split("//")[1].split(".")[1]


STATE_PATH = ROOT / "data" / "state" / "last_pull.json"


def _load_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    with open(STATE_PATH) as f:
        return json.load(f)


def _save_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _is_retryable_status(status: int) -> bool:
    """HTTP statuses worth retrying with backoff: rate-limited or server-side."""
    return status == 429 or 500 <= status < 600


def _backoff_delay(attempt: int, retry_after: float | None = None, cap: float = 30.0) -> float:
    """Exponential backoff delay for a 0-indexed retry attempt, honoring Retry-After."""
    if retry_after is not None:
        return max(retry_after, 0.0)
    return min(2**attempt, cap)


def _split_at_watermark(items: list[dict], since: str | None) -> tuple[list[dict], bool]:
    """Trim items to those newer than `since`, stopping at the first older item.

    Returns (kept items, whether an older item was seen this page).
    """
    kept = []
    for item in items:
        published = item.get("published_at")
        if published and published <= since:
            return kept, True
        kept.append(item)
    return kept, False


# Install cache
_cache_installed = False
if not _cache_installed:
    requests_cache.install_cache("dataverse_cache", expire_after=3600)  # 1 hour
    _cache_installed = True
    logger.info("Caching requests enabled")


class Metadata:
    def __init__(
        self,
        start: int = 0,
        per_page: int = 1000,
        page_limit: int = 2,
        url_list: str | list[str] = "installations",
        file_type: list[str] | None = None,
        save: bool = True,
        timeout: int = 180,
        file_name: str = "metadata",
        data_dir: Path = ROOT / "data" / "metadata",
        incremental: bool = False,
        page_delay: float = 0.2,
        max_retries: int = 3,
    ):
        self.start = start
        self.per_page = per_page
        self.page_limit = page_limit
        self.url_list = url_list
        self.file_type = (
            file_type if file_type is not None else ["dataverse", "dataset"]
        )
        self.save = save
        self.timeout: int = timeout
        self.file_name: str = file_name
        self.data_dir = Path(data_dir)
        self.incremental = incremental
        self.page_delay = page_delay
        self.max_retries = max_retries
        self.urls = self._get_urls()

    def call(self):
        self._pull_combine_save()

    def _get_urls(self) -> list[str]:
        """Take input arg, return URLs of installations as list of strings to call when collecting data"""
        # Load installation data to get URLs
        if self.url_list == "installations":
            installations = pd.read_csv(
                ROOT / "data" / "installations" / "installations.csv"
            )
            urls = installations["url"].tolist()
            logger.info(f"Loaded {len(urls)} installation URLs")
        else:
            if not isinstance(self.url_list, list):
                raise TypeError(
                    "url_list must be 'installations' or a list of URL strings"
                )
            urls = self.url_list
            logger.info(f"Loaded {len(urls)} URLs manually")

        return urls

    def _pull_combine_save(self):
        """API requests for Dataverse metadata with search API (parallel)

        Using list of installations, query each and get metadata with request_metadata and save as CSV and parquet.

        Parameters
        ----------
        urls : list of str
            List of URLs of Dataverse installations (including https://)
        start : int
            Record to start on for pagination
        per_page : int
            Number of records per page. Dataverse API limits at 1000 maybe?
        page_limit : int
            Limit the number of pages.

        Returns
        -------
        None
            Saves to file, does not return anything
        """

        # Run async requests in parallel
        logger.info(
            f"Starting parallel metadata fetch for {len(self.urls)} installations"
        )
        start_time = datetime.now()
        dfs, complete_urls = asyncio.run(self._fetch())
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Completed in {elapsed:.2f} seconds")
        logger.info(
            f"Successfully fetched from {len(dfs)}/{len(self.urls)} installations"
        )

        # Combine into single dataset
        if len(dfs) == 0:
            logger.error("No data fetched from any installation. Nothing to save.")
            return
        elif len(dfs) == 1:
            df = list(dfs.values())[0]
        else:
            df = pd.concat(dfs.values(), ignore_index=True)

        logger.info(f"Combined dataset: {len(df)} total records")

        # Track which installation URLs completed this run (reached total_count,
        # page_limit, or the watermark) rather than stopping early on a rate-limit/
        # server error - only these should advance the incremental watermark, so a
        # partial pull gets its missing tail retried on the next incremental run.
        successful_urls = set(df["installation_url"].unique()) & complete_urls

        if self.save:
            paths = {
                "csv": self.data_dir / (self.file_name + ".csv"),
                "parquet": self.data_dir / (self.file_name + ".parquet"),
            }

            if self.incremental and paths["csv"].exists():
                existing = pd.read_csv(paths["csv"])
                df = pd.concat([existing, df], ignore_index=True)
                dedupe_key = (
                    df["global_id"].fillna(df.get("identifier"))
                    if "global_id" in df.columns
                    else df["identifier"]
                )
                df["_dedupe_key"] = (
                    dedupe_key.astype(str) + "|" + df["installation_url"].astype(str)
                )
                df = (
                    df.sort_values("published_at")
                    .drop_duplicates("_dedupe_key", keep="last")
                    .drop(columns="_dedupe_key")
                )
                logger.info(
                    f"Incremental merge: {len(existing)} existing + new -> {len(df)} total after dedupe"
                )

            df.to_csv(paths["csv"], index=False)
            logger.info(f"Saved CSV to {paths['csv']}")

            # Prepare for parquet - convert all object columns to strings
            df_parquet = df.copy()
            for col in df_parquet.select_dtypes(include=["object"]).columns:
                df_parquet[col] = df_parquet[col].astype(str)

            df_parquet.to_parquet(paths["parquet"], index=False)
            logger.info(f"Saved Parquet to {paths['parquet']}")

            if self.incremental:
                state = _load_state()
                # Match the "...Z" format the Search API uses for published_at,
                # since watermarks are compared against it as plain strings.
                now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                for url in successful_urls:
                    state[url] = now
                _save_state(state)
                logger.info(f"Updated last-pull watermark for {len(successful_urls)} installations")
        else:
            logger.info("Not saving any files (--save False)")
            if self.incremental:
                logger.info("Incremental run with --no-save: state not updated")

    async def _fetch(self):
        """Fetch metadata from all installations in parallel"""
        logger.info(
            f"fetch called with: start={self.start}, per_page={self.per_page}, page_limit={self.page_limit}"
        )
        state = _load_state() if self.incremental else {}
        cache = SQLiteBackend(cache_name="aiohttp_cache", expire_after=3600)

        # Create SSL context
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with CachedSession(cache=cache, connector=connector) as session:
            tasks = [
                self._request_metadata(session=session, base=url, since=state.get(url))
                for url in self.urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build dictionary of DFs, filtering out errors
        dfs = {}
        failures = []
        complete_urls = set()

        for url, result in zip(self.urls, results):
            # if result is exception, log it and put in failures list
            if isinstance(result, BaseException):
                logger.error(
                    f"FAILED: {url} - {type(result).__name__}: {str(result)[:100]}"
                )
                failures.append({"url": url, "error": str(result)[:200]})
                continue

            df, complete = result

            # if empty data frame, add to failures list
            if df.empty:
                logger.warning(f"EMPTY: {url} - No data returned")
                failures.append({"url": url, "error": "No data returned"})
                continue

            # success or partial, these get returned as dict of dfs
            status = "SUCCESS" if complete else "PARTIAL"
            logger.info(f"{status}: {url} - {len(df)} records")
            # Add column with installation name and url
            df["installation"] = url_to_name(url)
            df["installation_url"] = url
            dfs[url_to_name(url)] = df
            if complete:
                complete_urls.add(url)

        # failure log
        if failures:
            failure_df = pd.DataFrame(failures)
            failure_df["timestamp"] = datetime.now()
            failure_df.to_csv(ROOT / "logs" / "failed_installations.csv", index=False)
            logger.warning(
                f"Logged {len(failures)} failures to logs/failed_installations.csv"
            )

        return dfs, complete_urls

    async def _get_page(self, session, url):
        """Fetch one page, retrying on 429/5xx with backoff.

        Returns (data, exhausted). exhausted=True means retries ran out on a
        rate-limit/server error - caller should stop and keep what it already has.
        Other HTTP errors raise aiohttp.ClientResponseError as before.
        """
        for attempt in range(self.max_retries + 1):
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if _is_retryable_status(response.status):
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        delay = _backoff_delay(
                            attempt, float(retry_after) if retry_after else None
                        )
                        logger.warning(
                            f"{url}: status {response.status}, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    return None, True
                response.raise_for_status()
                return await response.json(), False

    async def _request_metadata(self, session, base, since=None):
        page = 1
        all_items = []

        # type parameters - create &type=x&type=y for each type in list
        # could probably clean this up
        type_params = "".join([f"&type={t}" for t in self.file_type])

        start = self.start
        use_filter = since is not None
        filter_failed = False

        while True:
            filter_params = (
                f"&sort=date&order=desc&fq=dateSort:[{since} TO *]" if use_filter else ""
            )
            url = (
                f"{base.rstrip('/')}/api/search?q=*{type_params}{filter_params}"
                f"&start={start}&per_page={self.per_page}"
            )
            try:
                data, exhausted = await self._get_page(session, url)
                if exhausted:
                    logger.warning(
                        f"{base}: giving up after repeated rate-limit/server errors, "
                        f"returning partial results ({len(all_items)} records)"
                    )
                    return pd.DataFrame(all_items), False

                # check structure of response
                if "data" not in data or "items" not in data["data"]:
                    if use_filter and not filter_failed:
                        logger.warning(
                            f"{base}: incremental filter returned unexpected response, falling back to full pull"
                        )
                        use_filter, filter_failed = False, True
                        start, page, all_items = self.start, 1, []
                        continue
                    logger.debug(f"{base}: Unexpected response structure")
                    break

                items = data["data"]["items"]
                if use_filter:
                    items, hit_watermark = _split_at_watermark(items, since)
                    all_items.extend(items)
                    if hit_watermark:
                        logger.info(
                            f"{base}: reached watermark {since}, stopping, fetched {len(all_items)} records"
                        )
                        break
                else:
                    all_items.extend(items)

                # see if there are more to query
                total = data["data"]["total_count"]
                start = start + self.per_page
                page += 1

                if start >= total or page > self.page_limit:
                    reason = (
                        "reached total"
                        if start >= total
                        else f"hit page_limit ({page} > {self.page_limit})"
                    )
                    logger.info(
                        f"{base}: Stopping - {reason}, fetched {len(all_items)} records"
                    )
                    break

                await asyncio.sleep(self.page_delay)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if use_filter and not filter_failed:
                    logger.warning(
                        f"{base}: incremental filter request failed ({type(e).__name__}), falling back to full pull"
                    )
                    use_filter, filter_failed = False, True
                    start, page, all_items = self.start, 1, []
                    continue
                logger.warning(
                    f"{base}: {type(e).__name__}, giving up, returning partial results ({len(all_items)} records)"
                )
                return pd.DataFrame(all_items), False

            except json.JSONDecodeError:
                if use_filter and not filter_failed:
                    logger.warning(
                        f"{base}: incremental filter returned bad JSON, falling back to full pull"
                    )
                    use_filter, filter_failed = False, True
                    start, page, all_items = self.start, 1, []
                    continue
                logger.warning(
                    f"{base}: JSON decode error, giving up, returning partial results ({len(all_items)} records)"
                )
                return pd.DataFrame(all_items), False

        return pd.DataFrame(all_items), True

    def probe_sizes(self) -> pd.DataFrame:
        """Cheap ahead-of-time check: one per_page=1 request per installation to
        learn total_count, so page-limit/timeout/page-delay can be tuned before
        committing to a real pull."""
        return asyncio.run(self._probe_sizes())

    def probe_and_save_sizes(self) -> pd.DataFrame:
        df = self.probe_sizes()
        out_path = ROOT / "logs" / "installation_sizes.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"Saved installation sizes to {out_path}")
        return df

    async def _probe_sizes(self) -> pd.DataFrame:
        cache = SQLiteBackend(cache_name="aiohttp_cache", expire_after=3600)

        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with CachedSession(cache=cache, connector=connector) as session:
            tasks = [self._probe_one(session, url) for url in self.urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        rows = []
        for url, result in zip(self.urls, results):
            if isinstance(result, BaseException):
                logger.warning(f"{url}: size probe failed - {type(result).__name__}")
                continue
            rows.append(
                {"installation": url_to_name(url), "url": url, "total_count": result}
            )

        return (
            pd.DataFrame(rows)
            .sort_values("total_count", ascending=False)
            .reset_index(drop=True)
        )

    async def _probe_one(self, session, url) -> int:
        query = f"{url.rstrip('/')}/api/search?q=*&start=0&per_page=1"
        data, exhausted = await self._get_page(session, query)
        if exhausted or data is None:
            raise RuntimeError("rate limited / server error")
        return data["data"]["total_count"]
