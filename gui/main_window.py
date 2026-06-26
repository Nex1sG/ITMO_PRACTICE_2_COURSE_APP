import sys
import time
import threading
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QTabWidget,
    QInputDialog, QMessageBox, QComboBox, QStyledItemDelegate  # <-- Добавили сюда
)
from PySide6.QtCore import Qt, QTimer  # <-- Убрали QItemDelegate отсюда
from config.config import load_drones, save_drones
from backend.fleet_manager import FleetManager
from gui.realtime_plot import RealtimePlot

# Обновлённый класс делегата (используем QStyledItemDelegate)
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
        if value in self.PATTERNS:
            editor.setCurrentText(value)
        else:
            editor.setCurrentIndex(0)
    
    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система контроля дронов и визуализации телеметрии")
        self.resize(1400, 800)

        # Состояние системы
        self.fleet = None
        self.fleet_thread = None
        self.is_running = False

        # Основной виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Табы
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # === ВКЛАДКА 1: НАСТРОЙКИ ДРОНОВ ===
        self.tab_settings = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.tab_settings, "1. Дроны и Настройки")

        # === ВКЛАДКА 2: УПРАВЛЕНИЕ И ГРАФИКИ ===
        self.tab_control = QWidget()
        self.setup_control_tab()
        self.tabs.addTab(self.tab_control, "2. Полёт и Графики")

        # Загружаем данные
        self.refresh_table()

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
        
        # 🔥 Устанавливаем делегат для Pattern (колонка 4)
        self.table.setItemDelegateForColumn(4, PatternDelegate())
        
        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Добавить дрона")
        self.btn_add.clicked.connect(self.add_drone_dialog)
        
        self.btn_save = QPushButton("💾 Сохранить в JSON")
        self.btn_save.clicked.connect(self.save_to_json)
        
        self.btn_delete = QPushButton("🗑️ Удалить выбранного")
        self.btn_delete.clicked.connect(self.delete_drone)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def setup_control_tab(self):
        layout = QVBoxLayout(self.tab_control)

        # Панель управления
        control_panel = QHBoxLayout()
        
        self.btn_start = QPushButton("🚀 ЗАПУСТИТЬ ФЛОТ")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px; padding: 10px;")
        self.btn_start.clicked.connect(self.start_fleet)
        
        self.btn_stop = QPushButton("⏹️ ОСТАНОВИТЬ")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; font-size: 16px; padding: 10px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_fleet)

        self.status_label = QLabel("📊 Статус: Готов к запуску")
        self.status_label.setStyleSheet("font-size: 14px; margin-left: 10px;")

        control_panel.addWidget(self.btn_start)
        control_panel.addWidget(self.btn_stop)
        control_panel.addWidget(self.status_label)
        layout.addLayout(control_panel)

        # Область графиков
        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_container)
        layout.addWidget(self.plot_container)

    # ====================
    # ЛОГИКА ТАБЛИЦЫ
    # ====================

    def refresh_table(self):
        """Загружает данные из config.json в таблицу"""
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
            
            no_fly_str = "✅ Да" if drone.get("no_fly", False) else "❌ Нет"
            self.table.setItem(row, 9, QTableWidgetItem(no_fly_str))

    def add_drone_dialog(self):
        """Диалог добавления нового дрона"""
        ip, ok1 = QInputDialog.getText(self, "Новый дрон", "Введите IP адрес:", text="192.168.1.10")
        if not ok1 or not ip:
            return

        # 🔥 FIX: minValue/maxValue вместо min/max
        port, ok2 = QInputDialog.getInt(
            self, "Новый дрон", "Введите порт:", 
            value=20556, minValue=1000, maxValue=65535
        )
        if not ok2:
            return

        drones = load_drones()
        new_id = f"drone_{len(drones) + 1}"
        
        new_drone = {
            "id": new_id,
            "ip": ip,
            "port": port,
            "alt": 1.0,
            "pattern": "hover",
            "size": 1.0,
            "reps": 1,
            "duration": 60.0,
            "interval": 0.05,
            "no_fly": True  # По умолчанию безопасный режим
        }
        
        drones.append(new_drone)
        save_drones(drones)
        
        QMessageBox.information(self, "✅ Успех", f"Дрон {new_id} добавлен!\nНастройте параметры в таблице.")
        self.refresh_table()

    def save_to_json(self):
        """Сохраняет данные из таблицы с ВАЛИДАЦИЕЙ"""
        VALID_PATTERNS = ["hover", "line", "backforth", "square", "rectangle", 
                          "triangle", "circle", "ellipse", "figure8"]
        
        drones = []
        errors = []
        
        for row in range(self.table.rowCount()):
            try:
                # ID и IP
                drone_id = self.table.item(row, 0).text().strip()
                ip = self.table.item(row, 1).text().strip()
                
                # Port
                try:
                    port = int(self.table.item(row, 2).text())
                    if not (1000 <= port <= 65535):
                        errors.append(f"Строка {row+1}: порт {port} вне диапазона (1000-65535)")
                        port = 20556
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный порт")
                    port = 20556
                
                # Alt
                try:
                    alt = float(self.table.item(row, 3).text())
                    if not (0.1 <= alt <= 10.0):
                        errors.append(f"Строка {row+1}: высота {alt}м вне диапазона (0.1-10)")
                        alt = 1.0
                except ValueError:
                    errors.append(f"Строка {row+1}: неверная высота")
                    alt = 1.0
                
                # Pattern
                pattern = self.table.item(row, 4).text().strip().lower()
                if pattern not in VALID_PATTERNS:
                    errors.append(f"Строка {row+1}: недопустимый паттерн '{pattern}'")
                    pattern = "hover"
                
                # Size
                try:
                    size = float(self.table.item(row, 5).text())
                    if not (0.1 <= size <= 5.0):
                        errors.append(f"Строка {row+1}: размер {size}м вне диапазона (0.1-5)")
                        size = 1.0
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный размер")
                    size = 1.0
                
                # Reps
                try:
                    reps = int(self.table.item(row, 6).text())
                    if not (1 <= reps <= 100):
                        errors.append(f"Строка {row+1}: повторы {reps} вне диапазона (1-100)")
                        reps = 1
                except ValueError:
                    errors.append(f"Строка {row+1}: неверное число повторов")
                    reps = 1
                
                # Duration
                try:
                    duration = float(self.table.item(row, 7).text())
                    if not (10 <= duration <= 300):
                        errors.append(f"Строка {row+1}: длительность {duration}с вне диапазона (10-300)")
                        duration = 60.0
                except ValueError:
                    errors.append(f"Строка {row+1}: неверная длительность")
                    duration = 60.0
                
                # Interval
                try:
                    interval = float(self.table.item(row, 8).text())
                    if not (0.01 <= interval <= 1.0):
                        errors.append(f"Строка {row+1}: интервал {interval}с вне диапазона (0.01-1)")
                        interval = 0.05
                except ValueError:
                    errors.append(f"Строка {row+1}: неверный интервал")
                    interval = 0.05
                
                # No Fly
                no_fly_text = self.table.item(row, 9).text()
                no_fly = ("Да" in no_fly_text)
                
                drone = {
                    "id": drone_id,
                    "ip": ip,
                    "port": port,
                    "alt": alt,
                    "pattern": pattern,
                    "size": size,
                    "reps": reps,
                    "duration": duration,
                    "interval": interval,
                    "no_fly": no_fly
                }
                drones.append(drone)
                
            except Exception as e:
                errors.append(f"Строка {row+1}: {str(e)}")
        
        # Показываем предупреждения
        if errors:
            error_text = "⚠️ Найдены ошибки (использованы значения по умолчанию):\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Ошибки валидации", error_text)
        
        save_drones(drones)
        QMessageBox.information(self, "✅ Успех", f"Сохранено {len(drones)} дронов в config.json")

    def delete_drone(self):
        """Удаляет выбранного дрона"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "⚠️ Внимание", "Выберите дрона для удаления")
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
            QMessageBox.information(self, "✅ Удалено", f"Дрон {drone_id} удалён")

    # ====================
    # ЛОГИКА ЗАПУСКА
    # ====================

    def start_fleet(self):
        """Запускает флот дронов"""
        if self.is_running:
            return
        
        # Сохраняем настройки
        self.save_to_json()
        
        # Читаем конфиг
        drones_data = load_drones()
        if not drones_data:
            QMessageBox.critical(self, "❌ Ошибка", "Список дронов пуст!")
            return

        # Формируем список адресов
        tcp_list = [f"{d['ip']}:{d['port']}" for d in drones_data]
        
        # Берём параметры первого дрона (пока глобально)
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

            # Запуск
            self.is_running = True
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_label.setText("🔄 Статус: Подключение к дронам...")
            self.tabs.setCurrentIndex(1)
            
            self.fleet_thread = threading.Thread(target=self.fleet.run, daemon=True)
            self.fleet_thread.start()
            
            # Проверка подключения
            threading.Thread(target=self.wait_for_connection_and_plot, daemon=True).start()
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Ошибка запуска", f"Не удалось запустить флот:\n{e}")
            self.is_running = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def wait_for_connection_and_plot(self):
        """Ожидает подключения и создаёт графики"""
        while self.is_running:
            if self.fleet and self.fleet.drones:
                try:
                    controller = self.fleet.drones[0]
                    
                    # Создаём график
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self.create_plot(controller))
                    return
                except Exception as e:
                    print(f"Ошибка создания графика: {e}")
                    return
            time.sleep(0.2)

    def create_plot(self, controller):
        """Создаёт виджет графиков"""
        # Очищаем контейнер
        while self.plot_layout.count():
            child = self.plot_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Создаём график
        window = RealtimePlot(controller.get_realtime_data)
        self.plot_layout.addWidget(window)
        window.show()
        
        self.status_label.setText("✈️ Статус: ПОЛЁТ / ЛОГИРОВАНИЕ")
        QMessageBox.information(self, "✅ Запуск успешен", "Дроны подключены. Графики обновляются.")

    def stop_fleet(self):
        """Останавливает флот"""
        self.is_running = False
        self.status_label.setText("⏹️ Статус: Остановка...")
        
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
        self.status_label.setText("📊 Статус: Остановлено")
        QMessageBox.information(self, "✅ Остановлено", "Все дроны остановлены")