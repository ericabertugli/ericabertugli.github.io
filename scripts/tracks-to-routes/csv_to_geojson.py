#!/usr/bin/env python3
"""
Convert H3 cell counts CSV to GeoJSON with polygon boundaries.

Usage:
    python csv_to_geojson.py h3_counts.csv -o heatmap.geojson --min-count 5
    python csv_to_geojson.py h3_counts.csv -o heatmap.geojson --activity-type generic running
"""

import argparse
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path

import h3

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def cell_to_polygon(cell_id: str) -> list:
    """Convert H3 cell to GeoJSON polygon coordinates."""
    boundary = h3.cell_to_boundary(cell_id)
    coords = [[lng, lat] for lat, lng in boundary]
    coords.append(coords[0])
    return [coords]


def csv_to_geojson(
    csv_path: Path, min_count: int, activity_filter: set[str] | None
) -> dict:
    """Convert CSV with h3_cell,activity_type,count to GeoJSON FeatureCollection."""
    cell_counts = defaultdict(int)

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        has_activity_type = "activity_type" in reader.fieldnames

        for row in reader:
            if has_activity_type and activity_filter:
                if row["activity_type"] not in activity_filter:
                    continue
            cell_counts[row["h3_cell"]] += int(row["count"])

    features = []
    for cell_id, count in cell_counts.items():
        if count < min_count:
            continue
        try:
            polygon = cell_to_polygon(cell_id)
            features.append({
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": polygon},
            })
        except Exception as e:
            logger.warning(
                f"Failed to convert H3 cell to polygon: "
                f"cell_id={cell_id}, error={e}"
            )

    return {"type": "FeatureCollection", "features": features}


def main():
    parser = argparse.ArgumentParser(description="Convert H3 CSV to GeoJSON")
    parser.add_argument("csv_file", type=Path, help="Input CSV file")
    parser.add_argument("-o", "--output", type=Path, default=Path("heatmap.geojson"), help="Output GeoJSON file")
    parser.add_argument("--min-count", type=int, default=5, help="Minimum count threshold (default: 5)")
    parser.add_argument(
        "-a", "--activity-type", nargs="+", dest="activity_types",
        help="Filter by activity type(s), e.g., --activity-type generic running"
    )
    args = parser.parse_args()

    if not args.csv_file.exists():
        raise SystemExit(f"Error: {args.csv_file} not found")

    activity_filter = set(args.activity_types) if args.activity_types else None
    filter_msg = f", activity types: {', '.join(activity_filter)}" if activity_filter else ""
    print(f"Converting {args.csv_file} to GeoJSON (min count: {args.min_count}{filter_msg})...")

    geojson = csv_to_geojson(args.csv_file, args.min_count, activity_filter)

    with open(args.output, "w") as f:
        json.dump(geojson, f)

    print(f"Wrote {len(geojson['features'])} features to {args.output}")


if __name__ == "__main__":
    main()
