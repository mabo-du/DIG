"""Format parsers for geophysical instruments."""

from dig.parsers.dzt import DZTFile
from dig.parsers.dt1 import DT1File
from dig.parsers.magnetometry import MagnetometryFile
from dig.parsers.segy import SEGYFile

__all__ = [
    "DZTFile",
    "DT1File",
    "MagnetometryFile",
    "SEGYFile",
]