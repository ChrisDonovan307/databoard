from dagster import Definitions, define_asset_job, ScheduleDefinition
from pipeline.assets import installations, metadata

job = define_asset_job("refresh_all", selection=[installations, metadata])

schedule = ScheduleDefinition(job=job, cron_schedule="0 6 * * *")

defs = Definitions(assets=[installations, metadata], jobs=[job], schedules=[schedule])
