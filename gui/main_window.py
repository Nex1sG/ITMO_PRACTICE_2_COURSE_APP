# gui/main_window.py
import sys
import time
import threading
import ipaddress
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QTabWidget,
    QInputDialog, QMessageBox, QComboBox, QStyledItemDelegate
)
from PySide6.QtCore import Qt, QTimer
from config.config import load_drones, save_drones
from backend.fleet_manager import FleetManager
from gui.realtime_plot import RealtimePlot

# ==================== ВАЛИДАТОРЫ ДЛЯ ТАБЛИЦЫ ====================
class PatternDelegate(QStyledItemDelegate):
    """Выпадающий список для Pattern"""
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
    """Выпадающий список для No Fly (True/False)"""
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
        self.setWindowTitle("Система контроля дронов и визуализации телеметрии")
        self.resize(1500, 900)  # Чуть увеличил окно по умолчанию

        # Применяем стиль ко всему приложению
        self.setStyleSheet(self.get_global_style())

        # Состояние системы
        self.fleet = None
        self.fleet_thread = None
        self.is_running = False

        # Основной виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Табы
        self.tabs = QTabWidget()
        # Увеличиваем шрифт вкладок
        self.tabs.setStyleSheet("QTabBar::tab { font-size: 14px; padding: 10px 20px; }")
        main_layout.addWidget(self.tabs)

        # === ВКЛАДКА 1: НАСТРОЙКИ ДРОНОВ ===
        self.tab_settings = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.tab_settings, "1. Настройка дронов")

        # === ВКЛАДКА 2: УПРАВЛЕНИЕ И ГРАФИКИ ===
        self.tab_control = QWidget()
        self.setup_control_tab()
        self.tabs.addTab(self.tab_control, "2. Полёт и Графики")

        # Загружаем данные при старте
        self.refresh_table()

    def get_global_style(self):
        """CSS-подобные стили для PyQt"""
        return """
            QWidget {
                background-color: #2e3436;
                color: #ffffff;
                font-size: 12px;
            }
            QTableWidget {
                background-color: #33383a;
                gridline-color: #555753;
                border: 1px solid #555753;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #202324;
                padding: 5px;
                border: 1px solid #555753;
                font-weight: bold;
            }
            QPushButton {
                background-color: #4a90e2;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a5d96;
            }
            QPushButton:disabled {
                background-color: #555753;
                color: #888888;
            }
        """

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "IP", "Port", "Alt (m)", "Pattern", 
            "Size (m)", "Reps", "Duration (s)", "Interval (s)", "No Fly"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        
        # Увеличиваем высоту строк таблицы для удобства
        self.table.verticalHeader().setDefaultSectionSize(40)
        
        # Делегаты
        self.table.setItemDelegateForColumn(4, PatternDelegate())
        self.table.setItemDelegateForColumn(9, NoFlyDelegate())
        
        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15) # Отступы между кнопками
        
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

        # Панель управления (сверху)
        control_panel = QHBoxLayout()
        control_panel.setSpacing(15)
        
        # Кнопка запуска - зеленая
        self.btn_start = QPushButton("ЗАПУСТИТЬ ФЛОТ")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 18px;
                padding: 15px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #555753; color: #888888; }
        """)
        self.btn_start.clicked.connect(self.start_fleet)
        
        # Кнопка остановки - красная
        self.btn_stop = QPushButton("ОСТАНОВИТЬ")
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 18px;
                padding: 15px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
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

        # Разделительная линия
        line = QWidget()
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: #555753;")
        layout.addWidget(line)

        # Область графиков
        self.plot_container = QWidget()
        self.plot_container.setStyleSheet("background-color: #383c3e; border-radius: 5px;")
        self.plot_layout = QVBoxLayout(self.plot_container)
        layout.addWidget(self.plot_container)

    # ==================== ЛОГИКА ТАБЛИЦЫ ====================
    # ... (код методов refresh_table, add_drone_dialog, save_to_json, delete_drone остается без изменений) ...
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
        print(f"Таблица обновлена: {len(drones)} дронов")

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
        QMessageBox.information(self, "Успех", f"Дрон {new_id} добавлен. Настройте параметры в таблице.")
        self.refresh_table()

    def save_to_json(self):
        VALID_PATTERNS = ["hover", "line", "backforth", "square", "rectangle", 
                          "triangle", "circle", "ellipse", "figure8"]
        drones = []
        errors = []
        warnings = []
        for row in range(self.table.rowCount()):
            try:
                drone_id = self.table.item(row, 0).text().strip()
                if not drone_id:
                    errors.append(f"Строка {row+1}: пустой ID -> исправлено на drone_{row+1}")
                    drone_id = f"drone_{row+1}"
                ip = self.table.item(row, 1).text().strip()
                try:
                    ipaddress.ip_address(ip)
                except ValueError:
                    warnings.append(f"Строка {row+1}: неверный IP '{ip}' -> исправлено на 192.168.1.1")
                    ip = "192.168.1.1"
                try:
                    port = int(self.table.item(row, 2).text())
                    if not (1000 <= port <= 65535):
                        warnings.append(f"Строка {row+1}: порт {port} вне диапазона -> исправлено на 20556")
                        port = 20556
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный формат порта -> исправлено на 20556")
                    port = 20556
                try:
                    alt = float(self.table.item(row, 3).text())
                    if not (0.1 <= alt <= 10.0):
                        warnings.append(f"Строка {row+1}: высота {alt} вне диапазона -> исправлено на 1.0")
                        alt = 1.0
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный формат высоты -> исправлено на 1.0")
                    alt = 1.0
                pattern = self.table.item(row, 4).text().strip().lower()
                if pattern not in VALID_PATTERNS:
                    warnings.append(f"Строка {row+1}: неверный паттерн '{pattern}' -> исправлено на 'hover'")
                    pattern = "hover"
                try:
                    size = float(self.table.item(row, 5).text())
                    if not (0.1 <= size <= 5.0):
                        warnings.append(f"Строка {row+1}: размер {size} вне диапазона -> исправлено на 1.0")
                        size = 1.0
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный формат размера -> исправлено на 1.0")
                    size = 1.0
                try:
                    reps = int(self.table.item(row, 6).text())
                    if not (1 <= reps <= 100):
                        warnings.append(f"Строка {row+1}: повторы {reps} вне диапазона -> исправлено на 1")
                        reps = 1
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный формат повторов -> исправлено на 1")
                    reps = 1
                try:
                    duration = float(self.table.item(row, 7).text())
                    if not (10 <= duration <= 300):
                        warnings.append(f"Строка {row+1}: длительность {duration} вне диапазона -> исправлено на 60")
                        duration = 60.0
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный формат длительности -> исправлено на 60")
                    duration = 60.0
                try:
                    interval = float(self.table.item(row, 8).text())
                    if not (0.01 <= interval <= 1.0):
                        warnings.append(f"Строка {row+1}: интервал {interval} вне диапазона -> исправлено на 0.05")
                        interval = 0.05
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный формат интервала -> исправлено на 0.05")
                    interval = 0.05
                no_fly_text = self.table.item(row, 9).text().strip().lower()
                no_fly = no_fly_text in ["true", "yes", "1", "да"]
                drone = {
                    "id": drone_id, "ip": ip, "port": port, "alt": alt,
                    "pattern": pattern, "size": size, "reps": reps,
                    "duration": duration, "interval": interval, "no_fly": no_fly
                }
                drones.append(drone)
            except Exception as e:
                errors.append(f"Строка {row+1}: критическая ошибка {str(e)}")
        
        message = ""
        if errors:
            message = "ОШИБКИ (использованы значения по умолчанию):\n\n" + "\n".join(errors)
        if warnings:
            if message: message += "\n\n"
            message += "ПРЕДУПРЕЖДЕНИЯ (значения исправлены автоматически):\n\n" + "\n".join(warnings)
        if message:
            QMessageBox.warning(self, "Проверка данных", message)
        
        save_drones(drones)
        success_msg = f"Сохранено {len(drones)} дронов в config.json"
        if errors or warnings:
            success_msg += " (некоторые значения были исправлены)"
        QMessageBox.information(self, "Результат", success_msg)
        print(success_msg)

    def delete_drone(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите дрона для удаления")
            return
        drone_id = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить дрона {drone_id}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            drones = load_drones()
            drones = [d for d in drones if d.get("id") != drone_id]
            save_drones(drones)
            self.refresh_table()
            QMessageBox.information(self, "Готово", f"Дрон {drone_id} удалён")

    # ==================== ЛОГИКА ЗАПУСКА ====================
    def start_fleet(self):
        if self.is_running:
            return
        self.save_to_json()
        drones_data = load_drones()
        if not drones_data:
            QMessageBox.critical(self, "Ошибка", "Список дронов пуст! Добавьте хотя бы одного дрона.")
            return
        tcp_list = [f"{d['ip']}:{d['port']}" for d in drones_data]
        primary_drone = drones_data[0]
        try:
            self.fleet = FleetManager(
                tcp_list=tcp_list,
                alt=primary_drone["alt"],
                size=primary_drone.get("size", 1.0),
                reps=primary_drone.get("reps", 1),
                interval=primary_drone.get("interval", 0.05),
                pattern=primary_drone["pattern"],
                duration=primary_drone.get("duration", 60.0),
                no_fly=primary_drone.get("no_fly", False)
            )
            self.is_running = True
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_label.setText("Статус: Подключение к дронам...")
            self.tabs.setCurrentIndex(1)
            self.fleet_thread = threading.Thread(target=self.fleet.run, daemon=True)
            self.fleet_thread.start()
            threading.Thread(target=self.wait_for_connection_and_plot, daemon=True).start()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка запуска", f"Не удалось запустить флот:\n{e}")
            self.is_running = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def wait_for_connection_and_plot(self):
        while self.is_running:
            if self.fleet and self.fleet.drones:
                try:
                    controller = self.fleet.drones[0]
                    QTimer.singleShot()
                    return
                except Exception as e:
                    print(f"Ошибка создания графика: {e}")
                    return
            time.sleep(0.2)

    def create_plot(self):
        while self.plot_layout.count():
            child = self.plot_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        # Создаём вкладки для каждого дрона
        self.drone_plots = QTabWidget()
        for i, drone in enumerate(self.fleet.drones):
            plot = RealtimePlot(drone.get_realtime_data, drone_name=f"Дрон {i+1}")
            self.drone_plots.addTab(plot, f"Дрон {i+1}")
            
        self.plot_layout.addWidget(self.drone_plots)
        self.status_label.setText("Статус: ПОЛЁТ / ЛОГИРОВАНИЕ")

    def stop_fleet(self):
        self.is_running = False
        self.status_label.setText("Статус: Остановка...")
        if self.fleet:
            for drone in self.fleet.drones:
                try:
                    drone.stop_logging()
                    if drone.drone:
                        drone.drone.land()
                except:
                    pass
        if self.fleet_thread:
            self.fleet_thread.join(timeout=2.0)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Статус: Остановлено")
        QMessageBox.information(self, "Готово", "Все дроны остановлены")