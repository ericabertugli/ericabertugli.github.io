#!/usr/bin/env node

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

const KML_PATH = resolve(ROOT, "data/kml/travelmap.kml");
const CACHE_PATH = resolve(ROOT, "data/cache/geocode-cache.json");
const OUTPUT_REGIONS = resolve(ROOT, "data/geojson/travel-regions.geojson");
const OUTPUT_POINTS = resolve(ROOT, "data/geojson/travel-points.geojson");

const USER_AGENT =
  "EricaBertugliTravelMap/1.0 (GitHub Pages project; github.com/ericabertugli)";
const RATE_LIMIT_MS = 1100;
const NOMINATIM_BASE = "https://nominatim.openstreetmap.org";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchWithRetry(url, retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15_000);
      const response = await fetch(url, {
        headers: { "User-Agent": USER_AGENT },
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (response.status === 429) {
        const wait = 2 ** attempt * 1000;
        console.warn(`  Rate limited, waiting ${wait}ms...`);
        await sleep(wait);
        continue;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      if (attempt === retries) {
        console.warn(`  Failed after ${retries} attempts: ${err.message}`);
        return null;
      }
      await sleep(2 ** attempt * 1000);
    }
  }
  return null;
}

async function loadCache() {
  if (!existsSync(CACHE_PATH)) return {};
  try {
    const data = await readFile(CACHE_PATH, "utf-8");
    return JSON.parse(data);
  } catch {
    return {};
  }
}

async function saveCache(cache) {
  await mkdir(dirname(CACHE_PATH), { recursive: true });
  await writeFile(CACHE_PATH, JSON.stringify(cache, null, 2));
}

function parseKml(content) {
  const points = [];
  const placemarkRegex =
    /<Placemark>[\s\S]*?<name>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/name>[\s\S]*?<coordinates>\s*([\d.eE+\-,]+)\s*<\/coordinates>[\s\S]*?<\/Placemark>/g;

  let match;
  while ((match = placemarkRegex.exec(content)) !== null) {
    const name = match[1].trim();
    const coords = match[2].split(",");
    const lon = parseFloat(coords[0]);
    const lat = parseFloat(coords[1]);
    if (!isNaN(lon) && !isNaN(lat)) {
      points.push({ name, lon, lat });
    }
  }
  return points;
}

function cacheKey(lat, lon) {
  return `${lat.toFixed(6)},${lon.toFixed(6)}`;
}

async function reverseGeocodeAll(points, cache) {
  const results = [];
  let uncachedCount = points.filter(
    (p) => !cache[cacheKey(p.lat, p.lon)],
  ).length;
  let processed = 0;
  let cacheHits = 0;
  const startTime = Date.now();

  console.log(
    `  ${points.length} points total, ${uncachedCount} need geocoding`,
  );

  for (let i = 0; i < points.length; i++) {
    const point = points[i];
    const key = cacheKey(point.lat, point.lon);

    if (cache[key]) {
      cacheHits++;
      results.push({ ...point, ...cache[key] });
      continue;
    }

    const url = `${NOMINATIM_BASE}/reverse?lat=${point.lat}&lon=${point.lon}&format=jsonv2&zoom=5&addressdetails=1`;
    const data = await fetchWithRetry(url);

    if (!data || data.error) {
      console.warn(
        `  [${i + 1}/${points.length}] SKIP "${point.name}" - ${data?.error || "no response"}`,
      );
      results.push({ ...point, skipped: true });
      await sleep(RATE_LIMIT_MS);
      processed++;
      continue;
    }

    const osmType = data.osm_type || "relation";
    const osmId = data.osm_id;
    const regionName =
      data.address?.state ||
      data.address?.region ||
      data.address?.country ||
      data.display_name;
    const country = data.address?.country || "";
    const countryCode = data.address?.country_code || "";

    const entry = {
      osm_type: osmType,
      osm_id: osmId,
      region_name: regionName,
      country,
      country_code: countryCode,
    };

    cache[key] = entry;
    results.push({ ...point, ...entry });
    processed++;

    if (processed % 10 === 0) {
      await saveCache(cache);
    }

    if (processed % 50 === 0 || processed === uncachedCount) {
      // Avoid dividing by zero when there are no uncached points or none processed yet.
      if (processed === 0 || uncachedCount === 0) {
        console.log(
          `  [${i + 1}/${points.length}] 0/${uncachedCount} geocoded via API (all points served from cache so far)`,
        );
      } else {
        const elapsed = (Date.now() - startTime) / 1000;
        const rate = processed / elapsed;
        const remaining = Math.round((uncachedCount - processed) / rate);
        console.log(
          `  [${i + 1}/${points.length}] ${processed}/${uncachedCount} geocoded (ETA ~${Math.floor(remaining / 60)}m ${remaining % 60}s)`,
        );
      }
    } else if (processed <= 5) {
      console.log(
        `  [${i + 1}/${points.length}] "${point.name}" -> ${regionName}, ${country}`,
      );
    }

    await sleep(RATE_LIMIT_MS);
  }

  await saveCache(cache);
  console.log(`  Done. ${cacheHits} cache hits, ${processed} API calls.`);
  return results;
}

