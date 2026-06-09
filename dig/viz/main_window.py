"""main_window.py — The main application window for DIG.

exports: MainWindow
used_by: dig.__main__
rules:
  - Must tie together all 2D and 3D visualization widgets.
"""

from PySide6.QtWidgets import QMainWindow, QTabWidget, QDockWidget, Qt
from dig.viz.radargram_widget import RadargramWidget
from dig.viz.volume_widget import VolumeWidget
from dig.viz.slice_navigator import SliceNavigator
from dig.viz.controls import ControlPanel
from dig.viz.history_panel import HistoryPanel
from dig.viz.velocity_panel import VelocityPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIG - Digital Imaging for Geophysics")
        self.resize(1200, 800)

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
