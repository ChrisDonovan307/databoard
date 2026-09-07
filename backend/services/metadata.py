from pathlib import Path
import json
import pandas as pd

import requests_cache
import asyncio
import aiohttp

from aiohttp_client_cache import CachedSession, SQLiteBackend
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from db import get_engine, get_session
from db.models import Installation as InstallationRow, PullState
from db.upsert import upsert_rows
from services.ingest import ingest_installation


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


_WATERMARK_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _load_state() -> dict[str, str]:
    """{installation_url: watermark string} from the pull_state table.

    Watermark strings are formatted to match the Search API's published_at
    ("...Z"), since _split_at_watermark compares them as plain strings.
    """
    out: dict[str, str] = {}
    try:
        with get_session() as s:
            rows = s.execute(
                select(InstallationRow.url, PullState.last_pulled_at).join(
                    PullState, PullState.installation_id == InstallationRow.id
                )
            )
            for url, ts in rows:
                if ts is not None:
                    out[url] = ts.strftime(_WATERMARK_FMT)
    except Exception as e:  # noqa: BLE001 - no DB / empty table -> no watermarks
        logger.warning(
            f"Could not read pull_state ({type(e).__name__}: {e}); "
            "treating all installations as un-watermarked"
        )
    return out


def _advance_watermarks(urls: set[str], ts: datetime) -> int:
    """Set pull_state.last_pulled_at = ts for the given installation URLs."""
    if not urls:
        return 0
    with get_session() as s:
        conn = s.connection()
        id_by_url = dict(
            s.execute(
                select(InstallationRow.url, InstallationRow.id).where(
                    InstallationRow.url.in_(list(urls))
                )
            ).all()
        )
        rows = [
            {"installation_id": id_by_url[u], "last_pulled_at": ts}
            for u in urls
            if u in id_by_url
        ]
        upsert_rows(
            conn,
            PullState.__table__,
            rows,
            index_elements=["installation_id"],
            update_cols=["last_pulled_at"],
        )
    return len(rows)


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

    def _installation_ids(self) -> dict[str, int]:
        """{installation_url: id} from the installation table."""
        with get_session() as s:
            return dict(
                s.execute(select(InstallationRow.url, InstallationRow.id)).all()
            )

    def _get_urls(self) -> list[str]:
        """Take input arg, return URLs of installations as list of strings to call when collecting data"""
        # Load installation data to get URLs
        if self.url_list == "installations":
            try:
                urls = list(self._installation_ids().keys())
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Could not read installation table ({type(e).__name__}: {e})")
                urls = []
            if urls:
                logger.info(f"Loaded {len(urls)} installation URLs from DB")
                return urls
            installations = pd.read_csv(
                ROOT / "data" / "installations" / "installations.csv"
            )
            urls = installations["url"].tolist()
            logger.info(f"Loaded {len(urls)} installation URLs from CSV (DB empty)")
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

        if len(dfs) == 0:
            logger.error("No data fetched from any installation. Nothing to save.")
            return

        total = sum(len(df) for df in dfs.values())
        logger.info(f"Fetched {total} records across {len(dfs)} installations")

        # Track which installation URLs completed this run (reached total_count,
        # page_limit, or the watermark) rather than stopping early on a rate-limit/
        # server error - only these should advance the incremental watermark, so a
        # partial pull gets its missing tail retried on the next incremental run.
        fetched_urls = {df["installation_url"].iloc[0] for df in dfs.values()}
        successful_urls = fetched_urls & complete_urls

        if not self.save:
            logger.info("Not saving (--no-save): skipping DB writes")
            if self.incremental:
                logger.info("Incremental run with --no-save: watermarks not advanced")
            return

        self._upsert_to_db(dfs)

        if self.incremental:
            now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
            n = _advance_watermarks(successful_urls, now)
            logger.info(f"Advanced last-pull watermark for {n} installations")

    def _upsert_to_db(self, dfs: dict[str, pd.DataFrame]) -> None:
        """Upsert each installation's fetched records into the normalised schema,
        one transaction per installation."""
        id_by_url = self._installation_ids()
        for df in dfs.values():
            url = df["installation_url"].iloc[0]
            iid = id_by_url.get(url)
            if iid is None:
                logger.warning(
                    f"{url}: no installation row (run --cmd installations first); "
                    f"skipping {len(df)} records"
                )
                continue
            items = df.to_dict("records")
            with get_session() as s:
                counts = ingest_installation(s.connection(), iid, items)
            logger.info(f"{url}: upserted {counts}")

    @staticmethod
    def export_parquet(path: str) -> None:
        """Dump the core entity tables to a flat parquet for offline sharing.
        Opt-in; not part of the normal pipeline. Lookups/junctions are not
        included."""
        engine = get_engine()
        dv = pd.read_sql("SELECT * FROM dataverse", engine).assign(_entity="dataverse")
        ds = pd.read_sql("SELECT * FROM dataset", engine).assign(_entity="dataset")
        out = pd.concat([dv, ds], ignore_index=True)
        out.to_parquet(path, index=False)
        logger.info(f"Exported {len(out)} rows ({len(dv)} dataverse + {len(ds)} dataset) to {path}")

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
