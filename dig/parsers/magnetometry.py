"""Bartington/Geoscan magnetometry format parser (Python wrapper)."""

from pathlib import Path
from typing import Optional
import numpy as np
from dig.core import parse_magnetometry, PySurvey

# Void/sentinel value for missing data (matches Rust VOID_I16)
VOID_VALUE = -32768


class MagnetometryFile:
    """Bartington/Geoscan .dat/.grd format handler.

    Parses the .grd ASCII header for grid metadata and the .dat
    binary file for magnetic gradient measurements. Handles zig-zag
    traverse reversal and void value detection.

    Usage:
        mag = MagnetometryFile("survey.dat", "survey.grd")
        data = mag.data              # (rows, cols) int16 array
        grid = mag.grid_metadata     # dict of .grd parameters
    """

    def __init__(self, dat_path: str | Path, grd_path: str | Path | None = None):
        self.dat_path = Path(dat_path)
        if not self.dat_path.exists():
            raise FileNotFoundError(f"DAT file not found: {dat_path}")

        # Auto-discover .grd file
        if grd_path is None:
            candidates = [
                self.dat_path.with_suffix(".grd"),
                self.dat_path.with_suffix(".GRD"),
            ]
            grd_path = next((p for p in candidates if p.exists()), None)

        self.grd_path = Path(grd_path) if grd_path else None
        if not self.grd_path or not self.grd_path.exists():
            raise FileNotFoundError(
                f"GRD file not found for {dat_path}"
            )

        # Parse via Rust backend
        self._survey: PySurvey = parse_magnetometry(
            str(self.dat_path), str(self.grd_path)
        )

        # Build numpy grid from trace_data
        self._build_grid()

        # Parse raw .grd metadata for dict access
        self._raw_metadata: dict[str, str] = {}
        self._parse_raw_grd()

    def _build_grid(self) -> None:
        """Convert raw trace data bytes to 2D numpy array."""
        raw = bytes(self._survey.trace_data)
        rows = self._survey.num_traces
        cols = self._survey.samples_per_trace
        expected = rows * cols * 2  # int16

        if len(raw) >= expected:
            self._data = np.frombuffer(
                raw[:expected], dtype=np.int16
            ).reshape(rows, cols)
        else:
            self._data = np.zeros((rows, cols), dtype=np.int16)

    def _parse_raw_grd(self) -> None:
        """Parse .grd file for raw metadata dict."""
        content = self.grd_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "//")):
                continue
            for sep in (" ", "=", ":"):
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        key, val = parts[0].strip().upper(), parts[1].strip()
                        self._raw_metadata[key] = val
                    break

    @property
    def data(self) -> np.ndarray:
        """2D array of shape (rows, cols) with magnetic gradient values (int16).

        Void values (-32768) indicate missing/no-data cells.
        Use np.ma.masked_equal(mag.data, VOID_VALUE) for masked arrays.
        """
        return self._data

    @property
    def shape(self) -> tuple[int, int]:
        """Grid dimensions (rows, cols)."""
        return (self._survey.num_traces, self._survey.samples_per_trace)

    @property
    def rows(self) -> int:
        return self._survey.num_traces

    @property
    def cols(self) -> int:
        return self._survey.samples_per_trace

    @property
    def cell_size(self) -> float:
        """Grid cell size in meters."""
        if len(self._survey.trace_positions) >= 3:
            return self._survey.trace_positions[2]
        return 0.5

    @property
    def origin_easting(self) -> float:
        """Grid origin easting coordinate."""
        if len(self._survey.trace_elevations) >= 1:
            return self._survey.trace_elevations[0]
        return 0.0

    @property
    def origin_northing(self) -> float:
        """Grid origin northing coordinate."""
        if len(self._survey.trace_elevations) >= 2:
            return self._survey.trace_elevations[1]
        return 0.0

    @property
    def rotation_deg(self) -> float:
        """Grid rotation in degrees."""
        if len(self._survey.trace_positions) >= 4:
            return self._survey.trace_positions[3]
        return 0.0

    @property
    def grid_metadata(self) -> dict[str, str]:
        """Raw .grd key-value pairs."""
        return dict(self._raw_metadata)

    @property
    def void_mask(self) -> np.ndarray:
        """Boolean mask: True where data is void/missing."""
        return self._data == VOID_VALUE

    def __repr__(self) -> str:
        return (
            f"MagnetometryFile(shape=({self.rows}, {self.cols}), "
            f"cell_size={self.cell_size})"
        )