# Skating Map Scripts

Scripts to fetch skating-friendly paths and POIs from OpenStreetMap and export them as GeoJSON for display on a Leaflet map.

## Scripts

**`overpass_to_db.py`** - Fetches way data from Overpass API and stores in SQLite
- Takes an Overpass query (inline or from file) and a "way type" label
- Stores ways with their geometry, name, and tags in `data/skating_routes.db`

**`export_geojson.py`** - Exports from SQLite to GeoJSON
- Reads the database and outputs `data/routes.geojson`
- Can filter by way type or export all

**`fetch_drinking_water.py`** - Fetches drinking water locations
- Queries Overpass API for `amenity=drinking_water` nodes
- Outputs `data/drinking_water.geojson`

## Queries

**`queries/cycleways.overpassql`** - Bike lanes and cycle paths

**`queries/pedestrian_ways.overpassql`** - Pedestrian paths and footways

**`queries/30kmh_ways.overpassql`** - Streets with 30 km/h speed limit

**`queries/no_skating.overpassql`** - Paths where skating is prohibited (`inline_skates=no`)

**`queries/bbox.overpassql`** - Bounding box for all queries (Barcelona area)

## Output

**`data/routes.geojson`** - LineString features with properties:
- `osm_id` - OpenStreetMap way ID
- `way_type` - category label
- `name` - path name if available
- `tags` - all OSM tags

**`data/drinking_water.geojson`** - Point features for drinking fountains

## Manual Usage

```bash
cd scripts/skatingmap
uv run python overpass_to_db.py --query-file queries/cycleways.overpassql --type cycleways
uv run python overpass_to_db.py --query-file queries/pedestrian_ways.overpassql --type pedestrian_ways
uv run python overpass_to_db.py --query-file queries/30kmh_ways.overpassql --type 30kmh_ways
uv run python overpass_to_db.py --query-file queries/no_skating.overpassql --type no_skating
uv run python export_geojson.py
uv run python fetch_drinking_water.py
```

## Automated Updates

A GitHub Action (`.github/workflows/update-map-data.yml`) runs monthly to refresh all data from OSM:
- Creates a PR with updated GeoJSON files
- Assigns repo owner as reviewer
- Can be triggered manually from the Actions tab
