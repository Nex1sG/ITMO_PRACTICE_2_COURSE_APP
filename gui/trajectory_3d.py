from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import QTimer, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

class Trajectory3D(QWidget):
    def __init__(self, fleet):
        super().__init__()
        self.fleet = fleet
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        title = QLabel("3D Траектории дронов")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.figure = Figure(figsize=(14, 10), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111, projection='3d')
        
        self.lines = {}
        self.colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
        
        self._setup_axes()
        self.figure.tight_layout()
        self.canvas.draw()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_trajectory)
        self.timer.start(200)

    def _setup_axes(self):
        self.ax.set_xlabel('X (м)', fontsize=12, labelpad=10)
        self.ax.set_ylabel('Y (м)', fontsize=12, labelpad=10)
        self.ax.set_zlabel('Z (м)', fontsize=12, labelpad=10)
        self.ax.set_title('Траектории полёта дронов', fontsize=14, fontweight='bold', pad=20)
        self.ax.grid(True, alpha=0.3)

    def update_trajectory(self):
        try:
            if not self.fleet or not self.fleet.drones:
                return
            
            has_data = False
            for i, drone in enumerate(self.fleet.drones):
                if drone.drone is None:
                    continue
                
                data = drone.get_realtime_data()
                if not data or not data.get('t'):
                    continue
                
                t = data['t']
                x = data['x']
                y = data['y']
                z = data['z']
                
                valid_indices = [j for j in range(len(t)) 
                                if t[j] is not None and x[j] is not None 
                                and y[j] is not None and z[j] is not None]
                
                if not valid_indices:
                    continue
                
                has_data = True
                x_vals = [x[j] for j in valid_indices]
                y_vals = [y[j] for j in valid_indices]
                z_vals = [z[j] for j in valid_indices]
                
                color = self.colors[i % len(self.colors)]
                drone_name = f"Дрон {i+1}"
                
                if drone_name in self.lines:
                    self.lines[drone_name].set_data(x_vals, y_vals)
                    self.lines[drone_name].set_3d_properties(z_vals)
                else:
                    line, = self.ax.plot(x_vals, y_vals, z_vals, 
                                        label=drone_name, 
                                        color=color, 
                                        linewidth=2,
                                        alpha=0.8)
                    self.lines[drone_name] = line
            
            if has_data:
                all_x = []
                all_y = []
                all_z = []
                for drone in self.fleet.drones:
                    if drone.drone is None:
                        continue
                    data = drone.get_realtime_data()
                    if not data:
                        continue
                    t = data.get('t', [])
                    x = data.get('x', [])
                    y = data.get('y', [])
                    z = data.get('z', [])
                    valid = [j for j in range(len(t)) 
                            if t[j] is not None and x[j] is not None 
                            and y[j] is not None and z[j] is not None]
                    all_x.extend([x[j] for j in valid])
                    all_y.extend([y[j] for j in valid])
                    all_z.extend([z[j] for j in valid])
                
                if all_x:
                    x_min, x_max = min(all_x), max(all_x)
                    y_min, y_max = min(all_y), max(all_y)
                    z_min, z_max = min(all_z), max(all_z)
                    
                    x_range = max(x_max - x_min, 1.0)
                    y_range = max(y_max - y_min, 1.0)
                    z_range = max(z_max - z_min, 1.0)
                    
                    x_center = (x_min + x_max) / 2
                    y_center = (y_min + y_max) / 2
                    z_center = (z_min + z_max) / 2
                    
                    max_range = max(x_range, y_range, z_range) / 2
                    
                    self.ax.set_xlim(x_center - max_range, x_center + max_range)
                    self.ax.set_ylim(y_center - max_range, y_center + max_range)
                    self.ax.set_zlim(z_center - max_range, z_center + max_range)
            
            if self.lines:
                self.ax.legend(loc='upper left', fontsize=10)
            
            self.canvas.draw_idle()
        except Exception as e:
            print(f"[3D Траектория] Ошибка обновления: {e}")