# From Tracks to Frequent Routes

Analyze GPS tracks from .fit files to identify frequently traveled routes using H3 spatial indexing.

## How it works

1. Reads all `.fit` files from a folder
2. Extracts GPS coordinates from each track
3. Maps each point to an H3 hexagonal cell (default resolution: 13)
4. Counts how many times each cell appears across all tracks
5. Outputs a CSV with cell IDs and occurrence counts

## Usage

```bash
cd scripts/tracks-to-routes
uv run python fit_to_h3.py /path/to/fit/files -o output.csv
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output CSV file path | `h3_counts.csv` |
| `-r, --resolution` | H3 resolution (0-15, higher = smaller cells) | `13` |

### H3 Resolution Reference

| Resolution | Avg cell area |
|------------|---------------|
| 10 | ~15,000 m² |
| 11 | ~2,100 m² |
| 12 | ~300 m² |
| 13 | ~43 m² |
| 14 | ~6 m² |

## Output

CSV with two columns:

```csv
h3_cell,count
8d39a339a4b13ff,42
8d39a339a4b11ff,38
```

Cells are sorted by count (most frequent first).