function deduplicateRegions(geocodedPoints) {
  const regionMap = new Map();

  for (const point of geocodedPoints) {
    if (point.skipped || !point.osm_id) continue;

    const id = `${point.osm_type}:${point.osm_id}`;
    if (!regionMap.has(id)) {
      regionMap.set(id, {
        osmType: point.osm_type,
        osmId: point.osm_id,
        regionName: point.region_name,
        country: point.country,
        countryCode: point.country_code,
        points: [],
      });
    }
    regionMap.get(id).points.push(point);
  }

  return regionMap;
}

async function fetchBoundaries(regionMap) {
  const features = [];
  const regions = [...regionMap.values()];
  console.log(`  ${regions.length} unique regions to fetch`);

  for (let i = 0; i < regions.length; i++) {
    const region = regions[i];
    const osmPrefix = region.osmType.charAt(0).toUpperCase();
    const url = `${NOMINATIM_BASE}/lookup?osm_ids=${osmPrefix}${region.osmId}&format=geojson&polygon_geojson=1`;

    const data = await fetchWithRetry(url);

    if (
      !data ||
      !data.features ||
      data.features.length === 0 ||
      !data.features[0].geometry
    ) {
      console.warn(
        `  [${i + 1}/${regions.length}] SKIP "${region.regionName}" - no boundary data`,
      );
      await sleep(RATE_LIMIT_MS);
      continue;
    }

    const feature = data.features[0];
    features.push({
      type: "Feature",
      properties: {
        osm_id: region.osmId,
        name: region.regionName,
        country: region.country,
        country_code: region.countryCode,
        point_count: region.points.length,
      },
      geometry: feature.geometry,
    });

    if ((i + 1) % 20 === 0 || i === regions.length - 1) {
      console.log(`  [${i + 1}/${regions.length}] boundaries fetched`);
    }

    await sleep(RATE_LIMIT_MS);
  }

  return features;
}

function buildPointsGeoJson(geocodedPoints) {
  const features = geocodedPoints
    .filter((p) => !p.skipped)
    .map((p) => ({
      type: "Feature",
      properties: {
        name: p.name,
        region: p.region_name || "",
        country: p.country || "",
        country_code: p.country_code || "",
      },
      geometry: {
        type: "Point",
        coordinates: [p.lon, p.lat],
      },
    }));

  return { type: "FeatureCollection", features };
}

async function main() {
  const totalStart = Date.now();

  console.log("\n[Phase 1] Parsing KML...");
  const kmlContent = await readFile(KML_PATH, "utf-8");
  const points = parseKml(kmlContent);
  console.log(`  Found ${points.length} placemarks`);

  console.log("\n[Phase 2] Reverse geocoding...");
  const cache = await loadCache();
  const geocodedPoints = await reverseGeocodeAll(points, cache);

  console.log("\n[Phase 3] Deduplicating regions...");
  const regionMap = deduplicateRegions(geocodedPoints);
  console.log(
    `  ${geocodedPoints.filter((p) => !p.skipped).length} points -> ${regionMap.size} unique regions`,
  );

  console.log("\n[Phase 4] Fetching boundary polygons...");
  const regionFeatures = await fetchBoundaries(regionMap);

  console.log("\n[Phase 5] Writing output...");
  await mkdir(dirname(OUTPUT_REGIONS), { recursive: true });

  const regionsGeoJson = {
    type: "FeatureCollection",
    features: regionFeatures,
  };
  await writeFile(OUTPUT_REGIONS, JSON.stringify(regionsGeoJson));
  const regionSize = (
    JSON.stringify(regionsGeoJson).length /
    1024 /
    1024
  ).toFixed(1);
  console.log(
    `  ${OUTPUT_REGIONS} (${regionFeatures.length} features, ${regionSize} MB)`,
  );

  const pointsGeoJson = buildPointsGeoJson(geocodedPoints);
  await writeFile(OUTPUT_POINTS, JSON.stringify(pointsGeoJson));
  const pointSize = (
    JSON.stringify(pointsGeoJson).length / 1024
  ).toFixed(0);
  console.log(
    `  ${OUTPUT_POINTS} (${pointsGeoJson.features.length} features, ${pointSize} KB)`,
  );

  const elapsed = ((Date.now() - totalStart) / 1000).toFixed(0);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  console.log(`\nDone in ${mins}m ${secs}s.\n`);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
