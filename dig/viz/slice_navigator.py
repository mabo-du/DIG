"""dig/viz/slice_navigator.py — Dockable panel linking inline, crossline, and time-slice 2D views.

exports: SliceNavigator
used_by: dig/main_window.py
rules:
  - Updates must be linked to volume_widget slice selections.
"""

from typing import Optional
from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt
import numpy as np

from dig.viz.radargram_widget import RadargramWidget
from dig.models.grid import Grid3D


class SliceNavigator(QDockWidget):
    """Panel containing three 2D RadargramWidgets for inline, crossline, and depth slices."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Slice Navigator", parent)
        
        self.grid: Optional[Grid3D] = None
        
        # Main widget
        self.main_widget = QWidget()
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Vertical)
        
        self.inline_view = RadargramWidget()
        self.crossline_view = RadargramWidget()
        self.time_slice_view = RadargramWidget()
        
        self.inline_view.plot.setTitle("Inline")
        self.crossline_view.plot.setTitle("Crossline")
        self.time_slice_view.plot.setTitle("Time Slice")
        
        # Override time slice labels since it plots crossline vs inline
        self.time_slice_view.plot.setLabel("bottom", "Inline")
        self.time_slice_view.plot.setLabel("left", "Crossline", units="m")
        
        self.splitter.addWidget(self.inline_view)
        self.splitter.addWidget(self.crossline_view)
        self.splitter.addWidget(self.time_slice_view)
        
        self.layout.addWidget(self.splitter)
        self.setWidget(self.main_widget)
        
    def set_grid(self, grid: Grid3D) -> None:
        self.grid = grid
        
    def update_slices(self, inline_idx: int, crossline_idx: int, depth_idx: int) -> None:
        """Update 2D views based on the selected indices from the 3D volume."""
        if self.grid is None:
            return
            
        # Inline section: trace = crossline, sample = depth
        inline_data = self.grid.inline_section(inline_idx)
        self.inline_view.set_data(
            inline_data,
            sample_interval_ns=self.grid.sample_interval_ns,
            time_zero_ns=0.0
        )
        self.inline_view.plot.setTitle(f"Inline {inline_idx}")
        
        # Crossline section: trace = inline, sample = depth
        crossline_data = self.grid.crossline_section(crossline_idx)
        self.crossline_view.set_data(
            crossline_data,
            sample_interval_ns=self.grid.sample_interval_ns,
            time_zero_ns=0.0
        )
        self.crossline_view.plot.setTitle(f"Crossline {crossline_idx}")
        
        # Time slice section: shape (inline, crossline)
        time_slice_data = self.grid.time_slice(depth_idx)
        self.time_slice_view.set_data(
            time_slice_data,
            sample_interval_ns=self.grid.crossline_spacing_m,
            time_zero_ns=0.0
        )
        self.time_slice_view.plot.setTitle(f"Time Slice {depth_idx}")
