import pandas as pd
import json
from dotenv import load_dotenv
import requests
import requests_cache
import os
import pandas as pd

requests_cache.install_cache('dataverse_cache', expire_after=3600) # 1 hour
print("\n[metadata] Caching requests")

def metadata_setup():
    """Setup for gathering metadata

    Hard coded for now - eventually take it form instalaltions list, add as arg

    Parameters
    ----------
    None

    Returns
    -------
    urls : list of str
        List of URLs containing every installation
    """

    # Just hard coding for now... Will want to pull from installations list
    # urls = [
    #     'https://dataverse.asu.edu',
    #     'https://dataverse.harvard.edu'
    # ]

    # Load installation data to get URLs
    installations = pd.read_parquet('app/data/installations/installations.parquet')
    urls = installations['url'].tolist()

    print(f"\n[metadata_setup] URL list: {urls}")
    return urls

def pull_combine_save(urls, start=0, rows=1000, page_limit=10):
    """API requests for Dataverse metadata with search API
    
    Using list of installations, query each and get metadata with request_metadata and save as CSV and parquet
    
    Parameters
    ----------
    urls : list of str
        List of URLs of Dataverse installations (including https://)
    start : int
        Record to start on for pagination
    rows : int
        Number of rows per query. Dataverse API limits at 1000 maybe?
    page_limit : int
        Limit the number of pages. 

    Returns
    -------
    None
        Saves to file, does not return anything
    """

    # Make dictionary of DFs
    dfs = {
        url_to_name(url): request_metadata(base=url, page_limit=2)
        for url in urls
    }
    print(f"[metadata.pull_combine_save] DF keys: {dfs.keys()}")

    # Combine into single dataset
    df = pd.concat(dfs, ignore_index=True)

    # Save as csv and parquet
    paths = {
        'csv': 'app/data/metadata/metadata.csv', 
        'parquet': 'app/data/metadata/metadata.parquet'
    }
    df.to_csv(paths['csv'])
    df.to_parquet(paths['parquet'])
    print(f"[metadata.pull_combine_save] Saved to {paths.values()}")


def request_metadata(
    base, type=["file", "dataset", "dataverse"], start=0, rows=1000, page_limit=10
):
    """
    Plan is to use this and loop through list of hosts to get all metadata
    """


    # initial parameters
    page = 1
    all_items = []

    print(f"\n[metadata.request_metadata] Requesting metadata for {url_to_name(base)}")
    while True:
        # url for query
        url = f"{base.rstrip('/')}/api/search?q=*&start={start}"
        print(f"Query: {url}")

        try:
            # Get items and add to json of all items
            response = requests.get(url, timeout=15)
            response.raise_for_status()  # error for bad status codes
            data = response.json()

            # Check if response has expected structure
            if "data" not in data or "items" not in data["data"]:
                print(f"[metadata.request_metadata] WARNING: Unexpected response structure from {base}")
                break

            all_items.extend(data["data"]["items"])

            # see if there are more to query
            total = data["data"]["total_count"]
            start = start + rows

            # reset
            page += 1
            if start >= total or page > page_limit:
                break

        except requests.exceptions.RequestException as e:
            print(f"[metadata.request_metadata] ERROR: Request failed for {base}: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"[metadata.request_metadata] ERROR: Invalid JSON response from {base}: {e}")
            break

    return pd.DataFrame(all_items)

def url_to_name(url):
    return url.split('//')[1].split('.')[1]
