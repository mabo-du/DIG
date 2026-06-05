"""CSV export for GIS and spreadsheet import."""

from pathlib import Path
import numpy as np
import pandas as pd


def export_csv(
    data: np.ndarray,
    output_path: str | Path,
    x_coords: np.ndarray | None = None,
    y_coords: np.ndarray | None = None,
    depth_labels: list[str] | None = None,
) -> str:
    """Export processed data as CSV.

    Args:
        data: 2D (rows, cols) or 3D (bands, rows, cols) array
        output_path: Output .csv path
        x_coords: X coordinates for each column
        y_coords: Y coordinates for each row
        depth_labels: Labels for each band/depth

    Returns:
        Path to the written CSV
    """
    output_path = Path(output_path)

    if data.ndim == 3:
        # Multi-band: one column per band
        n_bands, n_rows, n_cols = data.shape
        rows_list = []
        for i in range(n_rows):
            for j in range(n_cols):
                row = {
                    "row": i,
                    "col": j,
                }
                if x_coords is not None:
                    row["x"] = x_coords[j] if j < len(x_coords) else j
                if y_coords is not None:
                    row["y"] = y_coords[i] if i < len(y_coords) else i
                for b in range(n_bands):
                    label = depth_labels[b] if depth_labels and b < len(depth_labels) else f"band_{b}"
                    row[label] = data[b, i, j]
                rows_list.append(row)
        df = pd.DataFrame(rows_list)
    else:
        # 2D: simple grid
        df = pd.DataFrame(data)

    df.to_csv(output_path, index=False)
    return str(output_path)