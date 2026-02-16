#!/usr/bin/env python3
"""
Fetch drinking water locations from Overpass API and save as GeoJSON.

Usage:
    python fetch_drinking_water.py
"""

import json
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX_FILE = Path(__file__).parent / "queries" / "bbox.overpassql"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "drinking_water.geojson"


def load_bbox() -> str:
    if BBOX_FILE.exists():
        return BBOX_FILE.read_text().strip()
    return "41.32,2.05,41.47,2.23"


def fetch_drinking_water(bbox: str) -> list:
    query = f"[out:json][timeout:120][bbox:{bbox}];node[amenity=drinking_water];out;"
    response = requests.post(OVERPASS_URL, data={"data": query}, timeout=180)
    response.raise_for_status()
    return response.json().get("elements", [])


def to_geojson(elements: list) -> dict:
    features = []
    for el in elements:
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [el["lon"], el["lat"]]},
            "properties": el.get("tags", {}),
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def main():
    bbox = load_bbox()
    print(f"Fetching drinking water locations (bbox: {bbox})...")
    elements = fetch_drinking_water(bbox)
    geojson = to_geojson(elements)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(geojson, indent=2))
    print(f"Saved {len(elements)} locations to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
