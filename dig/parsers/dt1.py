"""Sensors & Software .DT1/.HD format parser (Python wrapper)."""

from pathlib import Path
import numpy as np
from dig.core import parse_dt1, PySurvey


class DT1File:
    """Sensors & Software .DT1/.HD format handler.

    Wraps the Rust DT1 parser. The .HD ASCII header provides
    global survey parameters; the .DT1 binary file contains
    interleaved trace headers and data.
    """

    def __init__(self, dt1_path: str | Path, hd_path: str | Path | None = None):
        self.dt1_path = Path(dt1_path)
        if not self.dt1_path.exists():
            raise FileNotFoundError(f"DT1 file not found: {dt1_path}")

        # Auto-discover .HD file
        if hd_path is None:
            hd_path = self.dt1_path.with_suffix(".HD")
            if not hd_path.exists():
                hd_path = self.dt1_path.with_suffix(".hd")
        self.hd_path = Path(hd_path) if hd_path else None

        # Parse header via Rust backend
        self._survey: PySurvey = parse_dt1(str(self.dt1_path))

        # Parse .HD metadata
        self._hd_metadata: dict = {}
        if self.hd_path and self.hd_path.exists():
            self._parse_hd()

    def _parse_hd(self) -> None:
        """Parse the .HD ASCII header file."""
        content = self.hd_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if "=" in line:
                key, _, val = line.partition("=")
                self._hd_metadata[key.strip()] = val.strip()

    @property
    def num_traces(self) -> int:
        return self._survey.num_traces

    @property
    def samples_per_trace(self) -> int:
        return self._survey.samples_per_trace

    @property
    def hd_metadata(self) -> dict:
        return dict(self._hd_metadata)

    def __repr__(self) -> str:
        return (
            f"DT1File(traces={self.num_traces}, "
            f"samples={self.samples_per_trace})"
        )