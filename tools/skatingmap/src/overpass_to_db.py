#!/usr/bin/env python3
"""
Fetch ways from Overpass API and store them in SQLite with GeoJSON geometry.

Usage:
    python overpass_to_db.py --query "way[surface=asphalt](41.35,2.10,41.42,2.20);" --type "smooth_asphalt"
    python overpass_to_db.py --query-file my_query.txt --type "bike_lanes"
"""

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DB_PATH = Path(__file__).parent.parent.parent / "data" / "skating_routes.db"
BBOX_FILE = Path(__file__).parent.parent / "queries" / "bbox.overpassql"


def _add_column_if_missing(conn: sqlite3.Connection, column: str, col_type: str) -> None:
    cursor = conn.execute("PRAGMA table_info(ways)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if column not in existing_columns:
        conn.execute(f"ALTER TABLE ways ADD COLUMN {column} {col_type}")


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ways (
            osm_id INTEGER PRIMARY KEY,
            way_type TEXT NOT NULL,
            name TEXT,
            geojson TEXT NOT NULL,
            tags TEXT
        )
    """)
    _add_column_if_missing(conn, "max_slope", "REAL")
    _add_column_if_missing(conn, "min_slope", "REAL")
    _add_column_if_missing(conn, "max_slope_start_lon", "REAL")
    _add_column_if_missing(conn, "max_slope_start_lat", "REAL")
    _add_column_if_missing(conn, "max_slope_end_lon", "REAL")
    _add_column_if_missing(conn, "max_slope_end_lat", "REAL")
    _add_column_if_missing(conn, "min_slope_start_lon", "REAL")
    _add_column_if_missing(conn, "min_slope_start_lat", "REAL")
    _add_column_if_missing(conn, "min_slope_end_lon", "REAL")
    _add_column_if_missing(conn, "min_slope_end_lat", "REAL")
    _add_column_if_missing(conn, "slope_enriched", "INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    return conn


def load_bbox_quadrants() -> list[str]:
    """Load bounding box from file and split into 4 quadrants to avoid overload overpass API (timeouts)."""
    if not BBOX_FILE.exists():
        return [""]

    bbox = BBOX_FILE.read_text().strip()
    south, west, north, east = map(float, bbox.split(","))
    mid_lat = (south + north) / 2
    mid_lon = (west + east) / 2

    quadrants = [
        f"{south},{west},{mid_lat},{mid_lon}",  # SW
        f"{south},{mid_lon},{mid_lat},{east}",  # SE
        f"{mid_lat},{west},{north},{mid_lon}",  # NW
        f"{mid_lat},{mid_lon},{north},{east}",  # NE
    ]
    return [f"[bbox:{q}]" for q in quadrants]


def fetch_overpass(query: str, bbox_setting: str = "", max_retries: int = 4, initial_delay: float = 30) -> dict:

    query = re.sub(r"\{\{style:.*?\}\}", "", query, flags=re.DOTALL).strip()
    query = re.sub(r"\[out:\w+\]", "", query).strip()
    query = re.sub(r"\[timeout:\d+\]", "", query).strip()
    query = re.sub(r"\[bbox:[^\]]+\]", "", query).strip()
    query = re.sub(r"out\s*(geom|body|skel|ids|meta|tags)?[^;]*;\s*$", "", query, flags=re.MULTILINE).strip()
    query = re.sub(r";+", ";", query)
    query = query.strip(";").strip()

    full_query = f"[out:json][timeout:300]{bbox_setting};{query};out geom;"

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(OVERPASS_URL, data={"data": full_query}, timeout=360)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 429 or status >= 500:
                if attempt < max_retries:
                    delay = initial_delay * (2 ** attempt)
                    print(f"Overpass API returned HTTP {status}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    continue
            raise SystemExit(f"Error: Overpass API returned HTTP {status}: {e.response.text[:200]}")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries:
                delay = initial_delay * (2 ** attempt)
                print(f"Request failed ({type(e).__name__}), retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                continue
            if isinstance(e, requests.exceptions.Timeout):
                raise SystemExit("Error: Overpass API request timed out. Try a smaller query area.")
            raise SystemExit("Error: Could not connect to Overpass API. Check your network connection.")
        except requests.exceptions.JSONDecodeError:
            raise SystemExit("Error: Overpass API returned invalid JSON response.")


def way_to_geojson(element: dict) -> dict:
    coordinates = [[node["lon"], node["lat"]] for node in element.get("geometry", [])]
    return {"type": "LineString", "coordinates": coordinates}


def store_ways(conn: sqlite3.Connection, elements: list, way_type: str) -> int:
    count = 0
    for el in elements:
        if el.get("type") != "way":
            continue
        osm_id = el["id"]
        tags = el.get("tags", {})
        name = tags.get("name")
        geojson = json.dumps(way_to_geojson(el))
        tags_json = json.dumps(tags)

        conn.execute(
            """
            INSERT OR REPLACE INTO ways (osm_id, way_type, name, geojson, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (osm_id, way_type, name, geojson, tags_json),
        )
        count += 1
    conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(description="Import Overpass ways to SQLite")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", help="Overpass query string")
    group.add_argument("--query-file", type=Path, help="File containing Overpass query")
    parser.add_argument("--type", required=True, dest="way_type", help="Way type label")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path")
    args = parser.parse_args()

    query = args.query or args.query_file.read_text().strip()
    bbox_quadrants = load_bbox_quadrants()

    conn = init_db(args.db)
    total_count = 0

    for i, bbox_setting in enumerate(bbox_quadrants, 1):
        print(f"Fetching quadrant {i}/{len(bbox_quadrants)} from Overpass API...")
        data = fetch_overpass(query, bbox_setting)
        count = store_ways(conn, data.get("elements", []), args.way_type)
        total_count += count
        print(f"  Stored {count} ways from quadrant {i}")

    conn.close()
    print(f"Total: {total_count} ways with type '{args.way_type}' in {args.db}")


if __name__ == "__main__":
    main()
