import time
import math
import threading
import random
from collections import deque
from pioneer_sdk2 import Pioneer
from threading import Barrier, BrokenBarrierError
from backend.data_logger import DataLogger
from backend.realtime_processor import RealtimeTelemetryProcessor

class DroneController:
    def __init__(self, tcp: str, alt: float = 1.0, size: float = 1.0,
                 reps: int = 1, interval: float = 0.05, no_fly: bool = False):
        self.tcp = tcp
        self.alt = alt
        self.size = size
        self.reps = reps
        self.interval = interval
        self.no_fly = no_fly
        
        self.drone = None
        self.logger = None
        self.is_logging = threading.Event()
        self.log_thread = None
        self.experiment_start_time = None
        self.experiment_id = None
        self.drone_id = None
        self.pattern = None
        
        self.buffer_lock = threading.Lock()
        self.buffer_size = 200
        self.time_buffer = deque(maxlen=self.buffer_size)
        self.x_buffer = deque(maxlen=self.buffer_size)
        self.y_buffer = deque(maxlen=self.buffer_size)
        self.z_buffer = deque(maxlen=self.buffer_size)
        
        self.realtime = RealtimeTelemetryProcessor(buffer_size=200)
        
        self.ax_buffer = deque(maxlen=self.buffer_size)
        self.ay_buffer = deque(maxlen=self.buffer_size)
        self.az_buffer = deque(maxlen=self.buffer_size)
        self.battery_buffer = deque(maxlen=self.buffer_size)
        
        self.barrier = None

    def _require_connection(self):
        if self.drone is None:
            raise RuntimeError("Дрон не подключён")

    def connect(self):
        print(f"[{self.drone_id}] Подключение к {self.tcp}...")
        try:
            self.drone = Pioneer(tcp=self.tcp, logger=True)
            print(f"[{self.drone_id}] Успешно подключён.")
            
            if self.drone_id is None:
                self.drone_id = self.tcp.replace(":", "_")
                
            self.logger = DataLogger(filename=f"logs_{self.drone_id}.csv")
            return True
        except Exception as e:
            print(f"[{self.drone_id}] Ошибка подключения: {e}")
            raise

    def close(self):
        if self.drone is None:
            return
            
        print(f"[{self.drone_id}] Отключение...")
        try:
            self.drone.close_connection()
        except Exception as e:
            print(f"[{self.drone_id}] Ошибка отключения: {e}")
            
        try:
            if self.logger:
                self.logger.close()
        except Exception:
            pass
            
        print(f"[{self.drone_id}] Соединение закрыто.")

    def goto(self, x, y, z, yaw=0, timeout=15):
        self._require_connection()
        print(f"[{self.drone_id}] Движение в точку {x}, {y}, {z}...")
        self.drone.go_to_local_point(x=x, y=y, z=z, yaw=yaw)
        
        start = time.time()
        while time.time() - start < timeout:
            try:
                if self.drone.point_reached():
                    print(f"[{self.drone_id}] Точка достигнута.")
                    return True
            except Exception:
                pass
            time.sleep(0.1)
            
        print(f"[{self.drone_id}] Таймаут движения: {x, y, z}")
        return False

    def takeoff_and_hover(self):
        self._require_connection()
        print(f"[{self.drone_id}] Проверка состояния перед армингом...")
        
        try:
            battery = self.drone.get_battery_status()
            if battery:
                print(f"[{self.drone_id}] Напряжение батареи: {battery[0]:.2f}V")
                if battery[0] < 10.5:
                    print(f"[{self.drone_id}] ВНИМАНИЕ: Низкий заряд батареи!")
        except Exception as e:
            print(f"[{self.drone_id}] Не удалось проверить батарею: {e}")

        base_wait = 3.0
        random_wait = random.uniform(0, 5.0)
        total_wait = base_wait + random_wait
        
        print(f"[{self.drone_id}] Ожидание инициализации {total_wait:.1f} сек...")
        time.sleep(total_wait)

        print(f"[{self.drone_id}] Арминг моторов...")
        max_attempts = 8
        for attempt in range(max_attempts):
            try:
                if self.drone.arm():
                    print(f"[{self.drone_id}] Арминг успешен (попытка {attempt + 1}).")
                    time.sleep(1.0)
                    break
                else:
                    print(f"[{self.drone_id}] Попытка {attempt + 1} не удалась. Ждём...")
                    wait_time = 4.0 + random.uniform(0, 2.0)
                    time.sleep(wait_time)
            except Exception as e:
                print(f"[{self.drone_id}] Ошибка арминга (попытка {attempt + 1}): {e}")
                wait_time = 4.0 + random.uniform(0, 2.0)
                time.sleep(wait_time)
        else:
            print(f"[{self.drone_id}] АРМИНГ НЕ УДАЛСЯ после {max_attempts} попыток.")
            print(f"[{self.drone_id}] Проверьте:")
            print(f"[{self.drone_id}] - Заряд батареи")
            print(f"[{self.drone_id}] - Калибровку дронов")
            print(f"[{self.drone_id}] - Наличие GPS сигнала (если требуется)")
            raise RuntimeError("Arm failed after multiple attempts")

        print(f"[{self.drone_id}] Арминг выполнен. Взлёт...")
        self.drone.takeoff()
        time.sleep(5)
        
        print(f"[{self.drone_id}] Зависание на высоте {self.alt} м...")
        self.goto(0, 0, self.alt)
        time.sleep(0.5)
        print(f"[{self.drone_id}] Логирование запущено.")

    def start_logging(self):
        if self.is_logging.is_set():
            return
            
        if self.drone is None:
            raise RuntimeError("Дрон не подключён")
        if self.logger is None:
            raise RuntimeError("Логгер не инициализирован")

        self.experiment_start_time = time.time()
        self.is_logging.set()
        self.log_thread = threading.Thread(target=self.monitor, daemon=True)
        self.log_thread.start()
        print(f"[{self.drone_id}] Поток логирования запущен.")

    def stop_logging(self):
        self.is_logging.clear()
        if self.log_thread and self.log_thread.is_alive():
            self.log_thread.join(timeout=2)
        self.log_thread = None
        print(f"[{self.drone_id}] Логирование остановлено.")

    def get_telemetry(self):
        def safe(call):
            try:
                return call()
            except:
                return None

        pos = safe(self.drone.get_local_position_lps)
        vel = safe(self.drone.get_local_velocity_lps)
        att = safe(self.drone.get_orientation)
        accel = safe(self.drone.get_accel)
        gyro = safe(self.drone.get_gyro)
        mag = safe(self.drone.get_mag)
        rpm = safe(self.drone.get_motors_rpm)
        battery = safe(self.drone.get_battery_status)

        return pos, vel, att, accel, gyro, mag, rpm, battery

    def make_log(self):
        pos, vel, att, accel, gyro, mag, rpm, battery = self.get_telemetry()
        t = time.time() - self.experiment_start_time if self.experiment_start_time else 0

        def safe_get(obj, key):
            if obj is None: return None
            if isinstance(key, str) and hasattr(obj, key): return getattr(obj, key)
            try: return obj[key]
            except (TypeError, IndexError, KeyError): return None

        return {
            "timestamp": time.time(),
            "t": t,
            "drone_id": self.drone_id,
            "experiment_id": self.experiment_id,
            "pattern": self.pattern,
            "x": safe_get(pos, "x"), "y": safe_get(pos, "y"), "z": safe_get(pos, "z"),
            "vx": safe_get(vel, "x"), "vy": safe_get(vel, "y"), "vz": safe_get(vel, "z"),
            "roll": safe_get(att, "roll"), "pitch": safe_get(att, "pitch"), "yaw": safe_get(att, "yaw"),
            "ax": safe_get(accel, 0), "ay": safe_get(accel, 1), "az": safe_get(accel, 2),
            "gx": safe_get(gyro, 0), "gy": safe_get(gyro, 1), "gz": safe_get(gyro, 2),
            "mx": safe_get(mag, 0), "my": safe_get(mag, 1), "mz": safe_get(mag, 2),
            "rpm1": safe_get(rpm, 0), "rpm2": safe_get(rpm, 1),
            "rpm3": safe_get(rpm, 2), "rpm4": safe_get(rpm, 3),
            "battery": safe_get(battery, 0) if isinstance(battery, (list, tuple)) else battery,
        }

    def monitor(self):
        print(f"[{self.drone_id}] Цикл мониторинга запущен.")
        while self.is_logging.is_set():
            try:
                if not self.drone or not self.logger:
                    time.sleep(self.interval)
                    continue

                log = self.make_log()
                self.logger.write(log)
                self.realtime.update(log)

                with self.buffer_lock:
                    self.time_buffer.append(log["t"])
                    self.x_buffer.append(log["x"])
                    self.y_buffer.append(log["y"])
                    self.z_buffer.append(log["z"])
                    self.ax_buffer.append(log["ax"])
                    self.ay_buffer.append(log["ay"])
                    self.az_buffer.append(log["az"])
                    self.battery_buffer.append(log["battery"])
                    
            except Exception as e:
                print(f"[{self.drone_id}] Ошибка логирования: {e}")
                
            time.sleep(self.interval)
            
        print(f"[{self.drone_id}] Цикл мониторинга завершён.")

    def get_realtime_data(self):
        with self.buffer_lock:
            return {
                "t": list(self.time_buffer),
                "x": list(self.x_buffer), "y": list(self.y_buffer), "z": list(self.z_buffer),
                "ax": list(self.ax_buffer), "ay": list(self.ay_buffer), "az": list(self.az_buffer),
                "battery": list(self.battery_buffer)
            }

    def hover(self):
        print(f"[{self.drone_id}] Выполнение зависания...")
        max_iterations = int(self.reps * 15 / self.interval)
        start_time = time.time()
        
        for _ in range(max_iterations):
            if not self.is_logging.is_set():
                break
            if time.time() - start_time > self.reps * 15:
                break
            self.goto(0, 0, self.alt)
            time.sleep(self.interval)

    def line(self):
        print(f"[{self.drone_id}] Выполнение линии...")
        s = min(self.size, 0.8)
        for _ in range(self.reps):
            if not self.goto(s, 0, self.alt): return
            if not self.goto(0, 0, self.alt): return

    def backforth(self):
        print(f"[{self.drone_id}] Выполнение возвратно-поступательного движения...")
        s = min(self.size, 0.8)
        for _ in range(self.reps):
            if not self.goto(s, 0, self.alt): return
            if not self.goto(-s, 0, self.alt): return
            if not self.goto(0, 0, self.alt): return

    def square(self):
        print(f"[{self.drone_id}] Выполнение квадрата...")
        s = min(self.size, 0.8)
        for _ in range(self.reps):
            if not self.goto(s, s, self.alt): return
            if not self.goto(-s, s, self.alt): return
            if not self.goto(-s, -s, self.alt): return
            if not self.goto(s, -s, self.alt): return
            if not self.goto(s, s, self.alt): return
            if not self.goto(0, 0, self.alt): return

    def rectangle(self):
        print(f"[{self.drone_id}] Выполнение прямоугольника...")
        w = min(self.size, 0.8)
        h = w / 2
        for _ in range(self.reps):
            if not self.goto(w, h, self.alt): return
            if not self.goto(-w, h, self.alt): return
            if not self.goto(-w, -h, self.alt): return
            if not self.goto(w, -h, self.alt): return
            if not self.goto(0, 0, self.alt): return

    def triangle(self):
        print(f"[{self.drone_id}] Выполнение треугольника...")
        s = min(self.size, 0.8)
        for _ in range(self.reps):
            if not self.goto(0, s, self.alt): return
            if not self.goto(-s, -s, self.alt): return
            if not self.goto(s, -s, self.alt): return
            if not self.goto(0, 0, self.alt): return

    def circle(self):
        print(f"[{self.drone_id}] Выполнение круга...")
        r = min(self.size, 0.6)
        for _ in range(self.reps):
            for i in range(24):
                a = 2 * math.pi * i / 24
                x = r * math.cos(a)
                y = r * math.sin(a)
                if not self.goto(x, y, self.alt): return
            if not self.goto(0, 0, self.alt): return

    def figure8(self):
        print(f"[{self.drone_id}] Выполнение восьмёрки...")
        r = min(self.size, 0.5)
        for _ in range(self.reps):
            for i in range(48):
                t = 2 * math.pi * i / 48
                x = r * math.sin(t)
                y = r * math.sin(t) * math.cos(t)
                if not self.goto(x, y, self.alt): return
            if not self.goto(0, 0, self.alt): return

    def _run_pattern(self, fn):
        if self.no_fly:
            print(f"[{self.drone_id}] Режим симуляции (no_fly=True). Полёт не выполняется.")
            return

        self._require_connection()
        self.takeoff_and_hover()
        self.start_logging()
        
        try:
            fn()
        except Exception as e:
            print(f"[{self.drone_id}] Ошибка выполнения паттерна: {e}")
        finally:
            print(f"[{self.drone_id}] Паттерн завершён. Запуск посадки...")
            self.stop_logging()
            try:
                self.drone.land()
                time.sleep(5)
                self.drone.disarm()
                print(f"[{self.drone_id}] Посадка и дизарминг выполнены.")
            except Exception as e:
                print(f"[{self.drone_id}] Ошибка посадки/дизарминга: {e}")

    def execute_pattern(self, pattern: str):
        if not self.drone:
            raise RuntimeError("Дрон не подключён")

        patterns = {
            "hover": self.hover, "line": self.line, "backforth": self.backforth,
            "square": self.square, "rectangle": self.rectangle, "triangle": self.triangle,
            "circle": self.circle, "figure8": self.figure8
        }
        
        fn = patterns.get(pattern)
        if not fn:
            raise ValueError(f"Неизвестный паттерн: {pattern}")

        if self.barrier:
            try:
                print(f"[{self.drone_id}] Ожидание синхронизации...")
                self.barrier.wait()
            except BrokenBarrierError:
                print(f"[{self.drone_id}] Синхронизация нарушена. Прерывание.")
                return

        self._run_pattern(fn)
        print(f"[{self.drone_id}] Миссия завершена.")