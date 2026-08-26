# Orchestrator

Heap of scripts to get Dataverse installation info and use it to download metadata for dataverses, datasets, and files stored in each installation.

Get help:

```
python -m services.orchestrator --help
```

Run everything:

```
python -m services.orchestrator --cmd all
```

## Dagster

Root is `backend/pipeline`. Assets are persistent, found in `backend/storage`.

To run from `/backend`:

```
dg dev
```

## Installations

Pull a JSON file of Dataverse installations from the [Dataverse Installation Map](https://iqss.github.io/dataverse-installations/), which actually takes the file from [here](https://raw.githubusercontent.com/IQSS/dataverse-installations/main/data/data.json)

```
python -m services.orchestrator --cmd installations
```

Note that UVM is not on there yet. We are adding it manually with some janky metadata in the process.

## Metadata Refresh

This pulls both dataverses and datasets, distinguished by the `type` column. Can specify for orchestrator

To run metadata service:

```
python -m services.orchestrator --cmd metadata
```

This is set with page limit of 2 as a default. To pull everything, add a large page limit:

```
python -m services.orchestrator --cmd metadata --page-limit=300
```

That will be enough to get all dataverses and collections (not files).

To enter URLs manually:

```
python -m services.orchestrator --cmd metadata --file-type datasets --url-list https://dataverse.uvm.edu,https://dataverse.yale.edu
```

### Incremental updates

Add `--incremental` to only fetch records newer than the last successful pull per installation (watermark tracked in `data/state/last_pull.json`), appending and deduping into existing metadata files instead of overwriting. Falls back to a full pull per installation if no watermark exists yet or the filtered query fails.

```
python -m services.orchestrator --cmd metadata --incremental
```

### Checking installation sizes ahead of time

The installations list itself doesn't carry record counts (its `metrics` field is just a bool for "has a metrics API"). To see which installations are large before running a real pull, use `--cmd sizes` — one cheap `per_page=1` request per installation, sorted by `total_count`:

```
python -m services.orchestrator --cmd sizes
```

Saves to `logs/installation_sizes.csv`. Use it to set `--page-limit`/`--timeout`/`--page-delay` for known-large installations like Harvard.

### Large installations (Harvard, etc.) and rate limiting

Pagination against a single installation now sleeps `--page-delay` seconds (default 0.2s) between requests, and retries individual pages up to `--max-retries` times (default 3, exponential backoff, honors `Retry-After`) on HTTP 429/5xx before giving up. If retries are exhausted or another error occurs, whatever was already fetched for that installation is kept (logged as `PARTIAL`) instead of being discarded — with `--incremental`, a partial pull's watermark isn't advanced, so the next incremental run picks up where it left off.

If you're still seeing timeouts on very large installations, raise `--timeout` and/or `--page-delay`:

```
python -m services.orchestrator --cmd metadata --url-list https://dataverse.harvard.edu --page-limit 300 --timeout 300 --page-delay 0.5
```

## Notes

- Metadata queries with Dataverse Search API are currently only pulling dataverses and datasets, not files. There are many files, a couple million in Harvard alone. If and when we want to get into this, we need to add it to the argparser to override the default in `request_metadata_async`.
