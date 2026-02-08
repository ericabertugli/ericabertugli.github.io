# Skating Map Scripts

Scripts to fetch skating-friendly paths from OpenStreetMap and export them as GeoJSON for display on a Leaflet map.

## Scripts

**`overpass_to_db.py`** - Fetches data from Overpass API and stores in SQLite
- Takes an Overpass query (inline or from file) and a "way type" label
- Stores ways with their geometry, name, and tags in `data/skating_routes.db`

**`export_geojson.py`** - Exports from SQLite to GeoJSON
- Reads the database and outputs `data/routes.geojson`
- Can filter by way type or export all

## Queries

**`queries/good_to_skate.overpassql`** - Skating-friendly paths:
- Highway types: pedestrian, cycleway, or footway
- Either smoothness excellent/good OR asphalt surface
- Not restricted for skating

**`queries/30kmh_ways.overpassql`** - Streets with 30 km/h speed limit:
- Roads with maxspeed=30
- Not restricted for cycling or skating

**`queries/no_skating.overpassql`** - Paths where skating is prohibited:
- Ways tagged with `inline_skates=no`

## Output

A GeoJSON FeatureCollection at `data/routes.geojson` with LineString features containing:
- `osm_id` - OpenStreetMap way ID
- `way_type` - label passed when importing
- `name` - path name if available
- `tags` - all OSM tags for the way

## Usage

```bash
cd scripts/skatingmap
uv run python overpass_to_db.py --query-file queries/good_to_skate.overpassql --type good_to_skate
uv run python overpass_to_db.py --query-file queries/30kmh_ways.overpassql --type 30kmh_ways
uv run python overpass_to_db.py --query-file queries/no_skating.overpassql --type no_skating
uv run python export_geojson.py
```
