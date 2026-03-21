#!/usr/bin/env python3
"""
Enrich ways with slope data from OpenTopoData elevation API.

Usage:
    python enrich_slopes.py
    python enrich_slopes.py --db path/to/db.sqlite --interval 50
    python enrich_slopes.py --recompute
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path

import requests

from geo_utils import haversine_distance, resample_linestring

DB_PATH = Path(__file__).parent.parent.parent / "data" / "skating_routes.db"
OPENTOPODATA_URL = "https://api.opentopodata.org/v1/eudem25m"
MAX_LOCATIONS_PER_REQUEST = 100
REQUEST_INTERVAL_SECONDS = 1.0


def fetch_elevations(points: list[tuple[float, float]]) -> list[float | None]:
    """Fetch elevations from OpenTopoData API.

    Args:
        points: List of (lat, lon) tuples

    Returns:
        List of elevations in meters (None for failed lookups)
    """
    locations = "|".join(f"{lat},{lon}" for lat, lon in points)
    response = requests.post(OPENTOPODATA_URL, data={"locations": locations}, timeout=30)
    response.raise_for_status()
    data = response.json()

    elevations = []
    for result in data.get("results", []):
        elevations.append(result.get("elevation"))
    return elevations


def compute_slopes(
    points: list[tuple[float, float]], elevations: list[float | None]
) -> tuple[float | None, float | None, tuple | None, tuple | None]:
    """Compute max and min slopes from points and elevations.

    Args:
        points: List of (lat, lon) tuples
        elevations: Corresponding elevations in meters

    Returns:
        (max_slope, min_slope, max_segment_coords, min_segment_coords)
        where segment_coords is ((start_lon, start_lat), (end_lon, end_lat))
    """
    max_slope = None
    min_slope = None
    max_segment = None
    min_segment = None

    for i in range(len(points) - 1):
        elev1 = elevations[i]
        elev2 = elevations[i + 1]

        if elev1 is None or elev2 is None:
            continue

        lat1, lon1 = points[i]
        lat2, lon2 = points[i + 1]

        distance = haversine_distance(lat1, lon1, lat2, lon2)
        if distance < 1:
            continue

        delta_elev = elev2 - elev1
        slope_pct = (delta_elev / distance) * 100

        if max_slope is None or slope_pct > max_slope:
            max_slope = slope_pct
            max_segment = ((lon1, lat1), (lon2, lat2))

        if min_slope is None or slope_pct < min_slope:
            min_slope = slope_pct
            min_segment = ((lon1, lat1), (lon2, lat2))

    return max_slope, min_slope, max_segment, min_segment


def enrich_way(
    conn: sqlite3.Connection,
    osm_id: int,
    geojson: str,
    interval_m: float,
    pending_points: list,
    pending_ways: list,
) -> None:
    """Queue a way for enrichment, batching API calls.

    Adds points to pending_points and way info to pending_ways.
    Caller should flush when batch is full.
    """
    geometry = json.loads(geojson)
    coords = geometry.get("coordinates", [])

    if len(coords) < 2:
        return

    points = resample_linestring(coords, interval_m)
    start_idx = len(pending_points)
    pending_points.extend(points)
    pending_ways.append((osm_id, start_idx, len(points)))


def flush_batch(
    conn: sqlite3.Connection,
    pending_points: list,
    pending_ways: list,
) -> int:
    """Fetch elevations and update DB for all pending ways.

    Returns:
        Number of ways processed
    """
    if not pending_points:
        return 0

    all_elevations = []
    for i in range(0, len(pending_points), MAX_LOCATIONS_PER_REQUEST):
        batch = pending_points[i : i + MAX_LOCATIONS_PER_REQUEST]
        elevations = fetch_elevations(batch)
        all_elevations.extend(elevations)

        if i + MAX_LOCATIONS_PER_REQUEST < len(pending_points):
            time.sleep(REQUEST_INTERVAL_SECONDS)

    for osm_id, start_idx, num_points in pending_ways:
        points = pending_points[start_idx : start_idx + num_points]
        elevations = all_elevations[start_idx : start_idx + num_points]

        max_slope, min_slope, max_seg, min_seg = compute_slopes(points, elevations)

        conn.execute(
            """
            UPDATE ways SET
                max_slope = ?,
                min_slope = ?,
                max_slope_start_lon = ?,
                max_slope_start_lat = ?,
                max_slope_end_lon = ?,
                max_slope_end_lat = ?,
                min_slope_start_lon = ?,
                min_slope_start_lat = ?,
                min_slope_end_lon = ?,
                min_slope_end_lat = ?,
                slope_enriched = 1
            WHERE osm_id = ?
            """,
            (
                max_slope,
                min_slope,
                max_seg[0][0] if max_seg else None,
                max_seg[0][1] if max_seg else None,
                max_seg[1][0] if max_seg else None,
                max_seg[1][1] if max_seg else None,
                min_seg[0][0] if min_seg else None,
                min_seg[0][1] if min_seg else None,
                min_seg[1][0] if min_seg else None,
                min_seg[1][1] if min_seg else None,
                osm_id,
            ),
        )

    conn.commit()
    return len(pending_ways)


def enrich(db_path: Path, interval_m: float = 50, recompute: bool = False) -> tuple[int, int]:
    """Enrich all ways with slope data.

    Args:
        db_path: Path to SQLite database
        interval_m: Sampling interval in meters
        recompute: If True, recompute all ways; otherwise only NULL ones

    Returns:
        (processed_count, skipped_count)
    """
    conn = sqlite3.connect(db_path)

    if recompute:
        cursor = conn.execute("SELECT osm_id, geojson FROM ways")
    else:
        cursor = conn.execute("SELECT osm_id, geojson FROM ways WHERE slope_enriched = 0")

    rows = cursor.fetchall()
    total = len(rows)

    if recompute:
        skipped = 0
    else:
        total_ways = conn.execute("SELECT COUNT(*) FROM ways").fetchone()[0]
        skipped = total_ways - total

    pending_points: list[tuple[float, float]] = []
    pending_ways: list[tuple[int, int, int]] = []
    processed = 0

    for osm_id, geojson in rows:
        enrich_way(conn, osm_id, geojson, interval_m, pending_points, pending_ways)

        if len(pending_points) >= MAX_LOCATIONS_PER_REQUEST:
            processed += flush_batch(conn, pending_points, pending_ways)
            pending_points.clear()
            pending_ways.clear()
            time.sleep(REQUEST_INTERVAL_SECONDS)

    if pending_points:
        processed += flush_batch(conn, pending_points, pending_ways)

    conn.close()
    return processed, skipped


def main():
    parser = argparse.ArgumentParser(description="Enrich ways with slope data from elevation API")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path")
    parser.add_argument("--interval", type=float, default=50, help="Sampling interval in meters")
    parser.add_argument("--recompute", action="store_true", help="Recompute all ways, not just NULL")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Database not found: {args.db}")
        return

    print(f"Enriching slopes (interval={args.interval}m, recompute={args.recompute})...")
    processed, skipped = enrich(args.db, args.interval, args.recompute)
    print(f"Done: {processed} processed, {skipped} skipped")


if __name__ == "__main__":
    main()