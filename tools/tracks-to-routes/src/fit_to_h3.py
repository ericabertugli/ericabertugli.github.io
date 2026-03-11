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
import math
from collections import Counter
from pathlib import Path

import h3
from fitparse import FitFile
from shapely.geometry import LineString

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
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


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS points."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def densify_track(
    points: list[tuple[float, float, str]], interval_m: float
) -> list[tuple[float, float, str]]:
    """Interpolate points along a track at fixed meter intervals.

    Args:
        points: List of (lat, lon, activity_type) tuples
        interval_m: Distance in meters between interpolated points
    """
    if len(points) < 2:
        return points

    activity_type = points[0][2]
    coords = [(lon, lat) for lat, lon, _ in points]
    line = LineString(coords)

    total_length = sum(
        haversine_distance(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        for i in range(len(points) - 1)
    )

    if total_length == 0:
        return points

    densified = []
    num_points = max(2, int(total_length / interval_m) + 1)

    for i in range(num_points):
        fraction = i / (num_points - 1)
        point = line.interpolate(fraction, normalized=True)
        densified.append((point.y, point.x, activity_type))

    return densified


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
    folder: Path,
    resolution: int,
    activity_filter: set[str] | None,
    densify_interval: float | None = None,
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

        if densify_interval and len(points) >= 2:
            original_count = len(points)
            points = densify_track(points, densify_interval)
            print(f"  Densified: {original_count} -> {len(points)} points")

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
    parser.add_argument(
        "-d", "--densify", type=float, dest="densify_interval", metavar="METERS",
        help="Interpolate points every N meters to fill gaps in long segments"
    )
    args = parser.parse_args()

    if not args.folder.is_dir():
        raise SystemExit(f"Error: {args.folder} is not a directory")

    if not 0 <= args.resolution <= 15:
        raise SystemExit(f"Error: Resolution must be between 0 and 15")

    if args.densify_interval is not None and args.densify_interval <= 0:
        raise SystemExit(f"Error: --densify METERS must be a positive number (got {args.densify_interval})")

    activity_filter = set(args.activity_types) if args.activity_types else None
    filter_msg = f" (filtering: {', '.join(activity_filter)})" if activity_filter else ""
    densify_msg = f", densifying every {args.densify_interval}m" if args.densify_interval else ""
    print(f"Processing .fit files in {args.folder} with H3 resolution {args.resolution}{filter_msg}{densify_msg}")

    counter = process_fit_folder(args.folder, args.resolution, activity_filter, args.densify_interval)

    if counter:
        write_csv(counter, args.output)
        print(f"\nWrote {len(counter)} unique (H3 cell, activity_type) pairs to {args.output}")
    else:
        print("No GPS data found")


if __name__ == "__main__":
    main()
