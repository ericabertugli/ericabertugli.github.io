#!/usr/bin/env python3
"""
Fetch drinking water locations from Overpass API and save as GeoJSON.

Usage:
    python fetch_drinking_water.py
"""

import json
import time
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX_FILE = Path(__file__).parent / "queries" / "bbox.overpassql"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "drinking_water.geojson"


def load_bbox() -> str:
    if BBOX_FILE.exists():
        return BBOX_FILE.read_text().strip()
    return "41.32,2.05,41.47,2.23"


def fetch_drinking_water(bbox: str, max_retries: int = 4, initial_delay: float = 30) -> list:
    query = f"[out:json][timeout:120][bbox:{bbox}];node[amenity=drinking_water];out;"
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(OVERPASS_URL, data={"data": query}, timeout=180)
            response.raise_for_status()
            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                print(f"Error: Failed to parse Overpass API response as JSON: {exc}")
                return []
            return data.get("elements", [])
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code
            if (status == 429 or status >= 500) and attempt < max_retries:
                delay = initial_delay * (2 ** attempt)
                print(f"Overpass API returned HTTP {status}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                continue
            print(f"Error: Overpass API returned an HTTP error response: {exc}")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            if attempt < max_retries:
                delay = initial_delay * (2 ** attempt)
                print(f"Request failed ({type(exc).__name__}), retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                continue
            if isinstance(exc, requests.exceptions.Timeout):
                print("Error: Request to Overpass API timed out. Please try again later.")
            else:
                print("Error: Failed to connect to Overpass API. Please check your network connection.")
        except requests.exceptions.RequestException as exc:
            print(f"Error: An unexpected error occurred while contacting the Overpass API: {exc}")
        return []


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
