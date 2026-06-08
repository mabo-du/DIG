"""Signal processing pipeline — DAG-based, immutable processing steps."""

from dig.processing import (
    time_zero,
    dewow,
    background,
    bandpass,
    gain,
    topography,
    migration,
    detection,
    batch,
    assembly,
    magnetometry as mag_processing,
)
from dig.processing.pipeline import ProcessingPipeline, ProcessingNode

__all__ = [
    "time_zero",
    "dewow",
    "background",
    "bandpass",
    "gain",
    "topography",
    "migration",
    "detection",
    "batch",
    "assembly",
    "mag_processing",
    "ProcessingPipeline",
    "ProcessingNode",
]
