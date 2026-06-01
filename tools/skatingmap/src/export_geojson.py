#!/usr/bin/env python3
"""
Export ways from SQLite to GeoJSON file for use in Leaflet map.

Usage:
    python export_geojson.py                          # Export all ways
    python export_geojson.py --type smooth_asphalt    # Export specific type
    python export_geojson.py --list-types             # List available types
"""

import argparse
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "skating_routes.db"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "routes.geojson"


def list_types(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute("SELECT DISTINCT way_type FROM ways ORDER BY way_type")
    return [row[0] for row in cursor.fetchall()]


def _build_segment(start_lon, start_lat, end_lon, end_lat) -> dict | None:
    """Build GeoJSON LineString from segment coordinates."""
    if None in (start_lon, start_lat, end_lon, end_lat):
        return None
    return {
        "type": "LineString",
        "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
    }


def export_geojson(conn: sqlite3.Connection, way_type: str | None) -> dict:
    query = """
        SELECT osm_id, way_type, name, geojson, tags,
               max_slope, min_slope,
               max_slope_start_lon, max_slope_start_lat,
               max_slope_end_lon, max_slope_end_lat,
               min_slope_start_lon, min_slope_start_lat,
               min_slope_end_lon, min_slope_end_lat
        FROM ways
    """
    if way_type:
        cursor = conn.execute(query + " WHERE way_type = ?", (way_type,))
    else:
        cursor = conn.execute(query)

    features = []
    for row in cursor.fetchall():
        (
            osm_id, wtype, name, geojson, tags,
            max_slope, min_slope,
            max_start_lon, max_start_lat, max_end_lon, max_end_lat,
            min_start_lon, min_start_lat, min_end_lon, min_end_lat,
        ) = row

        properties = {
            "osm_id": osm_id,
            "way_type": wtype,
            "name": name,
            "tags": json.loads(tags) if tags else {},
        }

        if max_slope is not None:
            properties["max_slope"] = round(max_slope, 1)
            properties["max_slope_segment"] = _build_segment(
                max_start_lon, max_start_lat, max_end_lon, max_end_lat
            )

        if min_slope is not None:
            properties["min_slope"] = round(min_slope, 1)
            properties["min_slope_segment"] = _build_segment(
                min_start_lon, min_start_lat, min_end_lon, min_end_lat
            )

        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": json.loads(geojson),
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def main():
    parser = argparse.ArgumentParser(description="Export ways to GeoJSON")
    parser.add_argument("--type", dest="way_type", help="Filter by way type")
    parser.add_argument("--list-types", action="store_true", help="List available types")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path")
    parser.add_argument("--output", "-o", type=Path, default=OUTPUT_PATH, help="Output file")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Database not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)

    if args.list_types:
        types = list_types(conn)
        print("Available way types:")
        for t in types:
            print(f"  - {t}")
        conn.close()
        return

    geojson = export_geojson(conn, args.way_type)
    conn.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(geojson, indent=2))
    print(f"Exported {len(geojson['features'])} features to {args.output}")


if __name__ == "__main__":
    main()
