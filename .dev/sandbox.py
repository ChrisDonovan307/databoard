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
df.info()
df.columns
df.head()
df.name_of_dataverse
df.name
df.global_id
df.installation.unique()

df.groupby('name')
df.iloc[0]
# does not include installation name!

# check installations
inst = pd.read_parquet('app/data/installations/installations.parquet')
inst.info()
inst.columns
inst.url
inst.doi_authority

