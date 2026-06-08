"""3D GPR volume model — assembled from multiple 2D profiles."""

from dataclasses import dataclass

import numpy as np


@dataclass
class Grid3D:
    """A 3D GPR volume assembled from multiple parallel profiles.

    Dimensions: (inline, crossline, depth/time)
    """

    data: np.ndarray  # 3D array (inline, crossline, depth)
    inline_spacing_m: float = 0.05
    crossline_spacing_m: float = 0.5
    sample_interval_ns: float = 0.1

    # Coordinate reference
    origin_easting: float = 0.0
    origin_northing: float = 0.0
    rotation_deg: float = 0.0

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.data.shape

    @property
    def n_inline(self) -> int:
        return self.data.shape[0]

    @property
    def n_crossline(self) -> int:
        return self.data.shape[1]

    @property
    def n_depth(self) -> int:
        return self.data.shape[2]

    def time_slice(self, depth_index: int) -> np.ndarray:
        """Extract a single time/depth slice."""
        return self.data[:, :, depth_index]

    def inline_section(self, inline_index: int) -> np.ndarray:
        """Extract a single inline profile."""
        return self.data[inline_index, :, :]

    def crossline_section(self, crossline_index: int) -> np.ndarray:
        """Extract a single crossline profile."""
        return self.data[:, crossline_index, :]
