# Orchestrator

Heap of scripts to get Dataverse installation info and use it to download metadata for dataverses, datasets, and files stored in each installation.

Get help:

```
python -m app.services.orchestrator --help
```

Run everything:

```
python -m app.services.orchestrator --cmd all
```


## Installations

Pull a JSON file of Dataverse installations from the [Dataverse Installation Map](https://iqss.github.io/dataverse-installations/), which actually takes the file from [here](https://raw.githubusercontent.com/IQSS/dataverse-installations/main/data/data.json)

```
python -m app.services.orchestrator --cmd installations
```

Note that UVM is not on there yet. We are adding it manually with some janky metadata in the process.

## Metadata Refresh

To run metadata service:

```
python -m app.services.metadata --cmd metadata
```

This is set with page limit of 2 as a default. To pull everything:

```
python -m app.services.metadata --cmd metadata --page-limit=300
```

That will be enough to get all dataverses and collections (not files).

To enter URLs manually:

```
python -m app.services.metadata --cmd metadata --url-list https://dataverse.uvm.edu,https://dataverse.yale.edu
```

Or does this work

## Notes

- Metadata queries with Dataverse Search API are currently only pulling dataverses and datasets, not files. There are many files, a couple million in Harvard alone. If and when we want to get into this, we need to add it to the argparser to override the default in `request_metadata_async`.
- Having issues with Harvard, maybe other large dataverses timing out. Just set timeout to 60s, see if that helps?
