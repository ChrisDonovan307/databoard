import argparse

from services.installations import Installation
from services.metadata import Metadata


def parse_args():
    parser = argparse.ArgumentParser(
        prog="Orchestrator",
        description="Run sets of functions to refresh metadata from Dataverse with API calls.",
    )
    parser.add_argument(
        "--cmd",
        required=True,
        choices=["init-db", "load-parquet", "installations", "metadata", "sizes", "all"],
        default="all",
        help="Which set of functions to run. \
            'init-db': create the MySQL schema (Base.metadata.create_all). \
            'load-parquet': one-time initial load of data/metadata/metadata.parquet into MySQL. \
            'installations': pull list of installations from Dataverse map into the installation table. \
            'metadata': use Dataverse search API to get metadata from each Dataverse and upsert into MySQL. \
            'sizes': cheap per_page=1 probe of each installation's total_count, saved to logs/installation_sizes.csv, \
            to see which installations are large before running a real pull. \
            (default: all)",
    )
    parser.add_argument(
        "--dump-page-limit",
        type=int,
        default=300,
        help="(load-parquet) The --page-limit that produced metadata.parquet. Installations "
        "whose row count reached page_limit*per_page are treated as capped and left "
        "un-watermarked. (default: 300)",
    )
    parser.add_argument(
        "--export-parquet",
        metavar="PATH",
        default=None,
        help="Dump the dataset/dataverse tables to a flat parquet at PATH and exit. "
        "Offline-sharing helper, not part of the pipeline.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="(metadata) Starting record for pagination. Mostly used internally. (default: 0)",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=1000,
        help="(metadata) Number of records per query. This caps out at 1000 for the Dataverse Search API. (default: 1000)",
    )
    parser.add_argument(
        "--url-list",
        type=lambda s: s if s == "installations" else [u.strip() for u in s.split(",")],
        default="installations",
        help="(metadata) If 'installations', uses whole set of installations. Otherwise, add them manually as list, \
            separated by commas ('https://dataverse.harvard.edu,https://dataverse.ucla.edu') \
            (default: installations)",
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        default=2,
        help="(metadata) Maximum number of pages to fetch (default: 2)",
    )
    parser.add_argument(
        "--file-type",
        type=str,
        default="dataverse,dataset",
        help="(metadata) File types for which to query, separated by commas. Options are dataverse, dataset, file. \
            Arg input should be comma separated (dataverse,file). \
            (default: dataverse,dataset)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        default=False,
        help="(metadata) Do not save parquet or csv files (default: --save)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="(metadata) Timeout length in seconds. 180 works for most, but larger dataverse still time out, like Harvard. (default: 180)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=False,
        help="(metadata) Only fetch items newer than the last successful pull per installation \
            (tracked in data/state/last_pull.json), and append+dedupe into existing metadata \
            files instead of overwriting. Falls back to a full pull per installation if no \
            watermark exists yet or the filtered query fails. (default: full overwrite pull)",
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=0.2,
        help="(metadata) Seconds to sleep between paginated requests to the same installation, \
            to avoid rate limiting on large installations. (default: 0.2)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="(metadata) Max retry attempts per page on HTTP 429/5xx responses, with exponential \
            backoff (honors Retry-After if present). (default: 3)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.export_parquet:
        Metadata.export_parquet(args.export_parquet)
        return

    if args.cmd == "init-db":
        from db.schema_init import create_all

        create_all()
        print("Schema created.")
        return
    if args.cmd == "load-parquet":
        from services.loader import load_parquet_dump

        load_parquet_dump(
            dump_page_limit=args.dump_page_limit, per_page=args.per_page
        )
        return

    if args.cmd in ("installations", "all"):
        Installation().call()
    if args.cmd == "sizes":
        Metadata(url_list=args.url_list, timeout=args.timeout).probe_and_save_sizes()
    if args.cmd in ("metadata", "all"):
        Metadata(
            start=args.start,
            per_page=args.per_page,
            page_limit=args.page_limit,
            url_list=args.url_list,
            save=not args.no_save,
            timeout=args.timeout,
            incremental=args.incremental,
            page_delay=args.page_delay,
            max_retries=args.max_retries,
        ).call()


if __name__ == "__main__":
    main()
