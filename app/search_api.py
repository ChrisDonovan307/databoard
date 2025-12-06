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


# $ Demo -----
url = f"{os.getenv('DEMO_URL')}/api/access/dataset/:persistentId/versions/{os.getenv('DEMO_VERSION')}?persistentId={os.getenv('DEMO_PID')}"
print(url)
# params = {"persistentId": os.getenv('DEMO_PID')}
# print(params)
headers = {"X-Dataverse-key": os.getenv("API_KEY")}
print(headers)

r = requests.get(
    url,
    # params=params,
    headers=headers,
)
print(r)
r.content


# $ UVM -----
url = f"https://{os.getenv('UVM_URL')}/api/search?q=atlas"
print(url)
# params = {"persistentId": os.getenv('DEMO_PID')}
# print(params)
headers = {"X-Dataverse-key": os.getenv("API_KEY")}
print(headers)

r = requests.get(
    url,
    # params=params,
    headers=headers,
)
print(r)
r.content
