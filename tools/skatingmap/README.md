# Skating Map Scripts

Scripts to build all data for the skating map: fetch skating-friendly paths and POIs from OpenStreetMap, and analyze personal GPS tracks to identify frequently traveled routes.

## OSM data scripts

**`src/overpass_to_db.py`** — Fetches way data from Overpass API and stores in SQLite.
- Takes an Overpass query (inline or from file) and a "way type" label
- Stores ways with their geometry, name, and tags in `data/skating_routes.db`

**`src/export_geojson.py`** — Exports from SQLite to GeoJSON.
- Reads the database and outputs `data/routes.geojson`
- Can filter by way type or export all

**`src/enrich_slopes.py`** — Enriches ways with slope data from elevation API.
- Queries OpenTopoData EU-DEM 25m elevation API
- Computes slope % between resampled points along each way
- Stores steepest ascent (`max_slope`) and descent (`min_slope`) per way
- Only processes unenriched ways by default (safe to run repeatedly)

```bash
uv run python src/enrich_slopes.py
uv run python src/enrich_slopes.py --db path/to/db.sqlite --interval 50
uv run python src/enrich_slopes.py --recompute
```

| Option | Description | Default |
|--------|-------------|---------|
| `--db` | SQLite database path | `data/skating_routes.db` |
| `--interval` | Sampling interval in meters | `50` |
| `--recompute` | Recompute all ways, not just new ones | off |

**Slope sign convention:**
- **Positive slope** = ascent (going uphill)
- **Negative slope** = descent (going downhill)
- `min_slope <= -5%` flags a dangerous descent for inline skaters
- `max_slope >= +5%` flags a hard climb

The slope enrichment also runs automatically as part of `generate_heatmap.py` (unless `--skip-slopes` is passed).

**`src/fetch_drinking_water.py`** — Fetches drinking water locations.
- Queries Overpass API for `amenity=drinking_water` nodes
- Outputs `data/drinking_water.geojson`

### Queries

| File | Description |
|------|-------------|
| `queries/cycleways.overpassql` | Bike lanes and cycle paths |
| `queries/pedestrian_ways.overpassql` | Pedestrian paths and footways |
| `queries/30kmh_ways.overpassql` | Streets with 30 km/h speed limit |
| `queries/no_skating.overpassql` | Paths where skating is prohibited (`inline_skates=no`) |
| `queries/bbox.overpassql` | Bounding box for all queries (Barcelona area) |

### OSM output

**`data/routes.geojson`** — LineString features with properties:
- `osm_id` — OpenStreetMap way ID
- `way_type` — category label
- `name` — path name if available
- `tags` — all OSM tags

**`data/drinking_water.geojson`** — Point features for drinking fountains.

### OSM usage

```bash
cd tools/skatingmap
uv run python src/overpass_to_db.py --query-file queries/cycleways.overpassql --type cycleways
uv run python src/overpass_to_db.py --query-file queries/pedestrian_ways.overpassql --type pedestrian_ways
uv run python src/overpass_to_db.py --query-file queries/30kmh_ways.overpassql --type 30kmh_ways
uv run python src/overpass_to_db.py --query-file queries/no_skating.overpassql --type no_skating
uv run python src/export_geojson.py
uv run python src/fetch_drinking_water.py
```

### Automated updates

A GitHub Action (`.github/workflows/update-map-data.yml`) runs monthly to refresh all data from OSM:
- Creates a PR with updated GeoJSON files
- Assigns repo owner as reviewer
- Can be triggered manually from the Actions tab

---

## GPS track scripts

Analyze `.fit` GPS tracks to identify frequently traveled routes using H3 spatial indexing.

**How it works:**
1. Reads all `.fit` files from a folder
2. Extracts GPS coordinates from each track
3. Maps each point to an H3 hexagonal cell (default resolution: 13)
4. Counts how many unique activities pass through each cell
5. Filters cells below a minimum visit count
6. Outputs GeoJSON polygons (hexagons) for visualization

**`src/fit_to_h3.py`** — Parses `.fit` files and outputs an H3 cell counts CSV.

```bash
uv run python src/fit_to_h3.py /path/to/fit/files -o h3_counts.csv
```

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output CSV path | `h3_counts.csv` |
| `-r, --resolution` | H3 resolution (0–15) | `13` |
| `-d, --densify METERS` | Interpolate points every ~N meters (approximate) | off |
| `-a, --activity-type` | Filter by activity type(s) | all |

**`src/csv_to_geojson.py`** — Converts H3 counts CSV to GeoJSON hexagon polygons.

```bash
uv run python src/csv_to_geojson.py h3_counts.csv -o frequent_routes.geojson --min-count 5
```

**`src/csv_to_heatmap.py`** — Converts H3 counts CSV to a `[lat, lng]` points JSON for `leaflet-heat`.

```bash
uv run python src/csv_to_heatmap.py h3_counts.csv -o heatmap_points.json --min-count 5
```

**`src/generate_heatmap.py`** — One-command pipeline: `.fit` files → GeoJSON.

```bash
uv run python src/generate_heatmap.py /path/to/fit/files -o frequent_routes.geojson
```

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output GeoJSON file path | `heatmap.geojson` |
| `-r, --resolution` | H3 resolution (0–15) | `11` |
| `-d, --densify METERS` | Interpolate points every ~N meters (approximate) | off |
| `-a, --activity-type` | Filter by activity type(s) | all |
| `--min-count` | Minimum visit count to include a cell | `3` |

### H3 resolution reference

| Resolution | Avg cell area |
|------------|---------------|
| 10 | ~15,000 m² |
| 11 | ~2,100 m² |
| 12 | ~300 m² |
| 13 | ~43 m² |
| 14 | ~6 m² |

### GPS output

**`data/frequent_routes.geojson`** — GeoJSON FeatureCollection of H3 hexagon polygons for cells visited at least `--min-count` times.
