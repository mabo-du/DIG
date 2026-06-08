"""Survey data model — the core abstraction for geophysical surveys."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from dig.models.audit import AuditTrail


@dataclass
class Survey:
    """A geophysical survey — the central data object.

    Holds memory-mapped trace data, header metadata, coordinate
    system, and an immutable processing history DAG.
    """

    path: Path
    format: str  # "dzt", "dt1", "magnetometry", "segy"

    # Data dimensions
    num_traces: int = 0
    samples_per_trace: int = 0
    bits_per_sample: int = 16

    # Time/depth parameters
    sample_interval_ns: float = 0.0
    time_window_ns: float = 0.0
    time_zero_ns: float = 0.0

    # Survey parameters
    traces_per_second: float = 0.0
    traces_per_meter: float = 0.0
    channels: int = 1

    # Spatial reference
    crs_epsg: Optional[int] = None
    origin_easting: float = 0.0
    origin_northing: float = 0.0
    rotation_deg: float = 0.0
    pixel_size_m: float = 0.0

    # Processing history (immutable DAG)
    audit: AuditTrail = field(default_factory=AuditTrail)

    # Data (memory-mapped, not loaded eagerly)
    _data: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def data(self) -> Optional[np.ndarray]:
        """Access the trace data array.

        Returns None if not loaded. Use load() to explicitly load.
        """
        return self._data

    def load(self) -> np.ndarray:
        """Load data into memory (for processing/visualization).

        For large surveys, prefer memory-mapped access via parsers.
        """
        if self._data is None:
            raise RuntimeError(
                "Data not loaded. Use a parser (DZTFile, DT1File, etc.) "
                "to create a Survey with data."
            )
        return self._data

    @property
    def shape(self) -> tuple[int, int]:
        """Data shape: (num_traces, samples_per_trace)."""
        return (self.num_traces, self.samples_per_trace)

    def __repr__(self) -> str:
        return (
            f"Survey(format={self.format}, "
            f"traces={self.num_traces}, "
            f"samples={self.samples_per_trace}, "
            f"steps={len(self.audit.steps)})"
        )
