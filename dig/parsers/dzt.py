"""GSSI .DZT format parser (Python wrapper around Rust core)."""

from pathlib import Path
import numpy as np
from dig.core import parse_dzt, PySurvey


class DZTFile:
    """GSSI .DZT format handler.

    Wraps the Rust DZT parser and provides NumPy array access
    to trace data via memory-mapped I/O.
    """

    def __init__(self, path: str | Path):
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
            offset=self._header_offset,
        )
        self._data = self._data.reshape(
            (self._survey.num_traces, self._survey.samples_per_trace)
        )

    @property
    def _header_offset(self) -> int:
        """Calculate header byte offset (matches Rust logic)."""
        rh_data = 1024  # placeholder — will be parsed from Rust
        if self._survey.bits_per_sample == 16:
            return 1024
        return 1024

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
    def time_window_ns(self) -> float:
        return self._survey.time_window_ns

    @property
    def sample_interval_ns(self) -> float:
        return self._survey.sample_interval_ns

    @property
    def traces_per_meter(self) -> float:
        return self._survey.traces_per_meter

    def __repr__(self) -> str:
        return (
            f"DZTFile(traces={self.num_traces}, "
            f"samples={self.samples_per_trace}, "
            f"bits={self._survey.bits_per_sample})"
        )