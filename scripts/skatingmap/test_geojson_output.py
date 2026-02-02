import json
from pathlib import Path

import pytest

GEOJSON_PATH = Path(__file__).parent.parent.parent / "data" / "routes.geojson"


@pytest.fixture
def geojson_data():
    if not GEOJSON_PATH.exists():
        pytest.skip(f"GeoJSON file not found: {GEOJSON_PATH}")
    return json.loads(GEOJSON_PATH.read_text())


class TestGeoJsonStructure:
    def test_is_feature_collection(self, geojson_data):
        assert geojson_data["type"] == "FeatureCollection"

    def test_has_features(self, geojson_data):
        assert "features" in geojson_data
        assert isinstance(geojson_data["features"], list)

    def test_features_have_required_fields(self, geojson_data):
        for feature in geojson_data["features"]:
            assert feature["type"] == "Feature"
            assert "geometry" in feature
            assert "properties" in feature

    def test_geometries_are_linestrings(self, geojson_data):
        for feature in geojson_data["features"]:
            assert feature["geometry"]["type"] == "LineString"
            assert isinstance(feature["geometry"]["coordinates"], list)

    def test_properties_have_expected_fields(self, geojson_data):
        for feature in geojson_data["features"]:
            props = feature["properties"]
            assert "osm_id" in props
            assert "way_type" in props
