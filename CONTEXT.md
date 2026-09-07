# Databoard

Databoard explores dataset and collection metadata harvested from installations of
the Dataverse Project. It pulls from Dataverse APIs, stores the result in a
relational database, and serves it as a map/chart dashboard.

## Language

**Installation**:
A single deployment of the Dataverse software at one institution, addressed by its
hostname (e.g. `dataverse.harvard.edu`). The top-level unit everything else is
harvested from.
_Avoid_: instance, site, host, repository

**Dataverse**:
A collection *inside* an installation that groups datasets (and sub-collections).
Always means the collection object, never the software or the project.
_Avoid_: collection, group

**Dataset**:
A published unit of research data within a dataverse, identified by a persistent
`global_id` (DOI/Handle), or by `identifier` when no `global_id` exists.
_Avoid_: study, deposit

**File**:
An individual data file belonging to a dataset. Not yet harvested; a planned
future scope.

**Record**:
One item as returned by the Dataverse Search API, before it is normalised into
installation / dataverse / dataset rows. The raw shape, not the stored shape.

**Search API**:
Dataverse's `/api/search` endpoint. The only source Databoard harvests from;
returns dataverse and dataset records (and files, unused so far) but a thinner
view than the native metadata API (e.g. authors come back as bare names).

**Watermark**:
The timestamp of the last successful pull for one installation. An incremental
pull asks the Search API only for records published after this point.
_Avoid_: cursor, checkpoint, high-water mark

**Full pull**:
A harvest of every available record for an installation, ignoring any watermark.
Used for first load and to repair a capped installation.

**Incremental pull**:
A harvest of only the records newer than an installation's watermark, upserted
into the existing data. The normal refresh mode.
_Avoid_: delta pull, sync

**Capped installation**:
An installation whose stored data was truncated by a page limit rather than
reaching its true total (Harvard being the standing example). A capped
installation is deliberately left without a watermark so the next pull refills it.
_Avoid_: partial installation, incomplete pull

**Orphan reference**:
A stored `parent_dataverse_identifier` that does not resolve to a known dataverse
row (sub-collection, or a parent from an installation not yet harvested). Kept as
a string and tolerated; the foreign key stays null until the parent appears.

**Lookup dedup**:
Collapsing repeated authors, keywords, subjects and publications into shared rows
by exact/normalised string match. The only deduplication done today.

**Canonical resolution**:
The future, fuzzy version of lookup dedup — merging "J. Smith" / "John Smith" and
similar into one canonical entity. Not yet done; the schema reserves a pointer for
it.

**Reconcile**:
A future full re-pull that compares current upstream records against stored ones
and marks vanished records inactive. Incremental pulls never see upstream
deletions, so nothing removes stale rows today.
