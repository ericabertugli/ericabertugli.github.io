#!/usr/bin/env python3
"""
Extract GPS points from .fit files and count H3 cell visits per activity.

Each .fit file counts as one visit. If you pass through a cell 10 times in 10
different activities, the count is 10 (not the number of GPS points).

Usage:
    python fit_to_h3.py /path/to/fit/files -o output.csv
    python fit_to_h3.py /path/to/fit/files --resolution 12 -o output.csv
    python fit_to_h3.py /path/to/fit/files --activity-type generic running -o output.csv
"""

import argparse
import csv
import logging
from collections import Counter
from pathlib import Path

import h3
from fitparse import FitFile

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def extract_gps_points(fit_path: Path) -> list[tuple[float, float, str]]:
    """Extract (lat, lon, activity_type) tuples from a .fit file."""
    points = []
    try:
        fitfile = FitFile(str(fit_path))
        for record in fitfile.get_messages("record"):
            lat = None
            lon = None
            activity_type = "unknown"
            for field in record.fields:
                if field.name == "position_lat" and field.value is not None:
                    lat = field.value * (180 / 2**31)
                elif field.name == "position_long" and field.value is not None:
                    lon = field.value * (180 / 2**31)
                elif field.name == "activity_type" and field.value is not None:
                    activity_type = str(field.value)
            if lat is not None and lon is not None:
                points.append((lat, lon, activity_type))
    except Exception as e:
        print(f"Warning: Could not parse {fit_path.name}: {e}")
    return points


def points_to_h3_cells(
    points: list[tuple[float, float, str]], resolution: int
) -> list[tuple[str, str]]:
    """Convert GPS points to (H3 cell, activity_type) tuples."""
    cells = []
    for lat, lon, activity_type in points:
        try:
            cell = h3.latlng_to_cell(lat, lon, resolution)
            cells.append((cell, activity_type))
        except Exception as e:
            logger.warning(
                f"Failed to convert coordinate to H3 cell: "
                f"lat={lat}, lon={lon}, resolution={resolution}, error={e}"
            )
    return cells


def process_fit_folder(
    folder: Path, resolution: int, activity_filter: set[str] | None
) -> Counter:
    """Process all .fit files and count how many files pass through each H3 cell."""
    counter = Counter()
    fit_files = list(folder.glob("*.fit")) + list(folder.glob("*.FIT"))

    if not fit_files:
        print(f"No .fit files found in {folder}")
        return counter

    for fit_path in fit_files:
        print(f"Processing {fit_path.name}...")
        points = extract_gps_points(fit_path)
        if activity_filter:
            points = [(lat, lon, at) for lat, lon, at in points if at in activity_filter]
        cells = points_to_h3_cells(points, resolution)
        unique_cells = set(cells)
        counter.update(unique_cells)
        print(f"  Found {len(points)} GPS points -> {len(unique_cells)} unique H3 cells")

    return counter


def write_csv(counter: Counter, output_path: Path) -> None:
    """Write H3 cell counts to CSV."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["h3_cell", "activity_type", "count"])
        for (cell, activity_type), count in counter.most_common():
            writer.writerow([cell, activity_type, count])


def main():
    parser = argparse.ArgumentParser(description="Extract GPS from .fit files and count H3 cells")
    parser.add_argument("folder", type=Path, help="Folder containing .fit files")
    parser.add_argument("-o", "--output", type=Path, default=Path("h3_counts.csv"), help="Output CSV file")
    parser.add_argument("-r", "--resolution", type=int, default=13, help="H3 resolution (0-15, default: 13)")
    parser.add_argument(
        "-a", "--activity-type", nargs="+", dest="activity_types",
        help="Filter by activity type(s), e.g., --activity-type generic running"
    )
    args = parser.parse_args()

    if not args.folder.is_dir():
        raise SystemExit(f"Error: {args.folder} is not a directory")

    if not 0 <= args.resolution <= 15:
        raise SystemExit(f"Error: Resolution must be between 0 and 15")

    activity_filter = set(args.activity_types) if args.activity_types else None
    filter_msg = f" (filtering: {', '.join(activity_filter)})" if activity_filter else ""
    print(f"Processing .fit files in {args.folder} with H3 resolution {args.resolution}{filter_msg}")

    counter = process_fit_folder(args.folder, args.resolution, activity_filter)

    if counter:
        write_csv(counter, args.output)
        print(f"\nWrote {len(counter)} unique (H3 cell, activity_type) pairs to {args.output}")
    else:
        print("No GPS data found")


if __name__ == "__main__":
    main()
