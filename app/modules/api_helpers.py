# THIS IS OBSOLETE

import pandas as pd
import json
from dotenv import load_dotenv
import requests

def request_metadata(
    base, type=["file", "dataset", "dataverse"], start=0, rows=1000, page_limit=10
):
    """
    Plan is to use this and loop through list of hosts to get all metadata
    """
    # initial parameters
    page = 1
    all_items = []

    while True:
        # url for query
        url = f"{base.rstrip('/')}/api/search?q=*&start={start}"
        print(f"\nURL: {url}")

        # Get items and add to json of all items
        data = requests.get(url).json()
        all_items.extend(data["data"]["items"])

        # see if there are more to query
        total = data["data"]["total_count"]
        start = start + rows

        # reset
        page += 1
        if start >= total or page > page_limit:
            break

    return pd.DataFrame(all_items)

def url_to_name(url):
    return url.split('//')[1].split('.')[1]
