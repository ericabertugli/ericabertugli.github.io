#!/usr/bin/env python3
"""
Generate heatmap GeoJSON from .fit files in one command.

Usage:
    generate-heatmap /path/to/fit/files -o output.geojson
    generate-heatmap /path/to/fit/files -d 5 --min-count 3 -o output.geojson
"""

import argparse
import tempfile
from pathlib import Path

from csv_to_geojson import csv_to_geojson
from fit_to_h3 import process_fit_folder, write_csv


def main():
    parser = argparse.ArgumentParser(
        description="Generate heatmap GeoJSON from .fit files"
    )
    parser.add_argument("folder", type=Path, help="Folder containing .fit files")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("heatmap.geojson"),
        help="Output GeoJSON file"
    )
    parser.add_argument(
        "-r", "--resolution", type=int, default=11,
        help="H3 resolution (0-15, default: 11)"
    )
    parser.add_argument(
        "-d", "--densify", type=float, dest="densify_interval", metavar="METERS",
        help="Interpolate points every N meters (recommended: 5)"
    )
    parser.add_argument(
        "-a", "--activity-type", nargs="+", dest="activity_types",
        help="Filter by activity type(s), e.g., --activity-type generic"
    )
    parser.add_argument(
        "--min-count", type=int, default=3,
        help="Minimum visit count to include cell (default: 3)"
    )
    args = parser.parse_args()

    if not args.folder.is_dir():
        raise SystemExit(f"Error: {args.folder} is not a directory")

    if not 0 <= args.resolution <= 15:
        raise SystemExit("Error: Resolution must be between 0 and 15")

    activity_filter = set(args.activity_types) if args.activity_types else None

    print(f"Processing .fit files from {args.folder}")
    print(f"  Resolution: {args.resolution}, Densify: {args.densify_interval or 'off'}m")
    print(f"  Min count: {args.min_count}, Activity filter: {activity_filter or 'all'}")

    counter = process_fit_folder(
        args.folder, args.resolution, activity_filter, args.densify_interval
    )

    if not counter:
        print("No GPS data found")
        return

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        csv_path = Path(f.name)

    write_csv(counter, csv_path)
    print(f"Intermediate CSV: {len(counter)} cells")

    import json
    geojson = csv_to_geojson(csv_path, args.min_count, activity_filter)

    with open(args.output, "w") as f:
        json.dump(geojson, f)

    csv_path.unlink()
    print(f"Wrote {len(geojson['features'])} features to {args.output}")


if __name__ == "__main__":
    main()
