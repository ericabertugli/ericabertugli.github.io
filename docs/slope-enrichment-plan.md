# Slope Enrichment for Skating Map

## Problem
OSM `incline` tag covers <1% of ways in the Barcelona bbox. To highlight dangerously steep
descents for inline skaters, we need to derive slope from elevation data.

## Approach
Sample each OSM way geometry at fixed intervals (~50 m), query the EU-DEM 25 m elevation
dataset via the OpenTopoData public API, compute slope % between consecutive sample points,
and store the maximum slope back against the way ID in the existing SQLite database.

## Todos

- [x] **1. Add slope columns to the DB schema**
  - Alter `ways` table: add eleven new columns:
    - `max_slope REAL` — steepest ascent (positive %, e.g. `+8.3`)
    - `min_slope REAL` — steepest descent (negative %, e.g. `-6.1`)
    - `max_slope_start_lon REAL`, `max_slope_start_lat REAL` — start of steepest ascent segment
    - `max_slope_end_lon REAL`, `max_slope_end_lat REAL` — end of steepest ascent segment
    - `min_slope_start_lon REAL`, `min_slope_start_lat REAL` — start of steepest descent segment
    - `min_slope_end_lon REAL`, `min_slope_end_lat REAL` — end of steepest descent segment
    - `slope_enriched INTEGER DEFAULT 0` — boolean flag (0=pending, 1=processed)
  - Applied via `ALTER TABLE ADD COLUMN` with try/except in `init_db()` so existing DBs
    migrate safely without data loss
  - Created `src/geo_utils.py` with shared `haversine_distance` and `resample_linestring`

- [x] **2. Write `src/enrich_slopes.py`**
  - **Only process ways where `slope_enriched = 0`** — skip already-computed ways; re-runs
    are free and new OSM way IDs (inserted with `NULL`) are picked up automatically
  - For each unprocessed way: resample geometry every 50 m using Shapely
  - Batch sample points (≤100 per request) → POST to
    `https://api.opentopodata.org/v1/eudem25m`
  - Compute signed slope % per segment: `(Δelev / distance) * 100`
    (positive = ascent, negative = descent)
  - Track both the most positive segment (`max_slope`) and most negative (`min_slope`)
    with their respective segment coordinates
  - Write all ten values back to DB per way
  - Rate-limit to 1 req/s (API limit); log skipped vs processed count
  - `--recompute` flag to force full reprocessing (e.g. after changing sampling interval)

- [x] **3. Add CLI options**
  - `--db` path (default: same as other scripts)
  - `--interval METERS` sampling interval (default: 50)
  - `--recompute` flag (default: off)

- [x] **4. Integrate into `generate_heatmap.py`**
  - After the heatmap pipeline completes, call `enrich_slopes.enrich(db_path)` for any
    ways not yet enriched (the `slope_enriched` flag ensures only new ways are processed)
  - Add `--db` argument to `generate_heatmap.py` to pass the skating routes DB path
  - Add `--skip-slopes` flag to opt out (default: run enrichment)

- [x] **5. Update `export_geojson.py`**
  - Include `max_slope`, `min_slope` in exported GeoJSON feature properties (rounded to 1 decimal)
  - Build `max_slope_segment` and `min_slope_segment` GeoJSON LineStrings from the
    coordinate columns at export time via `_build_segment()` helper

- [ ] **6. Add tests**
  - Unit-test the geometry resampling logic
  - Unit-test signed slope computation (positive ascent, negative descent)
  - Mock the OpenTopoData HTTP call
  - Test the `NULL` guard (already-computed ways are skipped)

- [ ] **7. Update README**
  - Document `enrich_slopes.py` usage and CLI flags
  - Note it is also triggered automatically by `generate_heatmap.py`
  - Explain `max_slope` vs `min_slope` sign convention

## Notes
- OpenTopoData free tier: 100 locations/request, 1 req/s, no auth needed
- EU-DEM 25 m dataset (`eudem25m`) is the best available for Barcelona
- Shapely is already a project dependency — use it for resampling
- Sign convention: **positive slope = ascent, negative slope = descent**
  - `min_slope <= -5%` flags a dangerous descent for inline skaters
  - `max_slope >= +5%` flags a hard climb
- The segment coordinate columns let the map draw precise overlays on the exact danger
  zone, not the whole way (GeoJSON constructed at export time from lon/lat pairs)
- The `NULL` guard in `enrich_slopes.py` means the script is safe to run repeatedly:
  already-computed ways are skipped; new ways added by `overpass_to_db.py` (which insert
  with `NULL`) are automatically picked up on the next run
