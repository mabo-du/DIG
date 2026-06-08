"""Control panels for the radargram viewer."""

from __future__ import annotations

from typing import Callable

import numpy as np
from PySide6 import QtCore, QtWidgets

from dig.viz.colormaps import COLORMAPS


class ControlPanel(QtWidgets.QDockWidget):
    """Dockable control panel for radargram display settings."""

    colormapChanged = QtCore.Signal(str)
    gainChanged = QtCore.Signal(float)
    depthCalibrationChanged = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__("Controls", parent)
        self.setObjectName("ControlPanel")

        widget = QtWidgets.QWidget()
        self.setWidget(widget)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(8)

        # Colormap selector
        cmap_group = QtWidgets.QGroupBox("Colormap")
        cmap_layout = QtWidgets.QVBoxLayout(cmap_group)
        self.cmap_combo = QtWidgets.QComboBox()
        self.cmap_combo.addItems(sorted(COLORMAPS.keys()))
        self.cmap_combo.setCurrentText("seismic")
        self.cmap_combo.currentTextChanged.connect(self._on_colormap_changed)
        cmap_layout.addWidget(self.cmap_combo)
        layout.addWidget(cmap_group)

        # Gain controls
        gain_group = QtWidgets.QGroupBox("Gain")
        gain_layout = QtWidgets.QVBoxLayout(gain_group)
        self.gain_type = QtWidgets.QComboBox()
        self.gain_type.addItems(["None", "AGC", "SEC", "Linear"])
        self.gain_type.currentTextChanged.connect(self._on_gain_changed)
        gain_layout.addWidget(self.gain_type)
        gain_slider_layout = QtWidgets.QHBoxLayout()
        gain_slider_layout.addWidget(QtWidgets.QLabel("Amount:"))
        self.gain_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.gain_slider.setRange(0, 200)
        self.gain_slider.setValue(50)
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        gain_slider_layout.addWidget(self.gain_slider)
        self.gain_label = QtWidgets.QLabel("1.0x")
        gain_slider_layout.addWidget(self.gain_label)
        gain_layout.addLayout(gain_slider_layout)
        layout.addWidget(gain_group)

        # Depth calibration
        depth_group = QtWidgets.QGroupBox("Depth Calibration")
        depth_layout = QtWidgets.QVBoxLayout(depth_group)
        vel_layout = QtWidgets.QHBoxLayout()
        vel_layout.addWidget(QtWidgets.QLabel("Velocity (m/ns):"))
        self.velocity_spin = QtWidgets.QDoubleSpinBox()
        self.velocity_spin.setRange(0.01, 0.5)
        self.velocity_spin.setSingleStep(0.01)
        self.velocity_spin.setValue(0.1)
        self.velocity_spin.setDecimals(3)
        self.velocity_spin.valueChanged.connect(self._on_depth_calibration_changed)
        vel_layout.addWidget(self.velocity_spin)
        depth_layout.addLayout(vel_layout)
        self.depth_label = QtWidgets.QLabel("Depth scale: 1.0 m per 10 ns")
        depth_layout.addWidget(self.depth_label)
        layout.addWidget(depth_group)

        # Display info
        info_group = QtWidgets.QGroupBox("Data Info")
        info_layout = QtWidgets.QVBoxLayout(info_group)
        self.info_text = QtWidgets.QLabel("No data loaded")
        self.info_text.setWordWrap(True)
        info_layout.addWidget(self.info_text)
        layout.addWidget(info_group)

        layout.addStretch()

    def update_data_info(self, text: str) -> None:
        self.info_text.setText(text)

    def _on_colormap_changed(self, name: str) -> None:
        self.colormapChanged.emit(name)

    def _on_gain_changed(self) -> None:
        amount = self.gain_slider.value() / 50.0
        self.gain_label.setText(f"{amount:.1f}x")
        self.gainChanged.emit(amount)

    def _on_depth_calibration_changed(self, velocity: float) -> None:
        ns_per_m = (1.0 / velocity) / 2.0 if velocity > 0 else 0
        self.depth_label.setText(f"Depth scale: 1 m per {ns_per_m:.1f} ns")
        self.depthCalibrationChanged.emit(velocity)