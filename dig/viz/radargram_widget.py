"""radargram_widget.py — Interactive radargram viewer with background processing.

exports: RadargramWidget
used_by: dig/viz/__init__.py
rules:
  - Do not block the main thread; processing must use QThread.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from dig.viz.colormaps import COLORMAPS


class ImageProcessor(QtCore.QThread):
    """Background worker for radargram image processing."""

    # Emits: rgba, vmin, vmax, n_traces, n_samples
    resultReady = QtCore.Signal(object, float, float, int, int)

    def __init__(
        self,
        data: np.ndarray,
        gain_callback: Callable | None,
        colormap_name: str,
        parent: QtCore.QObject | None = None,
    ):
        super().__init__(parent)
        self.data = data
        self.gain_callback = gain_callback
        self.colormap_name = colormap_name
        self.is_cancelled = False

    def run(self) -> None:
        display_data = self.data
        if self.gain_callback is not None:
            display_data = self.gain_callback(display_data)

        if self.is_cancelled:
            return

        lut = COLORMAPS.get(self.colormap_name)
        if lut is None:
            return

        vmin = float(np.percentile(display_data, 2))
        vmax = float(np.percentile(display_data, 98))

        if self.is_cancelled:
            return

        normalized = np.clip((display_data - vmin) / (vmax - vmin + 1e-12), 0, 1)
        indices = (normalized * (len(lut) - 1)).astype(np.uint16)
        rgba = lut[indices]

        if self.is_cancelled:
            return

        n_traces, n_samples = self.data.shape
        self.resultReady.emit(rgba, vmin, vmax, n_traces, n_samples)


class RadargramWidget(pg.GraphicsLayoutWidget):
    """Interactive radargram (2D GPR profile) viewer.

    Displays traces vs. time/depth as a color-mapped image with
    mouse-driven pan, zoom, and trace inspection.
    """

    traceSelected = QtCore.Signal(int, object)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self.plot = self.addPlot(title="Radargram")
        self.plot.setLabel("bottom", "Trace")
        self.plot.setLabel("left", "Time", units="ns")
        self.plot.showGrid(x=False, y=True, alpha=0.3)

        self.image = pg.ImageItem()
        self.plot.addItem(self.image)

        self.colorbar = pg.ColorBarItem(
            values=(0, 1),
            colorMap=pg.colormap.get("viridis"),
            width=20,
        )
        self.colorbar.setImageItem(self.image, insert_in=self.plot)

        self.v_line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen("w", width=1))
        self.h_line = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen("w", width=1))
        self.plot.addItem(self.v_line, ignoreBounds=True)
        self.plot.addItem(self.h_line, ignoreBounds=True)

        self.info_label = pg.TextItem(text="", anchor=(0, 1), color=(255, 255, 255))
        self.info_label.setPos(10, 10)
        self.plot.addItem(self.info_label)

        self.v_line.sigPositionChanged.connect(self._on_crosshair_moved)
        self.h_line.sigPositionChanged.connect(self._on_crosshair_moved)

        self._data: np.ndarray | None = None
        self._sample_interval_ns: float = 1.0
        self._time_zero_ns: float = 0.0
        self._colormap_name: str = "seismic"
        self._gain_callback: Callable | None = None
        self._worker: ImageProcessor | None = None

        self.plot.setMouseEnabled(x=True, y=True)

    def set_data(
        self,
        data: np.ndarray,
        sample_interval_ns: float = 1.0,
        time_zero_ns: float = 0.0,
        trace_positions: np.ndarray | None = None,
    ) -> None:
        self._data = np.asarray(data, dtype=np.float64)
        self._sample_interval_ns = sample_interval_ns
        self._time_zero_ns = time_zero_ns
        self._trace_positions = trace_positions
        self._update_image()
        n_traces, n_samples = self._data.shape
        y_max = n_samples * sample_interval_ns
        self.plot.setRange(xRange=(0, n_traces), yRange=(y_max, 0))
        self._update_info()

    def set_colormap(self, name: str) -> None:
        if name not in COLORMAPS:
            raise ValueError(f"Unknown colormap '{name}'. Available: {list(COLORMAPS.keys())}")
        self._colormap_name = name
        self._update_image()

    def set_gain_callback(self, callback: Callable[[np.ndarray], np.ndarray] | None) -> None:
        self._gain_callback = callback
        self._update_image()

    def get_trace_at(self, x: float) -> np.ndarray | None:
        if self._data is None:
            return None
        idx = max(0, min(int(round(x)), self._data.shape[0] - 1))
        return self._data[idx]

    @property
    def data(self) -> np.ndarray | None:
        return self._data

    @property
    def colormap_name(self) -> str:
        return self._colormap_name

    def _update_image(self) -> None:
        if self._data is None:
            return

        if self._worker is not None:
            self._worker.is_cancelled = True
            try:
                self._worker.resultReady.disconnect()
            except RuntimeError:
                pass
            self._worker = None

        self._worker = ImageProcessor(
            self._data, self._gain_callback, self._colormap_name, parent=self
        )
        self._worker.resultReady.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(
        self, rgba: np.ndarray, vmin: float, vmax: float, n_traces: int, n_samples: int
    ) -> None:
        self.image.setImage(rgba, autoLevels=False)
        self.colorbar.setLevels((vmin, vmax))
        self.image.setRect(QtCore.QRectF(0, 0, n_traces, n_samples * self._sample_interval_ns))
        self._worker = None

    def _on_crosshair_moved(self) -> None:
        if self._data is None:
            return
        x = self.v_line.value()
        y = self.h_line.value()
        trace_idx = max(0, min(int(round(x)), self._data.shape[0] - 1))
        sample_idx = max(0, min(int(round(y / self._sample_interval_ns)), self._data.shape[1] - 1))
        value = self._data[trace_idx, sample_idx]
        time_ns = sample_idx * self._sample_interval_ns + self._time_zero_ns
        self.info_label.setText(
            f"Trace: {trace_idx}  |  Time: {time_ns:.1f} ns  |  Amp: {value:.2f}"
        )
        self.traceSelected.emit(trace_idx, self._data[trace_idx])

    def _update_info(self) -> None:
        if self._data is None:
            return
        n_traces, n_samples = self._data.shape
        self.info_label.setText(
            f"Traces: {n_traces}  |  Samples: {n_samples}  |  Colormap: {self._colormap_name}"
        )

    def reset_view(self) -> None:
        if self._data is not None:
            n_traces, n_samples = self._data.shape
            y_max = n_samples * self._sample_interval_ns
            self.plot.setRange(xRange=(0, n_traces), yRange=(y_max, 0))
