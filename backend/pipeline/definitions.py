from dagster import Definitions, define_asset_job
from pipeline.assets import (
    raw_installations,
    clean_installations,
    installation_geojson,
    uvm_meta_datasets,
)

job = define_asset_job("refresh_all", selection=[raw_installations, uvm_meta_datasets])

# schedule = ScheduleDefinition(job=job, cron_schedule="0 6 * * *")

defs = Definitions(
    assets=[
        raw_installations,
        clean_installations,
        installation_geojson,
        uvm_meta_datasets,
    ],
    jobs=[job],
    # schedules=[schedule],
)
