import pandas as pd
import json
from dotenv import load_dotenv
import os
import re
import requests


# $ Setup
print(os.getcwd())

ROOT = os.path.dirname(os.path.abspath(__name__))
env_path = os.path.join(ROOT, ".env")
print(env_path)
load_dotenv(os.path.join(ROOT, ".env"))
print(os.getenv("HELLO"))
print(os.getenv("API_KEY"))


# $ Demo -----
url = f"{os.getenv('DEMO_URL')}/api/access/dataset/:persistentId/versions/{os.getenv('DEMO_VERSION')}?persistentId={os.getenv('DEMO_PID')}"
print(url)
# params = {"persistentId": os.getenv('DEMO_PID')}
# print(params)
# headers = {"X-Dataverse-key": os.getenv("API_KEY")}
print(headers)

r = requests.get(
    url,
    # params=params,
    # headers=headers,
)
print(r)
r.content

#$ Demo again -----
url = 'https://demo.dataverse.org/api/search?q=trees'
print(url)

r = requests.get(
    url,
)
print(r)
r.content


#$ ASU -----
url = 'https://dataverse.asu.edu/api/search?q=*'
print(url)

r = requests.get(
    url,
)
print(r)
r.content
r.status_code
r.text
dir(r)
r.content['data']

# Format into JSON
data = r.json()
type(data)
print(data)
data.keys()
data['status']
data["data"]
data["data"].keys()

# Explore
data['data']
data['data'].keys()
data['data']['total_count']
data['data']['q']
data['data']['items'] # actual things

# Pretty print
print(json.dumps(data, indent=2))

# Convert installations to DF
df = pd.DataFrame(data['data']['items'])
df.info()



# $ UVM -----
url = f"{os.getenv('UVM_URL')}/api/search?q=*"
print(url)
# params = {"persistentId": os.getenv('DEMO_PID')}
# print(params)
headers = {"X-Dataverse-key": os.getenv("API_KEY")}
print(headers)

r = requests.get(
    url,
    # params=params,
    # headers=headers,
)
print(r)
r.content
# UVM search API doesn't work?


#$ check function ----
import importlib
from app.modules import api_helpers
importlib.reload(api_helpers)
from app.modules.api_helpers import request_metadata, url_to_name

url = 'https://dataverse.asu.edu'
df = request_metadata(base = url, page_limit = 2)
print(df)


## try it with two hosts
urls = [
    'https://dataverse.asu.edu',
    'https://dataverse.harvard.edu'
]
[url_to_name(u) for u in urls]

# Make dictionary of DFs
dfs = {
    url_to_name(url): request_metadata(base=url, page_limit=2)
    for url in urls
}

dfs.keys()
dfs['asu'].info()
dfs['harvard'].info()
