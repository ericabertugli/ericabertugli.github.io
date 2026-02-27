#!/usr/bin/env python3
"""
Fetch skate parks and pump tracks from Overpass API and save as GeoJSON.

Usage:
    python fetch_skate_pois.py
"""

import json
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX_FILE = Path(__file__).parent / "queries" / "bbox.overpassql"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "skate_pois.geojson"


def load_bbox() -> str:
    if BBOX_FILE.exists():
        return BBOX_FILE.read_text().strip()
    return "41.32,2.05,41.47,2.23"


def fetch_skate_pois(bbox: str) -> list:
    query = f"""
    [out:json][timeout:120][bbox:{bbox}];
    (
      node["sport"~"skateboard|roller_skating"];
      way["sport"~"skateboard|roller_skating"];
      node["cycling"="pump_track"];
      way["cycling"="pump_track"];
    );
    out center;
    """
    response = requests.post(OVERPASS_URL, data={"data": query}, timeout=180)
    response.raise_for_status()
    return response.json().get("elements", [])


def get_poi_type(tags: dict) -> str:
    if tags.get("cycling") == "pump_track":
        return "pump_track"
    sport = tags.get("sport", "")
    if "roller_skating" in sport:
        return "skate_park"
    if "skateboard" in sport:
        return "skate_park"
    return "skate_park"


def get_image_url(tags: dict) -> str:
    if "wikimedia_commons" in tags:
        filename = tags["wikimedia_commons"].replace("File:", "").replace(" ", "_")
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=300"
    if "image" in tags:
        return tags["image"]
    return ""


def to_geojson(elements: list) -> dict:
    features = []
    for el in elements:
        if el["type"] == "way":
            lat = el.get("center", {}).get("lat")
            lon = el.get("center", {}).get("lon")
        else:
            lat = el.get("lat")
            lon = el.get("lon")

        if lat is None or lon is None:
            continue

        tags = el.get("tags", {})
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "name": tags.get("name", ""),
                "poi_type": get_poi_type(tags),
                "sport": tags.get("sport", ""),
                "surface": tags.get("surface", ""),
                "image": get_image_url(tags),
            },
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def main():
    bbox = load_bbox()
    print(f"Fetching skate parks and pump tracks (bbox: {bbox})...")
    elements = fetch_skate_pois(bbox)
    geojson = to_geojson(elements)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(geojson, indent=2))
    print(f"Saved {len(geojson['features'])} POIs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
