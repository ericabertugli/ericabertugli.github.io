import csv
import tempfile
from collections import Counter
from pathlib import Path

from fit_to_h3 import points_to_h3_cells, process_fit_folder, write_csv


def test_points_to_h3_cells_converts_coordinates():
    points = [(41.3874, 2.1686, "generic"), (41.3875, 2.1687, "running")]
    cells = points_to_h3_cells(points, resolution=13)
    assert len(cells) == 2
    assert all(isinstance(c[0], str) for c in cells)
    assert all(c[0].startswith("8d") for c in cells)
    assert cells[0][1] == "generic"
    assert cells[1][1] == "running"


def test_points_to_h3_cells_same_location_same_cell():
    points = [(41.3874, 2.1686, "generic"), (41.3874, 2.1686, "generic")]
    cells = points_to_h3_cells(points, resolution=13)
    assert cells[0][0] == cells[1][0]


def test_points_to_h3_cells_empty_input():
    cells = points_to_h3_cells([], resolution=13)
    assert cells == []


def test_points_to_h3_cells_different_resolutions():
    points = [(41.3874, 2.1686, "generic")]
    cell_13 = points_to_h3_cells(points, resolution=13)[0][0]
    cell_10 = points_to_h3_cells(points, resolution=10)[0][0]
    assert cell_13 != cell_10


def test_process_fit_folder_empty_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        counter = process_fit_folder(Path(tmpdir), resolution=13, activity_filter=None)
        assert counter == Counter()


def test_write_csv_creates_valid_file():
    counter = Counter({
        ("8d39a339a4b13ff", "generic"): 5,
        ("8d39a339a4b11ff", "running"): 3,
    })
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        output_path = Path(f.name)

    write_csv(counter, output_path)

    with open(output_path) as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows[0] == ["h3_cell", "activity_type", "count"]
    assert rows[1] == ["8d39a339a4b13ff", "generic", "5"]
    assert rows[2] == ["8d39a339a4b11ff", "running", "3"]
    output_path.unlink()
