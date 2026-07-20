import json

with open("grillplatser.json") as f:
    data = json.load(f)

features = []
for r in data["results"]:
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(r["longitude"]), float(r["latitude"])]
        },
        "properties": {k: v for k, v in r.items() if k not in ("latitude", "longitude")}
    }
    features.append(feature)

geojson = {"type": "FeatureCollection", "features": features}

with open("grillplatser.geojson", "w") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)
