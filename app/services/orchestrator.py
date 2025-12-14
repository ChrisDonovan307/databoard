from app.services.installations import * 
from app.services.metadata import * 

def refresh_installations():
    """
    Refresh all installations data: fetch from API, save as JSON, parquet, and GeoJSON
    """
    res = get_installations()
    save_installations_json(res)
    df = get_installations_df(res)
    save_installations_parquet(df)
    save_installations_geojson(df)
    save_installations_csv(df)

def refresh_metadata(start=0, rows=1000, page_limit=2):
    """
    Using list of installations, get metadata for stored collections for each one
    """
    urls = metadata_setup()
    pull_combine_save(
        urls,
        start=start,
        rows=rows,
        page_limit=page_limit
    )

if __name__ == "__main__":
    refresh_installations()

    # for adding arguments
    import argparse
    parser = argparse.ArgumentParser(
        prog="Orchestrator",
        description="Run sets of functions to refresh metadata from Dataverse with API calls."
    )
    parser.add_argument(
        "--cmd",
        required=True,
        choices=["installations", "metadata", "all"],
        help="Which set of functions to run. \
            'installations': pull list of installations from Dataverse map. \
            'metadata': use Dataverse search API to get metadata from each Dataverse, combine, and save."
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Starting record for pagination (default: 0)"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=1000,
        help="Number of rows per query (default: 1000)"
    )
    parser.add_argument(
        "--page_limit",
        type=int,
        default=2,
        help="Maximum number of pages to fetch (default: 2)"
    )

    args = parser.parse_args()

    if args.cmd == "metadata":
        refresh_metadata(start=args.start, rows=args.rows, page_limit=args.page_limit)
    elif args.cmd == "installations":
        refresh_installations()
    elif args.cmd == 'all':
        refresh_installations()
        refresh_metadata(start=args.start, rows=args.rows, page_limit=args.page_limit)
