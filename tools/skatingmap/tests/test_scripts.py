import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
import requests

from export_geojson import export_geojson, list_types
from fetch_drinking_water import fetch_drinking_water
from overpass_to_db import init_db, way_to_geojson, store_ways, fetch_overpass


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
        count = store_ways(conn, elements, "good_to_skate")
        assert count == 1

        cursor = conn.execute("SELECT * FROM ways WHERE osm_id = 12345")
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "good_to_skate"
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
            "INSERT INTO ways (osm_id, way_type, name, geojson, tags) VALUES (1, 'type_a', 'Path A', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": [[0, 0]]}), "{}"),
        )
        conn.execute(
            "INSERT INTO ways (osm_id, way_type, name, geojson, tags) VALUES (2, 'type_b', 'Path B', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": [[1, 1]]}), "{}"),
        )
        conn.commit()

        result = export_geojson(conn, None)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2

    def test_filters_by_way_type(self, temp_db):
        conn, _ = temp_db
        conn.execute(
            "INSERT INTO ways (osm_id, way_type, name, geojson, tags) VALUES (1, 'type_a', 'A', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": []}), "{}"),
        )
        conn.execute(
            "INSERT INTO ways (osm_id, way_type, name, geojson, tags) VALUES (2, 'type_b', 'B', ?, ?)",
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
            "INSERT INTO ways (osm_id, way_type, name, geojson, tags) VALUES (1, 'smooth', 'A', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": []}), "{}"),
        )
        conn.execute(
            "INSERT INTO ways (osm_id, way_type, name, geojson, tags) VALUES (2, 'rough', 'B', ?, ?)",
            (json.dumps({"type": "LineString", "coordinates": []}), "{}"),
        )
        conn.commit()

        result = list_types(conn)
        assert sorted(result) == ["rough", "smooth"]


def _mock_http_error(status_code):
    response = Mock()
    response.status_code = status_code
    response.text = "error"
    error = requests.exceptions.HTTPError(response=response)
    return error


SAMPLE_QUERY = "way[surface=asphalt];"


class TestFetchOverpassRetry:
    @patch("overpass_to_db.time.sleep")
    @patch("overpass_to_db.requests.post")
    def test_retries_on_504_then_succeeds(self, mock_post, mock_sleep):
        fail_resp = Mock()
        fail_resp.raise_for_status.side_effect = _mock_http_error(504)

        ok_resp = Mock()
        ok_resp.raise_for_status.return_value = None
        ok_resp.json.return_value = {"elements": []}

        mock_post.side_effect = [fail_resp, ok_resp]
        result = fetch_overpass(SAMPLE_QUERY, max_retries=2, initial_delay=0.01)
        assert result == {"elements": []}
        assert mock_post.call_count == 2

    @patch("overpass_to_db.time.sleep")
    @patch("overpass_to_db.requests.post")
    def test_retries_on_429_then_succeeds(self, mock_post, mock_sleep):
        fail_resp = Mock()
        fail_resp.raise_for_status.side_effect = _mock_http_error(429)

        ok_resp = Mock()
        ok_resp.raise_for_status.return_value = None
        ok_resp.json.return_value = {"elements": []}

        mock_post.side_effect = [fail_resp, ok_resp]
        result = fetch_overpass(SAMPLE_QUERY, max_retries=2, initial_delay=0.01)
        assert result == {"elements": []}

    @patch("overpass_to_db.time.sleep")
    @patch("overpass_to_db.requests.post")
    def test_exits_after_max_retries(self, mock_post, mock_sleep):
        fail_resp = Mock()
        fail_resp.raise_for_status.side_effect = _mock_http_error(504)
        mock_post.return_value = fail_resp

        with pytest.raises(SystemExit, match="HTTP 504"):
            fetch_overpass(SAMPLE_QUERY, max_retries=1, initial_delay=0.01)
        assert mock_post.call_count == 2

    @patch("overpass_to_db.time.sleep")
    @patch("overpass_to_db.requests.post")
    def test_no_retry_on_400(self, mock_post, mock_sleep):
        fail_resp = Mock()
        fail_resp.raise_for_status.side_effect = _mock_http_error(400)
        mock_post.return_value = fail_resp

        with pytest.raises(SystemExit, match="HTTP 400"):
            fetch_overpass(SAMPLE_QUERY, max_retries=3, initial_delay=0.01)
        assert mock_post.call_count == 1


class TestFetchDrinkingWaterRetry:
    @patch("fetch_drinking_water.time.sleep")
    @patch("fetch_drinking_water.requests.post")
    def test_retries_on_504_then_succeeds(self, mock_post, mock_sleep):
        fail_resp = Mock()
        fail_resp.raise_for_status.side_effect = _mock_http_error(504)

        ok_resp = Mock()
        ok_resp.raise_for_status.return_value = None
        ok_resp.json.return_value = {"elements": [{"lat": 1, "lon": 2}]}

        mock_post.side_effect = [fail_resp, ok_resp]
        result = fetch_drinking_water("41.32,2.05,41.47,2.23", max_retries=2, initial_delay=0.01)
        assert len(result) == 1

    @patch("fetch_drinking_water.time.sleep")
    @patch("fetch_drinking_water.requests.post")
    def test_returns_empty_after_max_retries(self, mock_post, mock_sleep):
        fail_resp = Mock()
        fail_resp.raise_for_status.side_effect = _mock_http_error(504)
        mock_post.return_value = fail_resp

        result = fetch_drinking_water("41.32,2.05,41.47,2.23", max_retries=1, initial_delay=0.01)
        assert result == []
        assert mock_post.call_count == 2
