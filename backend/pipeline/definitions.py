from dagster import Definitions, define_asset_job
from pipeline.assets import (
    raw_installations,
    clean_installations,
    installation_geojson,
    metadata,
)

job = define_asset_job("refresh_all", selection=[raw_installations, metadata])

# schedule = ScheduleDefinition(job=job, cron_schedule="0 6 * * *")

defs = Definitions(
    assets=[raw_installations, clean_installations, installation_geojson, metadata],
    jobs=[job],
    # schedules=[schedule],
)
