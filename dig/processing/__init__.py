"""Signal processing pipeline — DAG-based, immutable processing steps."""

from dig.processing import (
    time_zero,
    dewow,
    background,
    bandpass,
    gain,
    topography,
    migration,
    magnetometry as mag_processing,
)

__all__ = [
    "time_zero",
    "dewow",
    "background",
    "bandpass",
    "gain",
    "topography",
    "migration",
    "mag_processing",
]