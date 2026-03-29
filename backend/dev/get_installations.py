import pandas as pd
import requests
from requests_cache import CachedSession
import json
import plotly.express as px
import plotly.graph_objects as go

# Indefinite caching by default
session = CachedSession()

print('hello')
print('hello')



#$ Request-------------------------------------------------- 

# Pull JSON file that informs map of Installations
url = 'https://raw.githubusercontent.com/IQSS/dataverse-installations/main/data/data.json'
res = session.get(url)

# Explore
dir(res)
type(res)
res.url
print(res.text)
type(res.text) # str
print(res.content)
type(res.content) # bytes
# text is what we want - json format

# Save JSON output to file
with open("data/installations/response.json", "w") as f:
    f.write(res.text)




#$ Parse--------------------------------------------------

# Format into JSON
data = res.json()
type(data)
print(data)
data.keys()
data['installations']

# Convert installations to DF
df = pd.DataFrame(data['installations'])
df.info()

# Check one
print(df.loc[0, ])
print(df.loc[1, ])

# Create a proper URL column
df["url"] = "https://" + df["hostname"]
df.url


#$ GeoJSON--------------------------------------------------

# Also convert into GeoJSON features to put into maps
df.info()
features = []
for _, row in df.iterrows():
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [row["lng"], row["lat"]]
        },
        "properties": {
            "name": row["name"],
            "hostname": row["hostname"],
            "metrics": row["metrics"],
            "url": url,
            "about": row.get("about"),
            "country": row.get("country"),
            "launch_year": row.get("launch_year"),
            "description": row.get("description"),
            "doi_authority": row.get("doi_authority"),
            "dv_hub_id": row.get("dv_hub_id")
        }
    }
    features.append(feature)

geojson_data = {
    "type": "FeatureCollection",
    "features": features
}
geojson_data['features'][0]
geojson_data['features'][1]


#$ Save--------------------------------------------------

# As csv
df.to_csv("data/installations/installations.csv", index=False)

# and GeoJSON
with open("data/installations/installations.geojson", "w") as f:
    f.write(json.dumps(geojson_data))

# test load
with open("data/installations/installations.geojson", "r") as f:
    geodat = json.load(f)

print(geodat)


#$ Map--------------------------------------------------

# Map with plotly express
df.info()

df['launch_year'] = df['launch_year'].astype(int)
df['years_since_launch'] = 2025 - df['launch_year']

df['metrics'] = df['metrics'].astype(bool)
sum(df.metrics) # all true

fig = px.scatter_map(
    df,
    lat="lat",
    lon="lng",
    hover_data=[ # called as customdata in update_layout for some reason
        "name", 
        "hostname",
        "launch_year",
    ],
    size='years_since_launch',
    size_max=25,
    zoom=2,
    # color="metrics",
    # color_discrete_sequence=["#000", "#fff"],
)

fig.update_layout(
    # carto-positron, carto-darkmatter, stamen-terrain, open-street-map
    map_style="carto-positron",
    # margin={"r":0,"t":0,"l":0,"b":0},
)

# Custom hover template
fig.update_traces(
    # custom_data=["hostname", "launch_year", "years_since_launch", "country", "doi_authority", "lat", "lng"],
    # custom_data=df[['name', 'hostname', 'launch_year', 'years_since_launch', 'country', 'doi_authority', 'lat', 'lng']],
    hovertemplate=
        "<b>%{customdata[0]}</b><br><br>" +
        "<b>Hostname:</b> %{customdata[1]}<br>" +
        "<b>Launch Year:</b> %{customdata[2]}<br>" +
        "<extra></extra>",
    hoverlabel=dict(
        bgcolor="white",
        font_size=16,
        font_color="black",
        font_family="Arial"
    ),
    marker=dict(
        opacity=0.8,
        # size=10,
    )
)

fig.show()
