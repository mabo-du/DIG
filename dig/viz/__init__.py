"""2D/3D visualization — radargram, time-slice, magnetometry, volume rendering."""

from dig.viz.colormaps import COLORMAPS, apply_colormap
from dig.viz.radargram_widget import RadargramWidget
from dig.viz.controls import ControlPanel
from dig.viz.history_panel import HistoryPanel
from dig.viz.velocity_panel import VelocityPanel
from dig.viz.volume_widget import VolumeWidget
from dig.viz.slice_navigator import SliceNavigator

__all__ = [
    "COLORMAPS",
    "apply_colormap",
    "RadargramWidget",
    "ControlPanel",
    "HistoryPanel",
    "VelocityPanel",
    "VolumeWidget",
    "SliceNavigator",
]
