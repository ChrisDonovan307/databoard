import json
import os

import pandas as pd
from dotenv import load_dotenv

import requests
import requests_cache
import asyncio
import aiohttp

from aiohttp_client_cache import CachedSession, SQLiteBackend
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/metadata_fetch.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# Install cache only once - guard against multiple imports
if not hasattr(requests_cache, '_dataverse_cache_installed'):
    requests_cache.install_cache("dataverse_cache", expire_after=3600)  # 1 hour
    requests_cache._dataverse_cache_installed = True
    logger.info("Caching requests enabled")

def metadata_setup(url_list = 'installations'):
    """Setup for gathering metadata

    Hard coded for now - eventually take it form instalaltions list, add as arg

    Parameters
    ----------
    urls : str
        If 'installations', pull whole list of URLs. Otherwise, input list manually.

    Returns
    -------
    urls : list of str
        List of URLs containing every installation
    """

    # Load installation data to get URLs
    if url_list == 'installations':
        installations = pd.read_parquet("app/data/installations/installations.parquet")
        urls = installations["url"].tolist()
        logger.info(f"Loaded {len(urls)} installation URLs")
    else:
        urls = url_list
        logger.info(f"Loaded {len(urls)} URLs manually")

    return urls


def pull_combine_save(urls, start=0, file_type=['dataverse', 'dataset'], per_page=1000, page_limit=10, save=True, timeout=180):
    """API requests for Dataverse metadata with search API (parallel)

    Using list of installations, query each and get metadata with request_metadata and save as CSV and parquet

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
    logger.info(f"Starting parallel metadata fetch for {len(urls)} installations")
    start_time = datetime.now()
    dfs = asyncio.run(fetch_all_metadata(
        urls=urls, 
        start=start, 
        file_type=file_type,
        per_page=per_page, 
        page_limit=page_limit, 
        timeout=timeout
    ))
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Completed in {elapsed:.2f} seconds")
    logger.info(f"Successfully fetched from {len(dfs)}/{len(urls)} installations")

    # Combine into single dataset
    if len(dfs) == 0:
        logger.error("No data fetched from any installation. Nothing to save.")
        return
    elif len(dfs) == 1:
        df = list(dfs.values())[0]
    else:
        df = pd.concat(dfs.values(), ignore_index=True)

    logger.info(f"Combined dataset: {len(df)} total records")

    if save:
        paths = {
            "csv": "app/data/metadata/metadata.csv",
            "parquet": "app/data/metadata/metadata.parquet",
        }
        df.to_csv(paths["csv"], index=False)
        logger.info(f"Saved CSV to {paths['csv']}")

        # Prepare for parquet - convert all object columns to strings
        df_parquet = df.copy()
        for col in df_parquet.select_dtypes(include=['object']).columns:
            df_parquet[col] = df_parquet[col].astype(str)

        df_parquet.to_parquet(paths["parquet"], index=False)
        logger.info(f"Saved Parquet to {paths['parquet']}")
    else: 
        logger.info(f"Not saving any files (--save False)")


async def fetch_all_metadata(urls, start, file_type, per_page, page_limit, timeout):
    """Fetch metadata from all installations in parallel"""
    logger.info(
        f"fetch_all_metadata called with: start={start}, per_page={per_page}, page_limit={page_limit}"
    )
    cache = SQLiteBackend(cache_name="aiohttp_cache", expire_after=3600)

    # Create SSL context that doesn't verify certificates (for problematic installations)
    import ssl

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with CachedSession(cache=cache, connector=connector) as session:
        tasks = [
            request_metadata_async(
                session=session, 
                base=url, 
                file_type=file_type,
                start=start, 
                per_page=per_page, 
                page_limit=page_limit,
                timeout=timeout
            )
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build dictionary of DFs, filtering out errors
    dfs = {}
    failures = []

    for url, result in zip(urls, results):
        # if result is exception, log it and put in failures list
        if isinstance(result, Exception):
            logger.error(
                f"FAILED: {url} - {type(result).__name__}: {str(result)[:100]}"
            )
            failures.append({"url": url, "error": str(result)[:200]})

        # if empty data frame, add to failures list
        elif result.empty:
            logger.warning(f"EMPTY: {url} - No data returned")
            failures.append({"url": url, "error": "No data returned"})

        # success, these get returned as dict of dfs
        else:
            logger.info(f"SUCCESS: {url} - {len(result)} records")
            # Add column with installation name and url
            result['installation'] = url_to_name(url)
            result['installation_url'] = url
            dfs[url_to_name(url)] = result

    # failure log
    if failures:
        failure_df = pd.DataFrame(failures)
        failure_df["timestamp"] = datetime.now()
        failure_df.to_csv("app/logs/failed_installations.csv", index=False)
        logger.warning(
            f"Logged {len(failures)} failures to app/logs/failed_installations.csv"
        )

    return dfs


async def request_metadata_async(session, base, file_type=['dataverse', 'dataset'], start=0, per_page=1000, page_limit=10, timeout=180):
    """Async version of request_metadata"""
    page = 1
    all_items = []

    # type parameters - create &type=x&type=y for each type in list
    # could probably clean this up
    type_params = ''.join([f'&type={t}' for t in file_type])

    while True:
        url = f"{base.rstrip('/')}/api/search?q=*{type_params}&start={start}&per_page={per_page}"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # check structure of response
                if "data" not in data or "items" not in data["data"]:
                    logger.debug(f"{base}: Unexpected response structure")
                    break
                all_items.extend(data["data"]["items"])

                # see if there are more to query
                total = data["data"]["total_count"]
                start = start + per_page
                page += 1

                if start >= total or page > page_limit:
                    reason = (
                        "reached total"
                        if start >= total
                        else f"hit page_limit ({page} > {page_limit})"
                    )
                    logger.info(
                        f"{base}: Stopping - {reason}, fetched {len(all_items)} records"
                    )
                    break

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(f"{base}: {type(e).__name__}")
            raise  # Re-raise to be caught by gather

        except json.JSONDecodeError as e:
            logger.debug(f"{base}: JSON decode error")
            raise  # Re-raise to be caught by gather

    return pd.DataFrame(all_items)


def url_to_name(url):
    return url.split("//")[1].split(".")[1]
