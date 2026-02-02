import json
import tempfile
from pathlib import Path

import pytest

from export_geojson import export_geojson, list_types
from overpass_to_db import init_db, way_to_geojson, store_ways


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()
    db_path.unlink()


class TestWayToGeojson:
    def test_converts_geometry_to_linestring(self):
        element = {
            "geometry": [
                {"lat": 41.0, "lon": 2.0},
                {"lat": 41.1, "lon": 2.1},
            ]
        }
        result = way_to_geojson(element)
        assert result["type"] == "LineString"
        assert result["coordinates"] == [[2.0, 41.0], [2.1, 41.1]]

    def test_handles_empty_geometry(self):
        result = way_to_geojson({"geometry": []})
        assert result["coordinates"] == []


class TestStoreWays:
    def test_stores_way_in_database(self, temp_db):
        conn, _ = temp_db
        elements = [
            {
                "type": "way",
                "id": 12345,
                "tags": {"name": "Test Path", "surface": "asphalt"},
                "geometry": [{"lat": 41.0, "lon": 2.0}, {"lat": 41.1, "lon": 2.1}],
            }
        ]
        count = store_ways(conn, elements, "smooth_paths")
        assert count == 1

        cursor = conn.execute("SELECT * FROM ways WHERE osm_id = 12345")
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "smooth_paths"
        assert row[2] == "Test Path"

    def test_skips_non_way_elements(self, temp_db):
        conn, _ = temp_db
        elements = [{"type": "node", "id": 1}, {"type": "relation", "id": 2}]
        count = store_ways(conn, elements, "test")
        assert count == 0


class TestExportGeojson:
    def test_exports_all_ways(self, temp_db):
        conn, _ = temp_db
        conn.execute(
            "INSERT INTO ways VALUES (1, 'type_a', 'Path A', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": [[0, 0]]}), "{}"),
        )
        conn.execute(
            "INSERT INTO ways VALUES (2, 'type_b', 'Path B', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": [[1, 1]]}), "{}"),
        )
        conn.commit()

        result = export_geojson(conn, None)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2

    def test_filters_by_way_type(self, temp_db):
        conn, _ = temp_db
        conn.execute(
            "INSERT INTO ways VALUES (1, 'type_a', 'A', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": []}), "{}"),
        )
        conn.execute(
            "INSERT INTO ways VALUES (2, 'type_b', 'B', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": []}), "{}"),
        )
        conn.commit()

        result = export_geojson(conn, "type_a")
        assert len(result["features"]) == 1
        assert result["features"][0]["properties"]["name"] == "A"


class TestListTypes:
    def test_returns_distinct_types(self, temp_db):
        conn, _ = temp_db
        conn.execute(
            "INSERT INTO ways VALUES (1, 'smooth', 'A', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": []}), "{}"),
        )
        conn.execute(
            "INSERT INTO ways VALUES (2, 'rough', 'B', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": []}), "{}"),
        )
        conn.commit()

        result = list_types(conn)
        assert sorted(result) == ["rough", "smooth"]
