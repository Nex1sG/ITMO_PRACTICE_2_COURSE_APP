import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel
from PySide6.QtCore import QTimer, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class RealtimePlot(QWidget):
    def __init__(self, data_source, drone_name="Drone"):
        super().__init__()
        self.data_source = data_source
        self.drone_name = drone_name
        self.setWindowTitle(f"Телеметрия: {drone_name}")
        
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(f"Телеметрия: {drone_name}")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        checkbox_layout = QHBoxLayout()
        self.cb_xyz = QCheckBox("Позиция (X/Y/Z)")
        self.cb_accel = QCheckBox("Ускорение (X/Y/Z)")
        self.cb_battery = QCheckBox("Аккумулятор")
        
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
        
        self.lines = {}
        for key, label, color, ax, ls in [
            ("x", "X", "blue", self.ax_position, "-"),
            ("y", "Y", "green", self.ax_position, "-"),
            ("z", "Z", "red", self.ax_position, "-"),
            ("ax", "AX", "orange", self.ax_accel, "--"),
            ("ay", "AY", "purple", self.ax_accel, "--"),
            ("az", "AZ", "brown", self.ax_accel, "--"),
            ("battery", "Напряжение", "darkgreen", self.ax_battery, "-")
        ]:
            line, = ax.plot([], [], label=label, color=color, linestyle=ls, linewidth=1.5 if ax == self.ax_position else 1)
            self.lines[key] = line
            
        self._setup_axes()
        self.figure.tight_layout()
        self.canvas.draw()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)
        self.timer.start(100)

    def _setup_axes(self):
        for ax in [self.ax_position, self.ax_accel, self.ax_battery]:
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Время (с)")
            
        self.ax_position.set_ylabel("Позиция (м)")
        self.ax_position.set_title("Пространственное положение")
        self.ax_accel.set_ylabel("Ускорение (м/с²)")
        self.ax_accel.set_title("Линейное ускорение")
        self.ax_battery.set_ylabel("Напряжение (В)")
        self.ax_battery.set_title("Состояние аккумулятора")

    def refresh_plot(self):
        try:
            data = self.data_source()
            if not data or not data.get("t"):
                return

            t_raw = data["t"]
            valid_indices = [i for i, x in enumerate(t_raw) if x is not None]
            if not valid_indices:
                return

            t = [t_raw[i] for i in valid_indices]
            min_t, max_t = t[0], t[-1]

            if self.cb_xyz.isChecked():
                for key in ["x", "y", "z"]:
                    raw_vals = data.get(key, [])
                    vals = [raw_vals[i] for i in valid_indices if i < len(raw_vals) and raw_vals[i] is not None]
                    if len(vals) == len(t):
                        self.lines[key].set_data(t, vals)
                        self.lines[key].set_visible(True)
                    else:
                        self.lines[key].set_visible(False)
            else:
                for key in ["x", "y", "z"]:
                    self.lines[key].set_visible(False)

            if self.cb_accel.isChecked():
                for key in ["ax", "ay", "az"]:
                    raw_vals = data.get(key, [])
                    vals = [raw_vals[i] for i in valid_indices if i < len(raw_vals) and raw_vals[i] is not None]
                    if len(vals) == len(t):
                        self.lines[key].set_data(t, vals)
                        self.lines[key].set_visible(True)
                    else:
                        self.lines[key].set_visible(False)
            else:
                for key in ["ax", "ay", "az"]:
                    self.lines[key].set_visible(False)

            if self.cb_battery.isChecked():
                raw_vals = data.get("battery", [])
                vals = [raw_vals[i] for i in valid_indices if i < len(raw_vals) and raw_vals[i] is not None]
                if len(vals) == len(t):
                    self.lines["battery"].set_data(t, vals)
                    self.lines["battery"].set_visible(True)
                    if hasattr(self.ax_battery, "_min_line"):
                        self.ax_battery._min_line.set_data([min_t, max_t], [10.5, 10.5])
                    else:
                        self.ax_battery._min_line, = self.ax_battery.plot([min_t, max_t], [10.5, 10.5], color='red', linestyle=':', alpha=0.5, label='Мин. 10.5В')
                else:
                    self.lines["battery"].set_visible(False)
            else:
                self.lines["battery"].set_visible(False)
                if hasattr(self.ax_battery, "_min_line"):
                    self.ax_battery._min_line.set_visible(False)

            for ax in [self.ax_position, self.ax_accel, self.ax_battery]:
                ax.set_xlim(min_t - 0.5, max_t + 0.5)

            self.ax_position.legend(loc='upper right', fontsize=8)
            self.ax_accel.legend(loc='upper right', fontsize=8)
            self.ax_battery.legend(loc='upper right', fontsize=8)

            self.canvas.draw_idle()
        except Exception as e:
            print(f"[График] Ошибка обновления: {e}")