from pioneer_sdk2 import Pioneer
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QCheckBox, QLabel
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class RealtimePlot(QWidget):
    def __init__(self, data_source):
        super().__init__()

        self.data_source = data_source  # DroneController.get_realtime_data

        self.setWindowTitle("Realtime Drone Telemetry")

        layout = QVBoxLayout()

        # чекбоксы
        self.cb_xyz = QCheckBox("Position X/Y/Z")
        self.cb_accel = QCheckBox("Accel X/Y/Z")
        self.cb_battery = QCheckBox("Battery")

        self.cb_xyz.setChecked(True)
        self.cb_accel.setChecked(True)
        self.cb_battery.setChecked(True)

        layout.addWidget(self.cb_xyz)
        layout.addWidget(self.cb_accel)
        layout.addWidget(self.cb_battery)

        # matplotlib
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)

        self.setLayout(layout)

        # таймер обновления
        self.startTimer(100)  # 10 Hz

    def timerEvent(self, event):
        data = self.data_source()

        self.ax.clear()

        t = data["t"]

        # X/Y/Z
        if self.cb_xyz.isChecked():
            self.ax.plot(t, data["x"], label="X")
            self.ax.plot(t, data["y"], label="Y")
            self.ax.plot(t, data["z"], label="Z")

        # accel (если есть)
        if self.cb_accel.isChecked() and "ax" in data:
            self.ax.plot(t, data["ax"], label="AX", linestyle="--")
            self.ax.plot(t, data["ay"], label="AY", linestyle="--")
            self.ax.plot(t, data["az"], label="AZ", linestyle="--")

        # battery (одна линия)
        if self.cb_battery.isChecked() and "battery" in data:
            self.ax.plot(t, data["battery"], label="Battery", linewidth=2)

        self.ax.legend()
        self.ax.set_title("Realtime telemetry")
        self.ax.set_xlabel("Time (s)")
        self.canvas.draw()