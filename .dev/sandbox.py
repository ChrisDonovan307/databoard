import pandas as pd
import os

print(os.getcwd())

df = pd.read_csv('../data/installations/installations.csv')
df.columns
df.info()

continents = list(df.continent.unique())
type(continents)
continents.append('All')

# continents = ['All'] += df.continent.unique()
type(continents)
print(continents)

first_list = ['a', 'b']
first_list.append('c')
# second_list = [first_list, 'c']
print(first_list)
print(second_list)


#$ play with metadata --------------
import pandas as pd

df = pd.read_parquet('app/data/metadata/metadata.parquet')
df.info()
df.type.unique()

file_type = ['dataset', 'dataverse']
types = file_type.split(',')
types

f"type={types}"

string = []
for file_type in types:
  formatted = f"&type={file_type}"
  string.append(formatted)

string
pd.concat(string)


file_type = ['dataset', 'dataverse']
type_params = ''.join([f'&type={t}' for t in file_type])
type_params
f"something_{type_params}_something"


#$ explore parquet metadata -------------------
import pandas as pd
df = pd.read_parquet('app/data/metadata/metadata.parquet')
# df = pd.read_parquet('app/data/metadata_backup/metadata.parquet') # backup with most installations
df.info()
df.columns

# Check things
df.installation # we added this
df.installation.unique()
df.name_of_dataverse # dataverse rather than dataset presumably
df.name # the record itself
df.global_id # dois

# explore by file type
df.groupby('type').agg(
  count=('name', 'count'),
  unique_subjects=('subjects', 'nunique'),
  total_file_count=('fileCount', 'sum')
)
df.iloc[0]

# explore by installation
df.groupby(['installation', 'type']).agg(
  count=('name', 'count'),
  unique_subjects=('subjects', 'nunique'),
  total_file_count=('fileCount', 'sum')
).sort_values(by='count', ascending=False)

# Datasets only
ds = df[df['type'] == 'dataset']
ds.groupby('installation').agg(
  count=('installation', 'count'),
).sort_values('count', ascending=False)
# Capped out because we stopped at 2000

# Dataverses only
dv = df[df['type'] == 'dataverse']
dv.groupby('installation').agg(
  count=('installation', 'count'),
  dataset_count=('datasetCount', 'sum'),
).sort_values('dataset_count', ascending=False)


#$ Wrangle dataset for map -----------------------
# Want to group by installation, join with our existing installations data (by url?)
# get: dataverse count, dataset count, unique subject count
# url, 

inst = pd.read_parquet('app/data/installations/installations.parquet')
inst.info()
inst.columns
inst.name
inst.url

# group up our dataverse df
grouped = df.groupby('installation')

# join with inst data
inst.hostname
df.columns

# we need to keep URL in the df - installation name abbreviation isn't enough
# do this in next set of API calls
# THIS IS DONE NOW - we can match by installation_url. ayoooo
