import sys
import time
import threading
import ipaddress
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QTabWidget,
    QInputDialog, QMessageBox, QComboBox, QStyledItemDelegate, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from config.config import load_drones, save_drones
from backend.fleet_manager import FleetManager
from gui.realtime_plot import RealtimePlot

class PatternDelegate(QStyledItemDelegate):
    PATTERNS = ["hover", "line", "backforth", "square", "rectangle",
                "triangle", "circle", "ellipse", "figure8"]

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self.PATTERNS)
        return combo

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole)
        editor.setCurrentText(value if value in self.PATTERNS else "hover")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

class NoFlyDelegate(QStyledItemDelegate):
    VALUES = ["True", "False"]

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self.VALUES)
        return combo

    def setEditorData(self, editor, index):
        value = str(index.model().data(index, Qt.DisplayRole))
        editor.setCurrentText(value if value in self.VALUES else "False")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система контроля дронов")
        self.resize(1600, 1000)
        self.setStyleSheet(self.get_global_style())
        
        self.fleet = None
        self.fleet_thread = None
        self.is_running = False
        self.is_flying = False
        self.plot_check_timer = None
        self.all_plots_timer = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { font-size: 14px; padding: 10px 20px; }")
        main_layout.addWidget(self.tabs)

        self.tab_settings = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.tab_settings, "1. Настройка дронов")

        self.tab_control = QWidget()
        self.setup_control_tab()
        self.tabs.addTab(self.tab_control, "2. Полёт и Графики")
        
        self.tab_all_plots = QWidget()
        self.setup_all_plots_tab()
        self.tabs.addTab(self.tab_all_plots, "3. Все графики")

        self.refresh_table()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status_label)
        self.status_timer.start(500)

    def get_global_style(self):
        return """
            QWidget { background-color: #2e3436; color: #ffffff; font-size: 12px; }
            QTableWidget { background-color: #33383a; gridline-color: #555753; border: 1px solid #555753; font-size: 13px; }
            QPushButton { background-color: #4a90e2; border-radius: 5px; padding: 10px 20px; font-size: 14px; font-weight: bold; color: white; }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2a5d96; }
            QPushButton:disabled { background-color: #555753; color: #888888; }
        """

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "IP", "Port", "Alt (m)", "Pattern", "Size (m)", "Reps", "Duration (s)", "Interval (s)", "No Fly"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        
        self.table.setItemDelegateForColumn(4, PatternDelegate())
        self.table.setItemDelegateForColumn(9, NoFlyDelegate())
        
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_add = QPushButton("Добавить дрона")
        self.btn_add.clicked.connect(self.add_drone_dialog)
        
        self.btn_save = QPushButton("Сохранить в JSON")
        self.btn_save.clicked.connect(self.save_to_json)
        
        self.btn_delete = QPushButton("Удалить выбранного")
        self.btn_delete.clicked.connect(self.delete_drone)
        
        self.btn_refresh = QPushButton("Обновить таблицу")
        self.btn_refresh.clicked.connect(self.refresh_table)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(btn_layout)

    def setup_control_tab(self):
        layout = QVBoxLayout(self.tab_control)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        control_panel = QHBoxLayout()
        control_panel.setSpacing(15)

        self.btn_start = QPushButton("ЗАПУСТИТЬ ФЛОТ")
        self.btn_start.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-size: 18px; padding: 15px 30px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #555753; color: #888888; }
        """)
        self.btn_start.clicked.connect(self.start_fleet)

        self.btn_stop = QPushButton("ОСТАНОВИТЬ")
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #f44336; color: white; font-size: 18px; padding: 15px 30px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #da190b; }
            QPushButton:disabled { background-color: #555753; color: #888888; }
        """)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_fleet)

        self.status_label = QLabel("Статус: Готов к запуску")
        self.status_label.setStyleSheet("font-size: 18px; margin-left: 20px; font-weight: bold; color: #ffffff;")

        control_panel.addWidget(self.btn_start)
        control_panel.addWidget(self.btn_stop)
        control_panel.addWidget(self.status_label)
        
        layout.addLayout(control_panel)

        line = QWidget()
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: #555753;")
        layout.addWidget(line)

        self.plot_container = QWidget()
        self.plot_container.setStyleSheet("background-color: #383c3e; border-radius: 5px;")
        self.plot_layout = QVBoxLayout(self.plot_container)
        
        layout.addWidget(self.plot_container)

    def setup_all_plots_tab(self):
        layout = QVBoxLayout(self.tab_all_plots)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.all_plots_scroll = QScrollArea()
        self.all_plots_scroll.setWidgetResizable(True)
        self.all_plots_scroll.setStyleSheet("background-color: #383c3e; border-radius: 5px;")
        
        self.all_plots_content = QWidget()
        self.all_plots_layout = QVBoxLayout(self.all_plots_content)
        self.all_plots_layout.setSpacing(20)
        
        self.all_plots_scroll.setWidget(self.all_plots_content)
        layout.addWidget(self.all_plots_scroll)
        
        self.info_label = QLabel("Запустите флот для отображения графиков всех дронов")
        self.info_label.setStyleSheet("font-size: 16px; color: #888888; padding: 20px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.all_plots_layout.addWidget(self.info_label)

    def update_status_label(self):
        if self.fleet and hasattr(self.fleet, 'status'):
            self.status_label.setText(f"Статус: {self.fleet.status}")
        elif self.is_running:
            self.status_label.setText("Статус: Инициализация...")

    def refresh_table(self):
        drones = load_drones()
        self.table.setRowCount(0)
        
        for drone in drones:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(drone.get("id", "")))
            self.table.setItem(row, 1, QTableWidgetItem(drone.get("ip", "")))
            self.table.setItem(row, 2, QTableWidgetItem(str(drone.get("port", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(drone.get("alt", 1.0))))
            self.table.setItem(row, 4, QTableWidgetItem(drone.get("pattern", "hover")))
            self.table.setItem(row, 5, QTableWidgetItem(str(drone.get("size", 1.0))))
            self.table.setItem(row, 6, QTableWidgetItem(str(drone.get("reps", 1))))
            self.table.setItem(row, 7, QTableWidgetItem(str(drone.get("duration", 60.0))))
            self.table.setItem(row, 8, QTableWidgetItem(str(drone.get("interval", 0.05))))
            
            no_fly_str = "True" if drone.get("no_fly", False) else "False"
            self.table.setItem(row, 9, QTableWidgetItem(no_fly_str))

    def add_drone_dialog(self):
        ip, ok1 = QInputDialog.getText(self, "Новый дрон", "Введите IP адрес:", text="192.168.1.10")
        if not ok1 or not ip: return
        
        port, ok2 = QInputDialog.getInt(self, "Новый дрон", "Введите порт:", value=20556, minValue=1000, maxValue=65535)
        if not ok2: return
        
        drones = load_drones()
        new_id = f"drone_{len(drones) + 1}"
        
        new_drone = {
            "id": new_id, "ip": ip, "port": port, "alt": 1.0, "pattern": "hover",
            "size": 1.0, "reps": 1, "duration": 60.0, "interval": 0.05, "no_fly": True
        }
        
        drones.append(new_drone)
        save_drones(drones)
        
        QMessageBox.information(self, "Успех", f"Дрон {new_id} добавлен.")
        self.refresh_table()

    def save_to_json(self):
        VALID_PATTERNS = ["hover", "line", "backforth", "square", "rectangle",
                          "triangle", "circle", "ellipse", "figure8"]
        drones = []
        
        for row in range(self.table.rowCount()):
            try:
                drone_id = self.table.item(row, 0).text().strip()
                if not drone_id:
                    drone_id = f"drone_{row+1}"
                    
                ip = self.table.item(row, 1).text().strip()
                try:
                    ipaddress.ip_address(ip)
                except ValueError:
                    ip = "192.168.1.1"
                    
                try:
                    port = int(self.table.item(row, 2).text())
                    if not (1000 <= port <= 65535):
                        port = 20556
                except ValueError:
                    port = 20556
                    
                try:
                    alt = float(self.table.item(row, 3).text())
                    if not (0.1 <= alt <= 10.0):
                        alt = 1.0
                except ValueError:
                    alt = 1.0
                    
                pattern = self.table.item(row, 4).text().strip().lower()
                if pattern not in VALID_PATTERNS:
                    pattern = "hover"
                    
                try:
                    size = float(self.table.item(row, 5).text())
                    if not (0.1 <= size <= 5.0):
                        size = 1.0
                except ValueError:
                    size = 1.0
                    
                try:
                    reps = int(self.table.item(row, 6).text())
                    if not (1 <= reps <= 100):
                        reps = 1
                except ValueError:
                    reps = 1
                    
                try:
                    duration = float(self.table.item(row, 7).text())
                    if not (10 <= duration <= 300):
                        duration = 60.0
                except ValueError:
                    duration = 60.0
                    
                try:
                    interval = float(self.table.item(row, 8).text())
                    if not (0.01 <= interval <= 1.0):
                        interval = 0.05
                except ValueError:
                    interval = 0.05
                    
                no_fly_text = self.table.item(row, 9).text().strip().lower()
                no_fly = no_fly_text in ["true", "yes", "1", "да"]
                
                drone = {
                    "id": drone_id, "ip": ip, "port": port, "alt": alt,
                    "pattern": pattern, "size": size, "reps": reps,
                    "duration": duration, "interval": interval, "no_fly": no_fly
                }
                drones.append(drone)
            except Exception:
                pass

        save_drones(drones)
        print(f"Сохранено {len(drones)} дронов в config.json")
        
        original_status = self.status_label.text()
        self.status_label.setText("Сохранено!")
        QTimer.singleShot(1000, lambda: self.status_label.setText(original_status))

    def delete_drone(self):
        row = self.table.currentRow()
        if row < 0: return
        
        drone_id = self.table.item(row, 0).text()
        if QMessageBox.question(self, "Подтверждение", f"Удалить {drone_id}?") == QMessageBox.Yes:
            drones = load_drones()
            drones = [d for d in drones if d.get("id") != drone_id]
            save_drones(drones)
            self.refresh_table()

    def start_fleet(self):
        if self.is_running: return
        
        self.save_to_json()
        drones_data = load_drones()
        if not drones_data:
            QMessageBox.critical(self, "Ошибка", "Список дронов пуст!")
            return

        tcp_list = [f"{d['ip']}:{d['port']}" for d in drones_data]
        primary = drones_data[0]
        
        try:
            self.fleet = FleetManager(
                tcp_list=tcp_list, alt=primary["alt"], size=primary.get("size", 1.0),
                reps=primary.get("reps", 1), interval=primary.get("interval", 0.05),
                pattern=primary["pattern"], duration=primary.get("duration", 60.0),
                no_fly=primary.get("no_fly", False)
            )
            
            self.is_running = True
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_label.setText("Статус: Подключение...")
            self.tabs.setCurrentIndex(1)

            self.fleet_thread = threading.Thread(target=self.fleet.run, daemon=True)
            self.fleet_thread.start()

            self.plot_check_timer = QTimer(self)
            self.plot_check_timer.timeout.connect(self.check_and_create_plots)
            self.plot_check_timer.start(200)
            
            self.all_plots_timer = QTimer(self)
            self.all_plots_timer.timeout.connect(self.check_and_update_all_plots)
            self.all_plots_timer.start(500)

            threading.Thread(target=self.monitor_thread_completion, daemon=True).start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка запуска", str(e))
            self.is_running = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def check_and_create_plots(self):
        if not self.is_running:
            if self.plot_check_timer:
                self.plot_check_timer.stop()
            return

        if self.fleet and self.fleet.drones:
            if any(d.drone is not None for d in self.fleet.drones):
                if self.plot_check_timer:
                    self.plot_check_timer.stop()
                self.create_all_plots()
                self.is_flying = True

    def create_all_plots(self):
        while self.plot_layout.count():
            child = self.plot_layout.takeAt(0)
            if child.widget(): 
                child.widget().deleteLater()

        self.drone_plots = QTabWidget()
        self.drone_plots.setStyleSheet("QTabBar::tab { font-size: 14px; padding: 10px 20px; }")

        for i, drone in enumerate(self.fleet.drones):
            plot_widget = RealtimePlot(drone.get_realtime_data, drone_name=f"Дрон {i+1}")
            self.drone_plots.addTab(plot_widget, f"Дрон {i+1}")

        self.plot_layout.addWidget(self.drone_plots)
        self.plot_container.update()
        
        self.status_label.setText("Статус: ПОЛЁТ / ЛОГИРОВАНИЕ")
        QMessageBox.information(self, "Запуск", "Дроны подключены. Графики обновляются.")

    def check_and_update_all_plots(self):
        if not self.is_running or not self.is_flying:
            return
            
        if self.fleet and self.fleet.drones:
            self.update_all_plots_tab()

    def update_all_plots_tab(self):
        while self.all_plots_layout.count():
            child = self.all_plots_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        for i, drone in enumerate(self.fleet.drones):
            if drone.drone is not None:
                plot_widget = RealtimePlot(drone.get_realtime_data, drone_name=f"Дрон {i+1}")
                self.all_plots_layout.addWidget(plot_widget)

    def stop_fleet(self):
        self.is_running = False
        self.is_flying = False
        self.status_label.setText("Статус: Остановка...")
        
        if self.plot_check_timer:
            self.plot_check_timer.stop()
            
        if self.all_plots_timer:
            self.all_plots_timer.stop()

        if self.fleet:
            self.fleet.stop_all()

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Статус: Остановлено")
        
        QMessageBox.information(self, "Готово", "Процесс остановлен. Дроны пытаются приземлиться.")

    def monitor_thread_completion(self):
        while self.is_running:
            if self.fleet_thread and not self.fleet_thread.is_alive():
                self.is_running = False
                self.is_flying = False
                QTimer.singleShot(0, self.reset_ui_after_finish)
                break
            time.sleep(0.5)

    def reset_ui_after_finish(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Статус: Миссия завершена")
        QMessageBox.information(self, "Готово", "Все дроны завершили работу.")