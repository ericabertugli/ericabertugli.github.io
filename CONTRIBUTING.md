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
