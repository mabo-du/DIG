"""Sensors & Software .DT1/.HD format parser (Python wrapper)."""

from pathlib import Path

import numpy as np

from dig.core import PySurvey, parse_dt1


class DT1File:
    """Sensors & Software .DT1/.HD format handler.

    The .HD ASCII header provides survey-level metadata (samples per trace,
    time window, channels). The .DT1 binary file contains interleaved
    128-byte trace headers and trace data.

    Usage:
        dt1 = DT1File("survey.dt1")
        data = dt1.traces              # (num_traces, samples_per_trace) array
        pos = dt1.trace_positions      # odometer position per trace (m)
    """

    def __init__(self, dt1_path: str | Path, hd_path: str | Path | None = None):
        self.dt1_path = Path(dt1_path)
        if not self.dt1_path.exists():
            raise FileNotFoundError(f"DT1 file not found: {dt1_path}")

        # Auto-discover .HD file
        if hd_path is None:
            candidates = [
                self.dt1_path.with_suffix(".HD"),
                self.dt1_path.with_suffix(".hd"),
            ]
            for c in candidates:
                if c.exists():
                    hd_path = c
                    break
        self.hd_path = Path(hd_path) if hd_path and Path(hd_path).exists() else None

        # Read .HD content for Rust parser
        hd_content: str | None = None
        self._hd_metadata: dict[str, str] = {}
        if self.hd_path:
            hd_content = self.hd_path.read_text()
            self._parse_hd(hd_content)

        # Parse via Rust backend (passes .HD content for metadata)
        self._survey: PySurvey = parse_dt1(str(self.dt1_path), hd_content)

        # Convert trace data from Rust to numpy array
        self._build_traces()

    def _parse_hd(self, content: str) -> None:
        """Parse .HD key=value pairs into a dict."""
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                self._hd_metadata[key.strip()] = val.strip()

    def _build_traces(self) -> None:
        """Convert raw trace data bytes to numpy array."""
        raw = bytes(self._survey.trace_data)
        dtype = self._numpy_dtype
        expected_bytes = self.num_traces * self.samples_per_trace * dtype.itemsize

        if len(raw) == 0:
            self._traces = np.empty((0, 0), dtype=dtype)
        elif len(raw) >= expected_bytes:
            self._traces = np.frombuffer(raw[:expected_bytes], dtype=dtype).reshape(
                self.num_traces, self.samples_per_trace
            )
        else:
            # Partial data — pad with zeros
            arr = np.frombuffer(raw, dtype=dtype)
            total = self.num_traces * self.samples_per_trace
            if len(arr) < total:
                arr = np.pad(arr, (0, total - len(arr)))
            self._traces = arr.reshape(self.num_traces, self.samples_per_trace)

    @property
    def _numpy_dtype(self) -> np.dtype:
        mapping = {8: np.dtype(np.uint8), 16: np.dtype(np.int16), 32: np.dtype(np.int32)}
        return mapping.get(self._survey.bits_per_sample, np.dtype(np.int16))

    @property
    def traces(self) -> np.ndarray:
        """2D array of shape (num_traces, samples_per_trace)."""
        return self._traces

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
    def time_window_ns(self) -> float:
        return self._survey.time_window_ns

    @property
    def sample_interval_ns(self) -> float:
        return self._survey.sample_interval_ns

    @property
    def time_zero_ns(self) -> float:
        return self._survey.time_zero_ns

    @property
    def trace_positions(self) -> list[float]:
        """Odometer position (m) for each trace."""
        return list(self._survey.trace_positions)

    @property
    def trace_time_zeros(self) -> list[float]:
        """Time-zero offset (ns) for each trace."""
        return list(self._survey.trace_time_zeros)

    @property
    def trace_elevations(self) -> list[float]:
        """GPS elevation (m) for each trace."""
        return list(self._survey.trace_elevations)

    @property
    def hd_metadata(self) -> dict[str, str]:
        """Raw .HD key-value pairs."""
        return dict(self._hd_metadata)

    def get_trace(self, index: int) -> np.ndarray:
        """Return a single trace as a 1D array."""
        if index < 0 or index >= self.num_traces:
            raise IndexError(f"Trace index {index} out of range (0-{self.num_traces - 1})")
        return self._traces[index, :]

    def __repr__(self) -> str:
        return (
            f"DT1File(traces={self.num_traces}, "
            f"samples={self.samples_per_trace}, "
            f"bits={self.bits_per_sample})"
        )
