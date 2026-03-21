"""Shared geographic utilities."""

import math

from shapely.geometry import LineString


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS points."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def resample_linestring(coords: list[list[float]], interval_m: float) -> list[tuple[float, float]]:
    """Resample a LineString at approximately fixed intervals.

    Args:
        coords: GeoJSON coordinates [[lon, lat], ...]
        interval_m: Target distance in meters between points

    Returns:
        List of (lat, lon) tuples
    """
    if len(coords) < 2:
        return [(coords[0][1], coords[0][0])] if coords else []

    line = LineString(coords)

    total_length = sum(
        haversine_distance(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0])
        for i in range(len(coords) - 1)
    )

    if total_length == 0:
        return [(coords[0][1], coords[0][0])]

    num_points = max(2, int(total_length / interval_m) + 1)
    resampled = []

    for i in range(num_points):
        fraction = i / (num_points - 1)
        point = line.interpolate(fraction, normalized=True)
        resampled.append((point.y, point.x))

    return resampled
