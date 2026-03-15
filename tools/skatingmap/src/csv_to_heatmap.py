#!/usr/bin/env python3
"""
Convert H3 cell counts CSV to a JSON array of [lat, lng] points for leaflet-heat.

Usage:
    python csv_to_heatmap.py h3_counts.csv -o heatmap_points.json --min-count 5
    python csv_to_heatmap.py h3_counts.csv -o heatmap_points.json --activity-type generic
"""

import argparse
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path

import h3

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def csv_to_heatmap_points(
    csv_path: Path, min_count: int, activity_filter: set[str] | None
) -> list[list[float]]:
    """Convert CSV with h3_cell,activity_type,count to a list of [lat, lng] points."""
    cell_counts: dict[str, int] = defaultdict(int)

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        has_activity_type = "activity_type" in reader.fieldnames

        for row in reader:
            if has_activity_type and activity_filter:
                if row["activity_type"] not in activity_filter:
                    continue
            cell_counts[row["h3_cell"]] += int(row["count"])

    points = []
    for cell_id, count in cell_counts.items():
        if count < min_count:
            continue
        try:
            lat, lng = h3.cell_to_latlng(cell_id)
            points.append([round(lat, 6), round(lng, 6)])
        except Exception as e:
            logger.warning(f"Failed to convert H3 cell: cell_id={cell_id}, error={e}")

    return points


def main():
    parser = argparse.ArgumentParser(
        description="Convert H3 CSV to heatmap points JSON"
    )
    parser.add_argument("csv_file", type=Path, help="Input CSV file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("heatmap_points.json"),
        help="Output JSON file",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=5,
        help="Minimum count threshold (default: 5)",
    )
    parser.add_argument(
        "-a",
        "--activity-type",
        nargs="+",
        dest="activity_types",
        help="Filter by activity type(s), e.g., --activity-type generic running",
    )
    args = parser.parse_args()

    if not args.csv_file.exists():
        raise SystemExit(f"Error: {args.csv_file} not found")

    activity_filter = set(args.activity_types) if args.activity_types else None
    filter_msg = (
        f", activity types: {', '.join(activity_filter)}" if activity_filter else ""
    )
    print(
        f"Converting {args.csv_file} to heatmap points "
        f"(min count: {args.min_count}{filter_msg})..."
    )

    points = csv_to_heatmap_points(args.csv_file, args.min_count, activity_filter)

    with open(args.output, "w") as f:
        json.dump(points, f)

    print(f"Wrote {len(points)} points to {args.output}")


if __name__ == "__main__":
    main()
