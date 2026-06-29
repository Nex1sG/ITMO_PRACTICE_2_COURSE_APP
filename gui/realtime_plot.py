from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class RealtimePlot(QWidget):
    def __init__(self, data_source, drone_name="Drone"):
        super().__init__()
        self.data_source = data_source
        self.drone_name = drone_name
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel(f"Телеметрия: {drone_name}")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; padding: 5px;")
        layout.addWidget(self.title_label)
        
        self.figure = Figure(figsize=(12, 9), dpi=100)
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
            line, = ax.plot([], [], label=label, color=color, linestyle=ls, linewidth=2 if ax == self.ax_position else 1.5)
            self.lines[key] = line
            
        self._setup_axes()
        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)
        self.timer.start(100)

    def _setup_axes(self):
        for ax in [self.ax_position, self.ax_accel, self.ax_battery]:
            ax.grid(True, alpha=0.3, linewidth=1)
            ax.set_xlabel("Время (с)", fontsize=11)
            ax.tick_params(labelsize=9)
            
        self.ax_position.set_ylabel("Позиция (м)", fontsize=11)
        self.ax_position.set_title("Пространственное положение", fontsize=13, fontweight='bold', pad=10)
        self.ax_position.legend(loc='upper right', fontsize=9)
        
        self.ax_accel.set_ylabel("Ускорение (м/с²)", fontsize=11)
        self.ax_accel.set_title("Линейное ускорение", fontsize=13, fontweight='bold', pad=10)
        self.ax_accel.legend(loc='upper right', fontsize=9)
        
        self.ax_battery.set_ylabel("Напряжение (В)", fontsize=11)
        self.ax_battery.set_title("Состояние аккумулятора", fontsize=13, fontweight='bold', pad=10)
        self.ax_battery.legend(loc='upper right', fontsize=9)

    def refresh_plot(self):
        try:
            data = self.data_source()
            
            if data and data.get('t'):
                valid_x = len([v for v in data.get('x', []) if v is not None])
                valid_y = len([v for v in data.get('y', []) if v is not None])
                valid_z = len([v for v in data.get('z', []) if v is not None])
                if len(data['t']) > 0 and len(data['t']) % 50 == 0:
                    print(f"[PLOT {self.drone_name}] t={len(data['t'])}, x_valid={valid_x}, y_valid={valid_y}, z_valid={valid_z}")

            if not data or not data.get("t"):
                return

            t_raw = data["t"]
            valid_indices = [i for i, x in enumerate(t_raw) if x is not None]
            if not valid_indices:
                return

            t = [t_raw[i] for i in valid_indices]
            if len(t) < 2:
                return
                
            min_t, max_t = t[0], t[-1]
            time_range = max_t - min_t
            if time_range < 1:
                max_t = min_t + 1

            for key in ["x", "y", "z"]:
                raw_vals = data.get(key, [])
                vals = [raw_vals[i] for i in valid_indices if i < len(raw_vals) and raw_vals[i] is not None]
                if len(vals) == len(t):
                    self.lines[key].set_data(t, vals)
                    self.lines[key].set_visible(True)
                else:
                    self.lines[key].set_visible(False)

            for key in ["ax", "ay", "az"]:
                raw_vals = data.get(key, [])
                vals = [raw_vals[i] for i in valid_indices if i < len(raw_vals) and raw_vals[i] is not None]
                if len(vals) == len(t):
                    self.lines[key].set_data(t, vals)
                    self.lines[key].set_visible(True)
                else:
                    self.lines[key].set_visible(False)

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

            for ax in [self.ax_position, self.ax_accel, self.ax_battery]:
                ax.set_xlim(min_t - 0.5, max_t + 0.5)

            self.canvas.draw_idle()
        except Exception as e:
            print(f"[График] Ошибка обновления: {e}")