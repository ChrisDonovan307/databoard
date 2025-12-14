from app.services.installations import * 

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

if __name__ == "__main__":
    refresh_installations()

    # for when we have multiple operations:
    # import argparse
    # parser = argparse.ArgumentParser(description="Run specific refresh functions.")
    # parser.add_argument(
    #     "function",
    #     choices=["installations", "metadata", "all"],
    #     help="Which refresh function to run"
    # )

    # args = parser.parse_args()

    # if args.function == "metadata":
    #     refresh_metadata()
    # elif args.function == "installations":
    #     refresh_installations()
    # elif args.function == 'all':
    #     refresh_installations()
    #     refresh_metadata()
