"""Tests for slope enrichment functionality."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from enrich_slopes import compute_slopes, enrich, resample_way_coords
from geo_utils import resample_linestring


class TestResampleLinestring:
    def test_returns_at_least_two_points(self):
        coords = [[0.0, 0.0], [0.001, 0.001]]
        result = resample_linestring(coords, interval_m=50)
        assert len(result) >= 2

    def test_single_coordinate_returns_single_point(self):
        coords = [[2.15, 41.38]]
        result = resample_linestring(coords, interval_m=50)
        assert result == [(41.38, 2.15)]

    def test_empty_coords_returns_empty(self):
        result = resample_linestring([], interval_m=50)
        assert result == []

    def test_returns_lat_lon_tuples(self):
        coords = [[2.15, 41.38], [2.16, 41.39]]
        result = resample_linestring(coords, interval_m=50)
        for lat, lon in result:
            assert 41.0 < lat < 42.0
            assert 2.0 < lon < 3.0

    def test_invalid_interval_raises_error(self):
        coords = [[0.0, 0.0], [0.001, 0.001]]
        with pytest.raises(ValueError, match="interval_m must be positive"):
            resample_linestring(coords, interval_m=0)
        with pytest.raises(ValueError, match="interval_m must be positive"):
            resample_linestring(coords, interval_m=-10)


class TestComputeSlopes:
    def test_ascending_slope_is_positive(self):
        points = [(41.38, 2.15), (41.39, 2.16)]
        elevations = [100.0, 200.0]
        max_slope, min_slope, _, _ = compute_slopes(points, elevations)
        assert max_slope is not None
        assert max_slope > 0

    def test_descending_slope_is_negative(self):
        points = [(41.38, 2.15), (41.39, 2.16)]
        elevations = [200.0, 100.0]
        max_slope, min_slope, _, _ = compute_slopes(points, elevations)
        assert min_slope is not None
        assert min_slope < 0

    def test_flat_terrain_has_zero_slope(self):
        points = [(41.38, 2.15), (41.39, 2.16)]
        elevations = [100.0, 100.0]
        max_slope, min_slope, _, _ = compute_slopes(points, elevations)
        assert max_slope == pytest.approx(0.0, abs=0.01)
        assert min_slope == pytest.approx(0.0, abs=0.01)

    def test_none_elevations_are_skipped(self):
        points = [(41.38, 2.15), (41.39, 2.16), (41.40, 2.17)]
        elevations = [100.0, None, 200.0]
        max_slope, min_slope, _, _ = compute_slopes(points, elevations)
        assert max_slope is None
        assert min_slope is None

    def test_returns_segment_coordinates(self):
        points = [(41.38, 2.15), (41.39, 2.16)]
        elevations = [100.0, 150.0]
        _, _, max_seg, min_seg = compute_slopes(points, elevations)
        assert max_seg == ((2.15, 41.38), (2.16, 41.39))
        assert min_seg == ((2.15, 41.38), (2.16, 41.39))

    def test_identifies_steepest_segments(self):
        points = [(41.38, 2.15), (41.39, 2.16), (41.40, 2.17)]
        elevations = [100.0, 110.0, 200.0]
        max_slope, min_slope, max_seg, min_seg = compute_slopes(points, elevations)
        assert max_seg[0] == (2.16, 41.39)
        assert min_seg[0] == (2.15, 41.38)


class TestResampleWayCoords:
    def test_returns_resampled_way(self):
        geojson = json.dumps({
            "type": "LineString",
            "coordinates": [[2.15, 41.38], [2.16, 41.39]]
        })
        result = resample_way_coords(osm_id=123, geojson=geojson, interval_m=50)
        assert result is not None
        points, osm_id = result
        assert osm_id == 123
        assert len(points) >= 2

    def test_returns_none_for_single_coordinate(self):
        geojson = json.dumps({
            "type": "LineString",
            "coordinates": [[2.15, 41.38]]
        })
        assert resample_way_coords(osm_id=123, geojson=geojson, interval_m=50) is None


class TestEnrichWithMocking:
    @pytest.fixture
    def temp_db(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE ways (
                osm_id INTEGER PRIMARY KEY,
                way_type TEXT NOT NULL,
                name TEXT,
                geojson TEXT NOT NULL,
                tags TEXT,
                max_slope REAL,
                min_slope REAL,
                max_slope_start_lon REAL,
                max_slope_start_lat REAL,
                max_slope_end_lon REAL,
                max_slope_end_lat REAL,
                min_slope_start_lon REAL,
                min_slope_start_lat REAL,
                min_slope_end_lon REAL,
                min_slope_end_lat REAL,
                slope_enriched INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
        return db_path

    def _insert_way(self, db_path: Path, osm_id: int, slope_enriched: int = 0):
        geojson = json.dumps({
            "type": "LineString",
            "coordinates": [[2.15, 41.38], [2.16, 41.39]]
        })
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO ways (osm_id, way_type, geojson, slope_enriched) VALUES (?, ?, ?, ?)",
            (osm_id, "test", geojson, slope_enriched)
        )
        conn.commit()
        conn.close()

    def _mock_elevations(self, points):
        """Generate mock elevations: ascending from 100m by 1m per point."""
        return [100.0 + i for i in range(len(points))]

    @patch("enrich_slopes.fetch_elevations")
    def test_skips_already_enriched_ways(self, mock_fetch, temp_db):
        self._insert_way(temp_db, osm_id=1, slope_enriched=1)
        self._insert_way(temp_db, osm_id=2, slope_enriched=0)

        mock_fetch.side_effect = self._mock_elevations

        processed, skipped = enrich(temp_db)
        assert processed == 1
        assert skipped == 1

    @patch("enrich_slopes.fetch_elevations")
    def test_processes_unenriched_ways(self, mock_fetch, temp_db):
        self._insert_way(temp_db, osm_id=1, slope_enriched=0)
        self._insert_way(temp_db, osm_id=2, slope_enriched=0)

        mock_fetch.side_effect = self._mock_elevations

        processed, skipped = enrich(temp_db)
        assert processed == 2
        assert skipped == 0

    @patch("enrich_slopes.fetch_elevations")
    def test_recompute_processes_all_ways(self, mock_fetch, temp_db):
        self._insert_way(temp_db, osm_id=1, slope_enriched=1)
        self._insert_way(temp_db, osm_id=2, slope_enriched=1)

        mock_fetch.side_effect = self._mock_elevations

        processed, skipped = enrich(temp_db, recompute=True)
        assert processed == 2
        assert skipped == 0

    @patch("enrich_slopes.fetch_elevations")
    def test_updates_slope_enriched_flag(self, mock_fetch, temp_db):
        self._insert_way(temp_db, osm_id=1, slope_enriched=0)

        mock_fetch.side_effect = self._mock_elevations

        enrich(temp_db)

        conn = sqlite3.connect(temp_db)
        result = conn.execute("SELECT slope_enriched FROM ways WHERE osm_id = 1").fetchone()
        conn.close()
        assert result[0] == 1

    @patch("enrich_slopes.fetch_elevations")
    def test_stores_slope_values(self, mock_fetch, temp_db):
        self._insert_way(temp_db, osm_id=1, slope_enriched=0)

        mock_fetch.side_effect = self._mock_elevations

        enrich(temp_db)

        conn = sqlite3.connect(temp_db)
        result = conn.execute(
            "SELECT max_slope, min_slope FROM ways WHERE osm_id = 1"
        ).fetchone()
        conn.close()
        assert result[0] is not None
        assert result[1] is not None
