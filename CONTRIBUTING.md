# Contributing

## Local Development

Serve the site locally:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Travel Map Scripts

Requires Node.js >= 18.

### Generate GeoJSON from KML

The script expects `data/kml/travelmap.kml` to exist. This file should include all the coordinates of all the points visited (e.g. a file exported from Google MyMaps or similar tools).
Parses `data/kml/travelmap.kml`, reverse-geocodes each point via Nominatim to identify admin regions, and fetches boundary polygons. Results are cached in `data/cache/` so re-runs are fast.

```bash
npm run generate-map
```

### Simplify GeoJSON

Reduces the full-detail regions file (~94 MB) to a browser-friendly size (~1 MB) using mapshaper.

```bash
npm run simplify-map
```

### Full Pipeline

Runs both steps in sequence:

```bash
npm run build-map
```

## Skating Map Scripts

See [scripts/skatingmap/README.md](scripts/skatingmap/README.md) for documentation on fetching and updating the skating_route database to display.

## From Tracks (.fit files) to Frequent Routes

See [From Tracks to Frequent Routes](scripts/tracks-to-routes/) - Analyze GPS tracks from `.fit` files to identify frequently 
traveled routes and generate GeoJSON for visualization on the site. 
This script processes raw GPS data, applies clustering to find common paths, and outputs simplified GeoJSON files for use in the travel map.
