"""GSSI .DZT format parser (Python wrapper around Rust core)."""

from pathlib import Path
from typing import Optional
import numpy as np
from dig.core import parse_dzt, parse_dzg, PySurvey


class DZTFile:
    """GSSI .DZT format handler.

    Wraps the Rust DZT parser and provides NumPy array access
    to trace data via memory-mapped I/O. Supports .DZG sidecar
    GPS files for georeferencing.

    Usage:
        dzt = DZTFile("survey.dzt")
        data = dzt.traces          # (num_traces, samples_per_trace) array
        gps = dzt.gps_positions    # [(trace_idx, lat, lon, alt), ...]
    """

    def __init__(self, path: str | Path, dzg_path: str | Path | None = None):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"DZT file not found: {path}")

        # Parse header via Rust backend
        self._survey: PySurvey = parse_dzt(str(self.path))

        # Memory-map the raw data for trace access
        self._data = np.memmap(
            self.path,
            dtype=self._numpy_dtype,
            mode="r",
            offset=self._survey.header_offset,
        )
        self._data = self._data.reshape(
            (self._survey.num_traces, self._survey.samples_per_trace)
        )

        # Parse optional .DZG sidecar GPS file
        self._gps_positions: list[tuple[int, float, float, float]] = []
        if dzg_path:
            self._load_dzg(dzg_path)
        else:
            # Auto-discover .DZG sidecar (same stem, .dzg extension)
            auto_dzg = self.path.with_suffix(".dzg")
            if auto_dzg.exists():
                self._load_dzg(auto_dzg)

    def _load_dzg(self, dzg_path: str | Path) -> None:
        """Load GPS positions from a .DZG sidecar file."""
        self._gps_positions = parse_dzg(str(dzg_path))

    @property
    def _numpy_dtype(self) -> np.dtype:
        mapping = {8: np.uint8, 16: np.int16, 32: np.int32}
        return mapping.get(self._survey.bits_per_sample, np.int16)

    @property
    def traces(self) -> np.ndarray:
        """2D array of shape (num_traces, samples_per_trace)."""
        return self._data

    @property
    def num_traces(self) -> int:
        return self._survey.num_traces

    @property
    def samples_per_trace(self) -> int:
        return self._survey.samples_per_trace

    @property
    def bits_per_sample(self) -> int:
        return self._survey.bits_per_sample

    @property
    def channels(self) -> int:
        return self._survey.channels

    @property
    def header_offset(self) -> int:
        return self._survey.header_offset

    @property
    def time_window_ns(self) -> float:
        return self._survey.time_window_ns

    @property
    def sample_interval_ns(self) -> float:
        return self._survey.sample_interval_ns

    @property
    def traces_per_second(self) -> float:
        return self._survey.traces_per_second

    @property
    def traces_per_meter(self) -> float:
        return self._survey.traces_per_meter

    @property
    def time_zero_ns(self) -> float:
        return self._survey.time_zero_ns

    @property
    def gps_positions(self) -> list[tuple[int, float, float, float]]:
        """GPS positions from .DZG sidecar: [(trace_idx, lat, lon, alt), ...]."""
        return list(self._gps_positions)

    @property
    def has_gps(self) -> bool:
        return len(self._gps_positions) > 0

    def get_trace(self, index: int) -> np.ndarray:
        """Return a single trace as a 1D array."""
        if index < 0 or index >= self.num_traces:
            raise IndexError(
                f"Trace index {index} out of range (0-{self.num_traces - 1})"
            )
        return self._data[index, :]

    def __repr__(self) -> str:
        gps_info = f", gps={len(self._gps_positions)} fixes" if self.has_gps else ""
        return (
            f"DZTFile(traces={self.num_traces}, "
            f"samples={self.samples_per_trace}, "
            f"bits={self.bits_per_sample}"
            f"{gps_info})"
        )