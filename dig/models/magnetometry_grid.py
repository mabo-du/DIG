"""Magnetometry grid model."""

from dataclasses import dataclass
import numpy as np


@dataclass
class MagnetometryGrid:
    """A 2D magnetometry grid.

    Represents gridded magnetic gradient data with spatial metadata.
    """

    data: np.ndarray  # 2D array (rows, cols)
    cell_size_m: float = 0.5
    origin_easting: float = 0.0
    origin_northing: float = 0.0
    rotation_deg: float = 0.0

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    @property
    def n_rows(self) -> int:
        return self.data.shape[0]

    @property
    def n_cols(self) -> int:
        return self.data.shape[1]

    @property
    def extent_m(self) -> tuple[float, float, float, float]:
        """Bounding box in metres (west, east, south, north)."""
        w = self.origin_easting
        e = w + self.n_cols * self.cell_size_m
        s = self.origin_northing
        n = s + self.n_rows * self.cell_size_m
        return (w, e, s, n)