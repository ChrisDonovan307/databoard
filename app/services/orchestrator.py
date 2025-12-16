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

def refresh_metadata(start=0, per_page=1000, page_limit=2, url_list='installations', save=True):
    """
    Using list of installations, get metadata for stored collections for each one
    """
    urls = metadata_setup(url_list=url_list)
    pull_combine_save(
        urls,
        start=start,
        per_page=per_page,
        page_limit=page_limit,
        save=save
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog="Orchestrator",
        description="Run sets of functions to refresh metadata from Dataverse with API calls."
    )
    parser.add_argument(
        "--cmd",
        required=True,
        choices=["installations", "metadata", "all"],
        default='all',
        help="Which set of functions to run. \
            'installations': pull list of installations from Dataverse map. \
            'metadata': use Dataverse search API to get metadata from each Dataverse, combine, and save. \
            (default: all)"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="(metadata) Starting record for pagination. Mostly used internally. (default: 0)"
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=1000,
        help="(metadata) Number of records per query. This caps out at 1000 for the Dataverse Search API. (default: 1000)"
    )
    parser.add_argument(
        "--url-list",
        type=str,
        default='installations',
        help="(metadata) If 'installations', uses whole set of installations. Otherwise, add them manually as list, \
            separated by commas (https://dataverse.harvard.edu,https://dataverse.ucla.edu) \
            (default: installations)"
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        default=2,
        help="(metadata) Maximum number of pages to fetch (default: 2)"
    )
    parser.add_argument(
        "--file-type",
        type=str,
        default='dataverse,dataset',
        help="(metadata) File types for which to query, separated by commas. Options are dataverse, dataset, file. \
            Arg input should be comma separated (dataverse,file). \
            (default: dataverse,dataset)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        default=True,
        help="(metadata) Do not save parquet or csv files (default: --save)"
    )
    args = parser.parse_args()


    ## pre parsing? post parsing
    if args.url_list == 'installations':
        url_list = 'installations'
    else:
        url_list = [url.strip() for url in args.url_list.split(',')]
    
    save = args.no_save == True


    ## run commands
    if args.cmd == "metadata":
        refresh_metadata(
            start=args.start, 
            per_page=args.per_page, 
            page_limit=args.page_limit,
            url_list=url_list,
            save=save
        )
    elif args.cmd == "installations":
        refresh_installations()
    elif args.cmd == 'all':
        refresh_installations()
        refresh_metadata(
            start=args.start, 
            per_page=args.per_page, 
            page_limit=args.page_limit,
            url_list=url_list,
            save=save
        )
