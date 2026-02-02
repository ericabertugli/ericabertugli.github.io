# Skating Map Scripts

Scripts to fetch skating-friendly paths from OpenStreetMap and export them as GeoJSON for display on a Leaflet map.

## Scripts

**`overpass_to_db.py`** - Fetches data from Overpass API and stores in SQLite
- Takes an Overpass query (inline or from file) and a "way type" label
- Stores ways with their geometry, name, and tags in `data/skating_routes.db`

**`export_geojson.py`** - Exports from SQLite to GeoJSON
- Reads the database and outputs `data/routes.geojson`
- Can filter by way type or export all

## Query

`queries/smooth_paths.overpassql` searches Barcelona for:
- **Highway types**: pedestrian, cycleway, or footway
- **Smoothness**: excellent or good
- **Not restricted**: excludes paths where `bicycle=no` or `inline_skates=no`

```
area[name="Barcelona"]["admin_level"="6"]
way["highway"~"pedestrian|cycleway|footway"]
   ["smoothness"~"excellent|good"]
   ["bicycle"!="no"]
   ["inline_skates"!="no"]
```

## Output

A GeoJSON FeatureCollection at `data/routes.geojson` with LineString features containing:
- `osm_id` - OpenStreetMap way ID
- `way_type` - label passed when importing
- `name` - path name if available
- `tags` - all OSM tags for the way

## Usage

```bash
cd scripts/skatingmap
uv run python overpass_to_db.py --query-file queries/smooth_paths.overpassql --type smooth_paths
uv run python export_geojson.py
```
