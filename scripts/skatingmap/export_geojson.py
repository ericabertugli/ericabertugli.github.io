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


def export_geojson(conn: sqlite3.Connection, way_type: str | None) -> dict:
    if way_type:
        cursor = conn.execute(
            "SELECT osm_id, way_type, name, geojson, tags FROM ways WHERE way_type = ?",
            (way_type,),
        )
    else:
        cursor = conn.execute(
            "SELECT osm_id, way_type, name, geojson, tags FROM ways"
        )

    features = []
    for osm_id, wtype, name, geojson, tags in cursor.fetchall():
        feature = {
            "type": "Feature",
            "properties": {
                "osm_id": osm_id,
                "way_type": wtype,
                "name": name,
                "tags": json.loads(tags) if tags else {},
            },
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
