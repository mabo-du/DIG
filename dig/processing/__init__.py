"""Signal processing pipeline — DAG-based, immutable processing steps."""

from dig.processing import (
    assembly,
    background,
    bandpass,
    batch,
    detection,
    dewow,
    gain,
    migration,
    time_zero,
    topography,
)
from dig.processing import (
    magnetometry as mag_processing,
)
from dig.processing.pipeline import ProcessingNode, ProcessingPipeline

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
