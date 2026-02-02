import { describe, it } from "node:test";
import assert from "node:assert";
import {
  parseKml,
  cacheKey,
  deduplicateRegions,
  buildPointsGeoJson,
} from "./generate-travel-geojson.js";

describe("parseKml", () => {
  it("parses simple placemark", () => {
    const kml = `<Placemark><name>Test Place</name><coordinates>2.1686,41.3874,0</coordinates></Placemark>`;
    const result = parseKml(kml);
    assert.strictEqual(result.length, 1);
    assert.strictEqual(result[0].name, "Test Place");
    assert.strictEqual(result[0].lon, 2.1686);
    assert.strictEqual(result[0].lat, 41.3874);
  });

  it("parses CDATA wrapped name", () => {
    const kml = `<Placemark><name><![CDATA[CDATA Place]]></name><coordinates>1.0,2.0,0</coordinates></Placemark>`;
    const result = parseKml(kml);
    assert.strictEqual(result[0].name, "CDATA Place");
  });

  it("parses multiple placemarks", () => {
    const kml = `
      <Placemark><name>A</name><coordinates>1.0,2.0</coordinates></Placemark>
      <Placemark><name>B</name><coordinates>3.0,4.0</coordinates></Placemark>
    `;
    const result = parseKml(kml);
    assert.strictEqual(result.length, 2);
  });

  it("returns empty array for invalid KML", () => {
    const result = parseKml("<invalid></invalid>");
    assert.strictEqual(result.length, 0);
  });
});

describe("cacheKey", () => {
  it("formats coordinates to 6 decimal places", () => {
    assert.strictEqual(cacheKey(41.3874, 2.1686), "41.387400,2.168600");
  });

  it("handles negative coordinates", () => {
    assert.strictEqual(cacheKey(-33.8688, -151.2093), "-33.868800,-151.209300");
  });
});

describe("deduplicateRegions", () => {
  it("groups points by osm_id", () => {
    const points = [
      { name: "A", osm_type: "relation", osm_id: 123, region_name: "Region1" },
      { name: "B", osm_type: "relation", osm_id: 123, region_name: "Region1" },
      { name: "C", osm_type: "relation", osm_id: 456, region_name: "Region2" },
    ];
    const result = deduplicateRegions(points);
    assert.strictEqual(result.size, 2);
    assert.strictEqual(result.get("relation:123").points.length, 2);
  });

  it("skips points marked as skipped", () => {
    const points = [
      { name: "A", osm_type: "relation", osm_id: 123, skipped: true },
      { name: "B", osm_type: "relation", osm_id: 456, region_name: "Region" },
    ];
    const result = deduplicateRegions(points);
    assert.strictEqual(result.size, 1);
  });
});

describe("buildPointsGeoJson", () => {
  it("creates valid GeoJSON FeatureCollection", () => {
    const points = [
      { name: "Test", lon: 2.0, lat: 41.0, region_name: "Catalonia", country: "Spain", country_code: "es" },
    ];
    const result = buildPointsGeoJson(points);
    assert.strictEqual(result.type, "FeatureCollection");
    assert.strictEqual(result.features.length, 1);
    assert.strictEqual(result.features[0].type, "Feature");
    assert.strictEqual(result.features[0].geometry.type, "Point");
    assert.deepStrictEqual(result.features[0].geometry.coordinates, [2.0, 41.0]);
  });

  it("filters out skipped points", () => {
    const points = [
      { name: "A", lon: 1.0, lat: 1.0, skipped: true },
      { name: "B", lon: 2.0, lat: 2.0 },
    ];
    const result = buildPointsGeoJson(points);
    assert.strictEqual(result.features.length, 1);
    assert.strictEqual(result.features[0].properties.name, "B");
  });
});
