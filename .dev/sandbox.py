import pandas as pd
import os

print(os.getcwd())

df = pd.read_csv("../data/installations/installations.csv")
df.columns
df.info()

continents = list(df.continent.unique())
type(continents)
continents.append("All")

# continents = ['All'] += df.continent.unique()
type(continents)
print(continents)

first_list = ["a", "b"]
first_list.append("c")
# second_list = [first_list, 'c']
print(first_list)
print(second_list)


# $ play with metadata --------------
import pandas as pd

df = pd.read_parquet("app/data/metadata/metadata.parquet")
df.info()
df.type.unique()

file_type = ["dataset", "dataverse"]
types = file_type.split(",")
types

f"type={types}"

string = []
for file_type in types:
    formatted = f"&type={file_type}"
    string.append(formatted)

string
pd.concat(string)


file_type = ["dataset", "dataverse"]
type_params = "".join([f"&type={t}" for t in file_type])
type_params
f"something_{type_params}_something"


# $ explore parquet metadata -------------------
import pandas as pd
df = pd.read_parquet("app/data/metadata/metadata.parquet")
# df = pd.read_parquet('app/data/metadata_backup/metadata.parquet') # backup with most installations
df.info()
df.columns

# Check things
df.installation  # we added this
df.installation.unique()
df.name_of_dataverse  # dataverse rather than dataset presumably
df.name  # the record itself
df.global_id  # dois

# explore by file type
df.groupby("type").agg(
    count=("name", "count"),
    unique_subjects=("subjects", "nunique"),
    total_file_count=("fileCount", "sum"),
)
df.iloc[0]

# explore by installation
df.groupby(["installation", "type"]).agg(
    count=("name", "count"),
    unique_subjects=("subjects", "nunique"),
    total_file_count=("fileCount", "sum"),
).sort_values(by="count", ascending=False)

# Datasets only
ds = df[df["type"] == "dataset"]
ds_agg = ds.groupby("installation_url").agg(
    count=("installation", "count"),
).sort_values("count", ascending=False)
# Capped out because we stopped at 2000

# Dataverses only
dv = df[df["type"] == "dataverse"]
dv.groupby("installation_url").agg(
    count=("installation", "count"),
    dataset_count=("datasetCount", "sum"),
).sort_values("dataset_count", ascending=False)


# $ Wrangle dataset for map -----------------------
# Want to group by installation, join with our existing installations data (by url?)
# get: dataverse count, dataset count, unique subject count
# url,

inst = pd.read_parquet("app/data/installations/installations.parquet")
inst.info()
inst.columns
inst.name
inst.url

# group up our dataverse df
grouped = df.groupby("installation")

# join with inst data using urls
inst.url
df.installation_url


# we need to keep URL in the df - installation name abbreviation isn't enough
# do this in next set of API calls
# THIS IS DONE NOW - we can match by installation_url. ayoooo


# do we have harvard
def url_to_name(url):
    return url.split("//")[1].split(".")[1]

"https://dataverse.harvard.edu" in df["installation_url"]

# convert to names before checking
a = df.installation_url.apply(url_to_name)
b = inst.url.apply(url_to_name)
set(a) - set(b)
missing = set(b) - set(a)
missing
len(missing) # 31 missing?

# check uniques in each
a.nunique()
b.nunique()
b.nunique() - a.nunique()
# yep 31 missing


# combine
ds.columns
inst.columns
datasets = ds.merge(
    inst, 
    how='right', 
    left_on='installation_url', 
    right_on='url',
    suffixes=('_ds', '_inst')
)
datasets.info()
datasets[['count', 'url']]
datasets[['name_inst', 'installation_url']]
datasets.name_inst

# lose dataset count - that is for dataverse DF
datasets.drop('datasetCount', axis=1, inplace=True)
datasets.info()

# save to clean datasets
datasets.to_parquet('app/data/clean/datasets.parquet')


#$ Condense? -----------------------------------------
# grouping this by installation to get summary stats

# This is from metadata
datasets.columns.sort_values()
agg = datasets.groupby("name_inst", as_index=False).agg(
    n_datasets=("installation", "count"),
    n_files=("fileCount", "sum"),
    n_authors=('authors', 'nunique'),
    n_subjects=('subjects', 'nunique'),
    n_keywords=('keywords', 'nunique'),
    # n_publications=('publications', lambda x: sum(x != 'nan')), # these are fucked up?
    n_publishers=('publisher', 'nunique'),
).sort_values("n_datasets", ascending=False) \
    .reset_index(drop=True)

agg[['inst_name', 'n_datasets']].head()
agg.head()
agg.info()
agg.columns

# combine back with inst
summary = inst.merge(
    agg,
    how="left",
    left_on="name",
    right_on="name_inst",
).drop('name_inst', axis=1)
summary.columns
summary.head()
summary[['name', 'n_files']]

# save this as installation summary data
summary.to_parquet('app/data/clean/installation_stats.parquet')

