"""velocity_panel.py — Velocity analysis and hyperbola fitting for radargrams.
exports: VelocityPanel(radargram_widget: Any, parent: QWidget) -> VelocityPanel
used_by: dig/viz/main_window.py -> MainWindow
rules:
  - Hyperbola overlay must always be drawn on the RadargramWidget.
  - Picking interaction intercepts clicks to define apex and limb.
"""

import json
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QFileDialog, QMessageBox

class VelocityPanel(QtWidgets.QWidget):
    """Dockable panel for velocity analysis. Supports standalone/embedded modes
    and hyperbola picking overlaid on the provided RadargramWidget."""

    def __init__(self, radargram_widget: Any = None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.radargram_widget = radargram_widget
        self.hyperbolas: List[Dict[str, float]] = []
        
        # State for picking
        self.picking_mode = False
        self.current_apex: Optional[Tuple[float, float]] = None  # (trace, time)
        
        # UI Elements
        self.layout = QtWidgets.QVBoxLayout(self)
        
        # Mode toggle (Dockable standalone vs Embedded/Overlay)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Standalone Panel", "Embedded Overlay"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(QtWidgets.QLabel("View Mode:"))
        top_layout.addWidget(self.mode_combo)
        self.layout.addLayout(top_layout)
        
        # Controls
        controls_layout = QtWidgets.QHBoxLayout()
        self.btn_pick = QtWidgets.QPushButton("Pick Hyperbola")
        self.btn_pick.setCheckable(True)
        self.btn_pick.clicked.connect(self._on_pick_toggled)
        self.btn_clear = QtWidgets.QPushButton("Clear Picks")
        self.btn_clear.clicked.connect(self.clear_picks)
        self.btn_export = QtWidgets.QPushButton("Export JSON")
        self.btn_export.clicked.connect(self.export_json)
        
        controls_layout.addWidget(self.btn_pick)
        controls_layout.addWidget(self.btn_clear)
        controls_layout.addWidget(self.btn_export)
        self.layout.addLayout(controls_layout)
        
        # Trace Spacing Input
        spacing_layout = QtWidgets.QHBoxLayout()
        self.spin_spacing = QtWidgets.QDoubleSpinBox()
        self.spin_spacing.setValue(0.05)
        self.spin_spacing.setRange(0.001, 10.0)
        self.spin_spacing.setSingleStep(0.01)
        spacing_layout.addWidget(QtWidgets.QLabel("Trace Spacing (m):"))
        spacing_layout.addWidget(self.spin_spacing)
        self.layout.addLayout(spacing_layout)
        
        # Semblance Display
        self.layout.addWidget(QtWidgets.QLabel("Semblance Analysis:"))
        self.semblance_plot = pg.PlotWidget(title="Semblance (V vs T0)")
        self.semblance_plot.setLabel("left", "Time", units="ns")
        self.semblance_plot.setLabel("bottom", "Velocity", units="m/ns")
        self.semblance_image = pg.ImageItem()
        self.semblance_plot.addItem(self.semblance_image)
        self.layout.addWidget(self.semblance_plot)
        
        # Overlay item for hyperbolas
        self.hyperbola_plot_item = pg.PlotDataItem(pen=pg.mkPen('r', width=2))
        self.temp_hyperbola_item = pg.PlotDataItem(pen=pg.mkPen('y', width=2, style=QtCore.Qt.PenStyle.DashLine))
        self.scatter_item = pg.ScatterPlotItem(size=8, pen=pg.mkPen(None), brush=pg.mkBrush(255, 0, 0, 120))
        
        if self.radargram_widget is not None:
            self.radargram_widget.plot.addItem(self.hyperbola_plot_item)
            self.radargram_widget.plot.addItem(self.temp_hyperbola_item)
            self.radargram_widget.plot.addItem(self.scatter_item)
            
            # Hook up mouse events
            self.radargram_widget.plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)
            self.radargram_widget.plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _on_mode_changed(self, index: int) -> None:
        """Handle standalone vs embedded toggle (ui logic for parent container)."""
        pass  # In a full app, this would request the main window to dock/undock this panel.

    def _on_pick_toggled(self, checked: bool) -> None:
        self.picking_mode = checked
        if not checked:
            self.current_apex = None
            self.temp_hyperbola_item.setData([], [])

    def _on_mouse_clicked(self, event) -> None:
        if not self.picking_mode:
            return
            
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
            
        if self.radargram_widget is None:
            return

        vb = self.radargram_widget.plot.vb
        scene_pos = event.scenePos()
        if not vb.sceneBoundingRect().contains(scene_pos):
            return
            
        mouse_point = vb.mapSceneToView(scene_pos)
        trace = mouse_point.x()
        time = mouse_point.y()
        
        if self.current_apex is None:
            # First click: define apex
            self.current_apex = (trace, time)
            self._update_scatter()
        else:
            # Second click: define limb and compute velocity
            apex_trace, apex_time = self.current_apex
            dx = abs(trace - apex_trace) * self.spin_spacing.value()
            dt = time - apex_time
            
            if dt > 0 and dx > 0:
                t_sq_diff = time**2 - apex_time**2
                if t_sq_diff > 0:
                    v = np.sqrt(4 * dx**2 / t_sq_diff)
                    self.hyperbolas.append({
                        "apex_trace": apex_trace,
                        "apex_time": apex_time,
                        "velocity": v
                    })
                    self._update_hyperbolas()
                    self._update_semblance()
                    
            self.current_apex = None
            self.temp_hyperbola_item.setData([], [])
            self._update_scatter()
            event.accept()

    def _on_mouse_moved(self, pos) -> None:
        if not self.picking_mode or self.current_apex is None or self.radargram_widget is None:
            return
            
        vb = self.radargram_widget.plot.vb
        if not vb.sceneBoundingRect().contains(pos):
            return
            
        mouse_point = vb.mapSceneToView(pos)
        trace = mouse_point.x()
        time = mouse_point.y()
        
        apex_trace, apex_time = self.current_apex
        dx = abs(trace - apex_trace) * self.spin_spacing.value()
        
        t_sq_diff = time**2 - apex_time**2
        if t_sq_diff > 0:
            v = np.sqrt(4 * dx**2 / t_sq_diff)
            self._draw_temp_hyperbola(apex_trace, apex_time, v)

    def _draw_temp_hyperbola(self, apex_trace: float, apex_time: float, v: float) -> None:
        traces = np.linspace(apex_trace - 50, apex_trace + 50, 100)
        times = self._calc_hyperbola(traces, apex_trace, apex_time, v)
        self.temp_hyperbola_item.setData(traces, times)

    def _update_hyperbolas(self) -> None:
        if not self.hyperbolas:
            self.hyperbola_plot_item.setData([], [])
            return
            
        all_traces = []
        all_times = []
        for hyp in self.hyperbolas:
            traces = np.linspace(hyp["apex_trace"] - 50, hyp["apex_trace"] + 50, 100)
            times = self._calc_hyperbola(traces, hyp["apex_trace"], hyp["apex_time"], hyp["velocity"])
            all_traces.extend(traces.tolist() + [np.nan])
            all_times.extend(times.tolist() + [np.nan])
            
        self.hyperbola_plot_item.setData(all_traces, all_times)

    def _update_scatter(self) -> None:
        spots = []
        for hyp in self.hyperbolas:
            spots.append({'pos': (hyp["apex_trace"], hyp["apex_time"]), 'brush': 'r'})
        if self.current_apex:
            spots.append({'pos': self.current_apex, 'brush': 'y'})
        self.scatter_item.setData(spots)

    def _calc_hyperbola(self, traces: np.ndarray, apex_trace: float, apex_time: float, v: float) -> np.ndarray:
        dx = (traces - apex_trace) * self.spin_spacing.value()
        return np.sqrt(apex_time**2 + 4 * dx**2 / v**2)

    def clear_picks(self) -> None:
        self.hyperbolas.clear()
        self.current_apex = None
        self._update_hyperbolas()
        self._update_scatter()
        self.temp_hyperbola_item.setData([], [])
        self.semblance_image.clear()

    def export_json(self) -> None:
        if not self.hyperbolas:
            QMessageBox.warning(self, "Export", "No hyperbolas to export.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export Velocity Model", "", "JSON Files (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump({"velocities": self.hyperbolas}, f, indent=4)

    def _update_semblance(self) -> None:
        """Placeholder for semblance calculation visualization."""
        if not self.hyperbolas:
            return
            
        velocities = np.linspace(0.05, 0.2, 50)
        times = np.linspace(0, 200, 100)
        
        semblance = np.zeros((len(velocities), len(times)))
        
        for hyp in self.hyperbolas:
            v_idx = np.argmin(np.abs(velocities - hyp["velocity"]))
            t_idx = np.argmin(np.abs(times - hyp["apex_time"]))
            if 0 <= v_idx < len(velocities) and 0 <= t_idx < len(times):
                semblance[v_idx, t_idx] = 1.0
                
        try:
            from scipy.ndimage import gaussian_filter
            semblance = gaussian_filter(semblance, sigma=2)
        except ImportError:
            pass
            
        self.semblance_image.setImage(semblance)
        self.semblance_image.setRect(QtCore.QRectF(0.05, 0, 0.15, 200))
        self.semblance_plot.setRange(xRange=(0.05, 0.2), yRange=(200, 0))

