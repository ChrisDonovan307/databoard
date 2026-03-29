import pandas as pd
import json
from dotenv import load_dotenv
import os
import requests

#$ Setup
load_dotenv()
print(os.getenv('HELLO'))

print("test")

# Demo url
SERVER_URL = "https://demo.dataverse.org"
ID="root"


#$ Collections
query = SERVER_URL + "/api/search?q=trees"
print(query)

r = requests.get(query)
print(r)

print(r.json())
print(r.json()['data'])

print(r.json().keys())
print(r.json().items())

# Get df from the items array (the actual datasets)
items = r.json()['data']['items']
df = pd.json_normalize(items)
df.head()
df.info()
df.columns

df[['name', 'name_of_dataverse', 'authors']].head()
df.name_of_dataverse.unique()
