"""main_window.py — The main application window for DIG.

exports: MainWindow
used_by: dig.__main__
rules:
  - Must tie together all 2D and 3D visualization widgets.
"""

from PySide6.QtWidgets import QMainWindow, QTabWidget, QDockWidget, QFileDialog, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from dig.viz.radargram_widget import RadargramWidget
from dig.viz.volume_widget import VolumeWidget
from dig.viz.slice_navigator import SliceNavigator
from dig.viz.controls import ControlPanel
from dig.viz.history_panel import HistoryPanel
from dig.viz.velocity_panel import VelocityPanel
from dig.parsers.dzt import DZTFile
from dig.parsers.dt1 import DT1File
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIG - Digital Imaging for Geophysics")
        self.resize(1200, 800)

        self._setup_menu()

        # Central Tab Widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Views
        self.radargram = RadargramWidget(self)
        self.slice_nav = SliceNavigator(self)
        self.volume_view = VolumeWidget(self)

        self.tabs.addTab(self.radargram, "2D Radargram")
        self.tabs.addTab(self.slice_nav, "2D Slices")
        self.tabs.addTab(self.volume_view, "3D Volume")

        # Dock Widgets
        self.controls = ControlPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.controls)

        self.history = HistoryPanel(self)
        hist_dock = QDockWidget("Audit Trail", self)
        hist_dock.setWidget(self.history)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, hist_dock)

        self.velocity = VelocityPanel(self.radargram, self)
        # VelocityPanel is a QWidget, so wrap it in a QDockWidget
        vel_dock = QDockWidget("Velocity Analysis", self)
        vel_dock.setWidget(self.velocity)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, vel_dock)

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Profile...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open GPR Profile",
            "",
            "GPR Files (*.dzt *.dt1);;GSSI (*.dzt);;Sensors & Software (*.dt1);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            if path.suffix.lower() == ".dzt":
                parsed = DZTFile(path)
                data = parsed.traces
            elif path.suffix.lower() == ".dt1":
                parsed = DT1File(path)
                data = parsed.traces
            else:
                QMessageBox.warning(self, "Unsupported File", f"Unsupported file extension: {path.suffix}")
                return
            
            # Switch to Radargram tab and set data
            self.tabs.setCurrentWidget(self.radargram)
            self.radargram.set_data(data)
            self.controls.update_data_info(f"Loaded: {path.name}\nTraces: {data.shape[0]}\nSamples: {data.shape[1]}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", f"Could not load {path.name}:\n\n{str(e)}")
