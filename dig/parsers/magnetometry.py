"""Bartington/Geoscan magnetometry format parser (Python wrapper)."""

from pathlib import Path
import numpy as np


class MagnetometryFile:
    """Bartington/Geoscan .dat/.grd format handler.

    Parses the .grd ASCII header for grid metadata and the .dat
    binary file for magnetic gradient measurements. Handles zig-zag
    traverse reversal.
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
        self._metadata: dict = {}
        self._data: np.ndarray | None = None

        if self.grd_path:
            self._parse_grd()
            self._load_data()

    def _parse_grd(self) -> None:
        """Parse the .grd ASCII header file."""
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
                        self._metadata[key] = val
                    break

    def _load_data(self) -> None:
        """Load and reshape the binary .dat file."""
        rows = int(self._metadata.get("ROWS", self._metadata.get("GRID_ROWS", 0)))
        cols = int(self._metadata.get("COLS", self._metadata.get("GRID_COLS", 0)))
        if rows == 0 or cols == 0:
            raise ValueError("Invalid grid dimensions in .grd file")

        raw = np.fromfile(self.dat_path, dtype=np.int16)
        expected = rows * cols
        if len(raw) < expected:
            raise ValueError(
                f"File too small: {len(raw)} values, expected {expected}"
            )

        grid = raw[:expected].reshape(rows, cols)

        # Unspool zig-zag: reverse every other row
        zigzag = self._metadata.get("ZIGZAG", "TRUE").upper()
        if zigzag in ("TRUE", "1", "YES"):
            grid[1::2] = grid[1::2, ::-1]

        self._data = grid

    @property
    def data(self) -> np.ndarray:
        """2D array of shape (rows, cols) with magnetic gradient values."""
        if self._data is None:
            raise RuntimeError("Data not loaded — check .grd file")
        return self._data

    @property
    def shape(self) -> tuple[int, int]:
        """Grid dimensions (rows, cols)."""
        return self.data.shape

    @property
    def cell_size(self) -> float:
        return float(self._metadata.get("CELL_SIZE", 0.5))

    def __repr__(self) -> str:
        return (
            f"MagnetometryFile(shape={self.shape}, "
            f"cell_size={self.cell_size})"
        )