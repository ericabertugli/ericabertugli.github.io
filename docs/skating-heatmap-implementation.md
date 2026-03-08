# Skating Heatmap Implementation

This document describes the approaches explored for visualizing frequently traveled routes from GPS tracks.

## Problem Statement

Given a collection of `.fit` files containing GPS tracks, we want to identify and visualize the most frequently traveled routes on a map.

**Challenges:**
- GPS points are recorded at variable intervals (time-based, not distance-based)
- Long straight segments have fewer points than winding paths
- Raw GPS data doesn't align perfectly with roads/paths

## Solutions Explored
 
### 1. H3 Cells (First Implementation)

**Approach:** Convert GPS points to H3 hexagonal cells, deduplicate per activity, then count how many activities passed through each cell.

```
.fit file → GPS Points → H3 Cells → Deduplicate per file → Count activities per cell
```

**Key insight:** We count *activities* (files), not GPS points. This prevents slow skating through a cell from inflating the count. A cell with count=10 means you skated through it in 10 different sessions.

**Pros:**
- Simple implementation
- No external dependencies (just h3 library)
- Resolution is configurable (we use res 11, ~2100m² per cell)
- Counts represent actual visits, not GPS recording frequency

**Cons:**
- Sparse data on long straight segments (fewer GPS points recorded)
- Hexagons don't follow road geometry
- Visual gaps where GPS recording interval was longer

---

### 2. Map Matching + OSM Way ID Counting (Discarded)

**Approach:** Match GPS points to OSM ways, then count which way IDs appear most frequently.

```
GPS Point → Match to nearest OSM way → Count way_id occurrences → Highlight frequent ways
```

**Pros:**
- Routes align perfectly with actual roads/paths
- Natural visualization (full street segments, not hexagons)
- Can leverage OSM metadata (surface, smoothness, etc.)

**Cons:**
- Requires map matching service (Valhalla, OSRM, or GraphHopper)
- More complex infrastructure
- GPS errors can cause incorrect matches
- Needs OSM data to be kept up to date

**Not implemented** - added complexity outweighs benefits for this use case.

---

### 3. Densify Tracks Before H3 (Current implementation)

**Approach:** Interpolate points along the GPS track at fixed intervals before converting to H3.

```
GPS Points → LineString → Interpolate every X meters → H3 cells → Count
```

**Steps:**
1. Convert GPS points to a LineString per activity
2. Interpolate points every X meters (e.g., every 5m)
3. Convert interpolated points to H3 cells
4. Count occurrences normally

**Pros:**
- Long streets get evenly filled (no sparse data)
- Still simple (no external services)
- Preserves the hexagon visualization approach
- Configurable density (interpolation interval)

**Cons:**
- Slightly more processing time
- May create points where you didn't actually travel (interpolation assumes straight line between GPS points)

**Implementation outline:**
```python
from shapely.geometry import LineString
from shapely.ops import substring

def densify_track(points: list[tuple[float, float]], interval_m: float) -> list[tuple[float, float]]:
    """Interpolate points along a track at fixed intervals."""
    if len(points) < 2:
        return points

    line = LineString([(lon, lat) for lat, lon in points])
    length = line.length * 111000  # approximate meters (at equator)

    densified = []
    distance = 0
    while distance < length:
        point = line.interpolate(distance / 111000)
        densified.append((point.y, point.x))  # lat, lon
        distance += interval_m

    return densified
```

**Status:** ✅ Implemented. Use `-d` / `--densify` flag:
```bash
python fit_to_h3.py /path/to/fits -d 5 -o output.csv  # interpolate every 5 meters
```

## Current Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  .fit files     │────▶│ fit_to_h3.py │────▶│  h3_counts.csv  │
│  (GPS tracks)   │     │              │     │                 │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────────┐   ┌─────────────────┐
│  skating.html   │◀────│ csv_to_geojson.py│◀──│ frequent_routes │
│  (Leaflet map)  │     │                  │   │   .geojson      │
└─────────────────┘     └──────────────────┘   └─────────────────┘
```

## Configuration

| Parameter | Current Value | Description |
|-----------|---------------|-------------|
| H3 Resolution | 11 | Cell size ~2100m² |
| Min Count | 5 | Minimum activities to include in visualization |
| Activity Filter | `generic` | Only include skating activities |