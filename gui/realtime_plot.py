from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox, QHBoxLayout, QLabel, QPushButton
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


class RealtimePlot(QWidget):
    def __init__(self, data_source, drone_name="Drone"):
        super().__init__()
        self.data_source = data_source
        self.drone_name = drone_name
        self.setWindowTitle(f"Telemetry: {drone_name}")
        
        layout = QVBoxLayout()
        self.title_label = QLabel(f"📊 {drone_name}")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)
        checkbox_layout = QHBoxLayout()
        self.cb_xyz = QCheckBox("Position (X/Y/Z)")
        self.cb_accel = QCheckBox("Acceleration (X/Y/Z)")
        self.cb_battery = QCheckBox("Battery")
        self.cb_xyz.setChecked(True)
        self.cb_accel.setChecked(False)
        self.cb_battery.setChecked(True)
        
        checkbox_layout.addWidget(self.cb_xyz)
        checkbox_layout.addWidget(self.cb_accel)
        checkbox_layout.addWidget(self.cb_battery)
        layout.addLayout(checkbox_layout)
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.ax_position = self.figure.add_subplot(311)
        self.ax_accel = self.figure.add_subplot(312, sharex=self.ax_position)
        self.ax_battery = self.figure.add_subplot(313, sharex=self.ax_position)
        self.ax_accel.set_visible(False)
        self.ax_battery.set_visible(False)
        self._setup_axes()
        
        self.figure.tight_layout()

        self.setLayout(layout)
        self.startTimer(100)  # 10 Hz
    
    def _setup_axes(self):
        """Настройка внешнего вида осей"""
        for ax in [self.ax_position, self.ax_accel, self.ax_battery]:
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Time (s)")
        
        self.ax_position.set_ylabel("Position (m)")
        self.ax_position.set_title("Position")
        
        self.ax_accel.set_ylabel("Accel (m/s²)")
        self.ax_accel.set_title("Acceleration")
        
        self.ax_battery.set_ylabel("Battery (V)")
        self.ax_battery.set_title("Battery Status")
        
        self.figure.tight_layout()
    
    def timerEvent(self, event):
        try:
            data = self.data_source()
            if not data or not data.get("t"):
                return
            
            t = [x for x in data["t"] if x is not None]
            if not t:
                return

            self.ax_position.clear()
            self.ax_accel.clear()
            self.ax_battery.clear()
            self._setup_axes()
            if self.cb_xyz.isChecked():
                has_valid_data = False
                
                for key, label, color in [("x", "X", "blue"), ("y", "Y", "green"), ("z", "Z", "red")]:
                    if key in data and data[key]:
                        values = [v for v in data[key] if v is not None]
                        if len(values) == len(t):
                            self.ax_position.plot(t, values, label=label, color=color, linewidth=1.5)
                            has_valid_data = True
                
                if has_valid_data:
                    self.ax_position.legend(loc='upper right', fontsize=8)
                    self.ax_position.set_visible(True)
                else:
                    self.ax_position.set_visible(False)
            else:
                self.ax_position.set_visible(False)
            if self.cb_accel.isChecked():
                has_valid_data = False
                
                for key, label, color in [("ax", "AX", "orange"), ("ay", "AY", "purple"), ("az", "AZ", "brown")]:
                    if key in data and data[key]:
                        values = [v for v in data[key] if v is not None]
                        if len(values) == len(t):
                            self.ax_accel.plot(t, values, label=label, color=color, linewidth=1, linestyle='--')
                            has_valid_data = True
                
                if has_valid_data:
                    self.ax_accel.legend(loc='upper right', fontsize=8)
                    self.ax_accel.set_visible(True)
                else:
                    self.ax_accel.set_visible(False)
            else:
                self.ax_accel.set_visible(False)
            if self.cb_battery.isChecked() and "battery" in data and data["battery"]:
                values = [v for v in data["battery"] if v is not None]
                if len(values) == len(t):
                    self.ax_battery.plot(t, values, label="Battery", color="darkgreen", linewidth=2)
                    self.ax_battery.legend(loc='upper right', fontsize=8)
                    self.ax_battery.set_visible(True)
                    min_battery = min(values) if values else 0
                    if min_battery > 0:
                        self.ax_battery.axhline(y=10.5, color='red', linestyle=':', alpha=0.5, label='Min (10.5V)')
                        self.ax_battery.legend(loc='upper right', fontsize=8)
                else:
                    self.ax_battery.set_visible(False)
            else:
                self.ax_battery.set_visible(False)
            if any([self.ax_position.get_visible(), self.ax_accel.get_visible(), self.ax_battery.get_visible()]):
                self.canvas.draw_idle()  # draw_idle безопаснее для Qt, чем draw()
        except Exception as e:
            print(f"[RealtimePlot] Error updating plot: {e}")
        
        except Exception as e:
            print(f"[RealtimePlot] Error updating plot: {e}")
