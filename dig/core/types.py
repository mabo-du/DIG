"""Python-side type wrappers and data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessingStep:
    """A single step in the processing history DAG."""

    name: str
    parameters: dict
    timestamp: float
    software_version: str


@dataclass
class CoordinateSystem:
    """Coordinate reference system and affine transform."""

    epsg: Optional[int] = None
    wkt: Optional[str] = None
    origin_easting: float = 0.0
    origin_northing: float = 0.0
    pixel_size_x: float = 0.0
    pixel_size_y: float = 0.0
    rotation_deg: float = 0.0


@dataclass
class SurveyMetadata:
    """High-level survey metadata."""

    format: str
    num_traces: int
    samples_per_trace: int
    bits_per_sample: int
    sample_interval_ns: float
    time_window_ns: float
    channels: int
    coordinate_system: CoordinateSystem = field(default_factory=CoordinateSystem)
    history: list[ProcessingStep] = field(default_factory=list)