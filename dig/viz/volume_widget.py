"""dig/viz/volume_widget.py — PyVista 3D volume rendering widget for GPR grids.

exports: VolumeWidget
used_by: dig/viz/__init__.py, dig/main_window.py
rules:
  - PyVista QtInteractor should be used to embed the renderer.
  - Slices, volume rendering, and isosurfaces must be toggleable.
"""

from typing import Optional
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QCheckBox, 
    QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal
from dig.models.grid import Grid3D


class VolumeWidget(QWidget):
    """3D volume viewer using PyVista for Grid3D."""
    
    slice_changed = Signal(int, int, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.grid: Optional[Grid3D] = None
        
        self.layout = QVBoxLayout(self)
        
        # PyVista Interactor
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor, stretch=1)
        
        # Controls Layout
        controls_layout = QHBoxLayout()
        self.layout.addLayout(controls_layout)
        
        # Slices controls
        slices_group = QGroupBox("Orthogonal Slices")
        slices_layout = QFormLayout()
        
        self.show_slices_cb = QCheckBox("Show Slices")
        self.show_slices_cb.setChecked(True)
        self.show_slices_cb.stateChanged.connect(self._update_visibility)
        slices_layout.addRow("", self.show_slices_cb)
        
        self.inline_slider = QSlider(Qt.Horizontal)
        self.inline_slider.valueChanged.connect(self._update_slices)
        slices_layout.addRow("Inline", self.inline_slider)
        
        self.crossline_slider = QSlider(Qt.Horizontal)
        self.crossline_slider.valueChanged.connect(self._update_slices)
        slices_layout.addRow("Crossline", self.crossline_slider)
        
        self.depth_slider = QSlider(Qt.Horizontal)
        self.depth_slider.valueChanged.connect(self._update_slices)
        slices_layout.addRow("Depth", self.depth_slider)
        
        slices_group.setLayout(slices_layout)
        controls_layout.addWidget(slices_group)
        
        # Volume rendering / Isosurface controls
        vol_group = QGroupBox("Volume / Isosurface")
        vol_layout = QVBoxLayout()
        
        self.show_vol_cb = QCheckBox("Show Volume")
        self.show_vol_cb.stateChanged.connect(self._update_visibility)
        vol_layout.addWidget(self.show_vol_cb)
        
        self.show_iso_cb = QCheckBox("Show Isosurface")
        self.show_iso_cb.stateChanged.connect(self._update_visibility)
        vol_layout.addWidget(self.show_iso_cb)
        
        iso_slider_layout = QHBoxLayout()
        iso_slider_layout.addWidget(QLabel("Iso Threshold"))
        self.iso_slider = QSlider(Qt.Horizontal)
        self.iso_slider.valueChanged.connect(self._update_isosurface)
        iso_slider_layout.addWidget(self.iso_slider)
        vol_layout.addLayout(iso_slider_layout)
        
        vol_group.setLayout(vol_layout)
        controls_layout.addWidget(vol_group)
        
        self.mesh: Optional[pv.ImageData] = None
        self.x_actor = None
        self.y_actor = None
        self.z_actor = None
        self.vol_actor = None
        self.iso_actor = None
        self.iso_val = 0.5
        
    def set_grid(self, grid: Grid3D) -> None:
        """Load a new Grid3D object and initialize visualization."""
        self.grid = grid
        
        # Create PyVista ImageData
        self.mesh = pv.ImageData()
        # Dimensions are n_inline, n_crossline, n_depth
        self.mesh.dimensions = np.array(grid.shape)
        # Spacing
        self.mesh.spacing = (
            grid.inline_spacing_m,
            grid.crossline_spacing_m,
            grid.sample_interval_ns
        )
        self.mesh.origin = (
            grid.origin_easting,
            grid.origin_northing,
            0.0 # depth origin
        )
        
        # Assign data. PyVista uses Fortran ordering typically for flattening
        self.mesh.point_data["values"] = grid.data.flatten(order="F")
        self.mesh.set_active_scalars("values")
        
        # Configure sliders
        self.inline_slider.setRange(0, grid.shape[0] - 1)
        self.inline_slider.setValue(grid.shape[0] // 2)
        
        self.crossline_slider.setRange(0, grid.shape[1] - 1)
        self.crossline_slider.setValue(grid.shape[1] // 2)
        
        self.depth_slider.setRange(0, grid.shape[2] - 1)
        self.depth_slider.setValue(grid.shape[2] // 2)
        
        v_min, v_max = float(np.min(grid.data)), float(np.max(grid.data))
        self.iso_slider.setRange(0, 100)
        self.iso_slider.setValue(50)
        self.iso_val = v_min + (v_max - v_min) * 0.5
        
        self.plotter.clear()
        
        # Setup actors
        self._create_slices()
        self._create_volume()
        if self.show_iso_cb.isChecked():
            self._create_isosurface()
        
        self._update_visibility()
        self.plotter.reset_camera()
        self.plotter.show_axes()
        
    def _create_slices(self) -> None:
        if self.mesh is None: return
        self._update_slices()
        
    def _update_slices(self) -> None:
        if self.mesh is None: return
        
        if not self.show_slices_cb.isChecked():
            if self.x_actor: self.x_actor.SetVisibility(False)
            if self.y_actor: self.y_actor.SetVisibility(False)
            if self.z_actor: self.z_actor.SetVisibility(False)
            self.plotter.render()
            return
            
        x_idx = self.inline_slider.value()
        y_idx = self.crossline_slider.value()
        z_idx = self.depth_slider.value()
        
        phys_x = self.mesh.origin[0] + x_idx * self.mesh.spacing[0]
        phys_y = self.mesh.origin[1] + y_idx * self.mesh.spacing[1]
        phys_z = self.mesh.origin[2] + z_idx * self.mesh.spacing[2]
        
        # We use name to replace the existing mesh
        x_slice = self.mesh.slice(normal='x', origin=(phys_x, 0, 0))
        y_slice = self.mesh.slice(normal='y', origin=(0, phys_y, 0))
        z_slice = self.mesh.slice(normal='z', origin=(0, 0, phys_z))
        
        self.x_actor = self.plotter.add_mesh(x_slice, cmap="seismic", name="x_slice", show_scalar_bar=False)
        self.y_actor = self.plotter.add_mesh(y_slice, cmap="seismic", name="y_slice", show_scalar_bar=False)
        self.z_actor = self.plotter.add_mesh(z_slice, cmap="seismic", name="z_slice", show_scalar_bar=False)
        
        self.x_actor.SetVisibility(True)
        self.y_actor.SetVisibility(True)
        self.z_actor.SetVisibility(True)
        
        self.slice_changed.emit(x_idx, y_idx, z_idx)
        
    def _create_volume(self) -> None:
        if self.mesh is None: return
        opacity = [0, 0, 0, 0.1, 0.2, 0.5, 1.0]
        self.vol_actor = self.plotter.add_volume(self.mesh, cmap="seismic", opacity=opacity, name="volume")
        self.vol_actor.SetVisibility(self.show_vol_cb.isChecked())
        
    def _create_isosurface(self) -> None:
        if self.mesh is None or self.grid is None: return
        try:
            iso_mesh = self.mesh.contour([self.iso_val])
            self.iso_actor = self.plotter.add_mesh(iso_mesh, color="red", name="isosurface", opacity=0.5)
            self.iso_actor.SetVisibility(self.show_iso_cb.isChecked())
        except Exception:
            # If the value is outside contour bounds, it might raise an error or return empty
            if self.iso_actor:
                self.plotter.remove_actor(self.iso_actor)
                self.iso_actor = None
        
    def _update_isosurface(self) -> None:
        if self.mesh is None or self.grid is None: return
        v_min, v_max = float(np.min(self.grid.data)), float(np.max(self.grid.data))
        pct = self.iso_slider.value() / 100.0
        # Make sure not to use exact min/max to avoid contour errors
        self.iso_val = v_min + (v_max - v_min) * (0.01 + 0.98 * pct)
        if self.show_iso_cb.isChecked():
            self._create_isosurface()
        
    def _update_visibility(self) -> None:
        if self.vol_actor:
            self.vol_actor.SetVisibility(self.show_vol_cb.isChecked())
            
        if self.show_iso_cb.isChecked():
            self._update_isosurface()
        elif self.iso_actor:
            self.iso_actor.SetVisibility(False)
            
        self._update_slices()
        self.plotter.render()
