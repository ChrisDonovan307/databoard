import argparse

from services.installations import * 
from services.metadata import * 


def parse_args():
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
        type=lambda s: s if s == 'installations' else [u.strip() for u in s.split(',')],
        default='installations',
        help="(metadata) If 'installations', uses whole set of installations. Otherwise, add them manually as list, \
            separated by commas ('https://dataverse.harvard.edu,https://dataverse.ucla.edu') \
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
        default=False,
        help="(metadata) Do not save parquet or csv files (default: --save)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="(metadata) Timeout length in seconds. 180 works for most, but larger dataverse still time out, like Harvard. (default: 180)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.cmd in ('installations', 'all'):
        Installation().call()
    if args.cmd in ('metadata', 'all'):
        Metadata(
            start=args.start,
            per_page=args.per_page,
            page_limit=args.page_limit,
            url_list=args.url_list,
            save=not args.no_save,
            timeout=args.timeout,
        ).call()


if __name__ == "__main__":
    main()