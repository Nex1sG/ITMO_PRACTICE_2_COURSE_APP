import time
import math
import threading
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
        self.barrier = None  # Будет установлен из FleetManager

    def _require_connection(self):
        if self.drone is None:
            raise RuntimeError("Drone is not connected")

    def connect(self):
        print(f"Connecting to {self.tcp}...")
        self.drone = Pioneer(tcp=self.tcp, logger=True)
        print("Connected")
        if self.drone_id is None:
            self.drone_id = self.tcp.replace(":", "_")
        self.logger = DataLogger(filename=f"logs_{self.drone_id}.csv")

    def close(self):
        if self.drone is None:
            return
        try:
            self.drone.close_connection()
        except Exception as e:
            print(f"[{self.drone_id}] Disconnect error: {e}")
        try:
            if self.logger:
                self.logger.close()
        except Exception:
            pass
        print(f"Connection closed for {self.drone_id}")
    def goto(self, x, y, z, yaw=0, timeout=15):
        self._require_connection()
        self.drone.go_to_local_point(x=x, y=y, z=z, yaw=yaw)
        start = time.time()
        while time.time() - start < timeout:
            try:
                if self.drone.point_reached():
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        print(f"[{self.drone_id}] Point timeout: {x, y, z}")
        return False

    def takeoff_and_hover(self):
        self._require_connection()
        print(f"[{self.drone_id}] Arming...")
        if not self.drone.arm():
            raise RuntimeError("Arm failed")
        print(f"[{self.drone_id}] Taking off...")
        self.drone.takeoff()
        time.sleep(5)
        self.goto(0, 0, self.alt)
        time.sleep(0.5)
        print(f"[{self.drone_id}] Logging started")
        
    def start_logging(self):
        if self.is_logging.is_set():
            return
        if self.drone is None:
            raise RuntimeError("Drone not connected yet")
        if self.logger is None:
            raise RuntimeError("Logger not initialized")
        self.experiment_start_time = time.time()
        self.is_logging.set()
        self.log_thread = threading.Thread(target=self.monitor, daemon=True)
        self.log_thread.start()

    def stop_logging(self):
        self.is_logging.clear()
        if self.log_thread and self.log_thread.is_alive():
            self.log_thread.join(timeout=2)
        self.log_thread = None

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
            if obj is None:
                return None
            if isinstance(key, str) and hasattr(obj, key):
                return getattr(obj, key)
            try:
                return obj[key]
            except (TypeError, IndexError, KeyError):
                return None
        
        return {
            "timestamp": time.time(),
            "t": t,
            "drone_id": self.drone_id,
            "experiment_id": self.experiment_id,
            "pattern": self.pattern,
            "x": safe_get(pos, "x"),
            "y": safe_get(pos, "y"),
            "z": safe_get(pos, "z"),
            "vx": safe_get(vel, "x"),
            "vy": safe_get(vel, "y"),
            "vz": safe_get(vel, "z"),
            "roll": safe_get(att, "roll"),
            "pitch": safe_get(att, "pitch"),
            "yaw": safe_get(att, "yaw"),
            "ax": safe_get(accel, 0),
            "ay": safe_get(accel, 1),
            "az": safe_get(accel, 2),
            "gx": safe_get(gyro, 0),
            "gy": safe_get(gyro, 1),
            "gz": safe_get(gyro, 2),
            "mx": safe_get(mag, 0),
            "my": safe_get(mag, 1),
            "mz": safe_get(mag, 2),
            "rpm1": safe_get(rpm, 0),
            "rpm2": safe_get(rpm, 1),
            "rpm3": safe_get(rpm, 2),
            "rpm4": safe_get(rpm, 3),
            "battery": safe_get(battery, 0) if isinstance(battery, (list, tuple)) else battery,
        }

    def monitor(self):
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
                print(f"[{self.drone_id}] logging error: {e}")
            time.sleep(self.interval)

    def get_realtime_data(self):
        with self.buffer_lock:
            return {
                "t": list(self.time_buffer),
                "x": list(self.x_buffer),
                "y": list(self.y_buffer),
                "z": list(self.z_buffer),
                "ax": list(self.ax_buffer),
                "ay": list(self.ay_buffer),
                "az": list(self.az_buffer),
                "battery": list(self.battery_buffer)
            }
    def hover(self):
        for _ in range(int(15 / self.interval)):
            self.goto(0, 0, self.alt)
            time.sleep(self.interval)

    def line(self):
        s = min(self.size, 0.4)
        for _ in range(self.reps):
            if not self.goto(s, 0, self.alt):
                return
            if not self.goto(0, 0, self.alt):
                return

    def backforth(self):
        s = min(self.size, 0.4)
        for _ in range(self.reps):
            if not self.goto(s, 0, self.alt):
                return
            if not self.goto(-s, 0, self.alt):
                return
            if not self.goto(0, 0, self.alt):
                return

    def square(self):
        s = min(self.size, 1.2)
        for _ in range(self.reps):
            if not self.goto(s, s, self.alt):
                return
            if not self.goto(-s, s, self.alt):
                return
            if not self.goto(-s, -s, self.alt):
                return
            if not self.goto(s, -s, self.alt):
                return
            if not self.goto(s, s, self.alt):
                return
            if not self.goto(0, 0, self.alt):
                return

    def rectangle(self):
        w = min(self.size, 0.45)
        h = w / 2
        for _ in range(self.reps):
            if not self.goto(w, h, self.alt):
                return
            if not self.goto(-w, h, self.alt):
                return
            if not self.goto(-w, -h, self.alt):
                return
            if not self.goto(w, -h, self.alt):
                return
            if not self.goto(0, 0, self.alt):
                return

    def triangle(self):
        s = min(self.size, 0.4)
        for _ in range(self.reps):
            if not self.goto(0, s, self.alt):
                return
            if not self.goto(-s, -s, self.alt):
                return
            if not self.goto(s, -s, self.alt):
                return
            if not self.goto(0, 0, self.alt):
                return

    def circle(self):
        r = min(self.size, 0.3)
        for _ in range(self.reps):
            for i in range(24):
                a = 2 * math.pi * i / 24
                x = r * math.cos(a)
                y = r * math.sin(a)
                if not self.goto(x, y, self.alt):
                    return
            if not self.goto(0, 0, self.alt):
                return

    def figure8(self):
        r = min(self.size, 0.25)
        for _ in range(self.reps):
            for i in range(48):
                t = 2 * math.pi * i / 48
                x = r * math.sin(t)
                y = r * math.sin(t) * math.cos(t)
                if not self.goto(x, y, self.alt):
                    return
            if not self.goto(0, 0, self.alt):
                return
    def _run_pattern(self, fn):
        if self.no_fly:
            print(f"[{self.drone_id}] Simulation mode (no_fly=True)")
            return
        self._require_connection()
        self.takeoff_and_hover()
        self.start_logging()
        try:
            fn()
        except Exception as e:
            print(f"[{self.drone_id}] pattern error: {e}")
        finally:
            self.stop_logging()
            try:
                self.drone.land()
                self.drone.disarm()
            except:
                pass

    def execute_pattern(self, pattern: str):
        if not self.drone:
            raise RuntimeError("Not connected")
        patterns = {
            "hover": self.hover,
            "line": self.line,
            "backforth": self.backforth,
            "square": self.square,
            "rectangle": self.rectangle,
            "triangle": self.triangle,
            "circle": self.circle,
            "figure8": self.figure8,
        }
        fn = patterns.get(pattern)
        if not fn:
            raise ValueError(f"Unknown pattern: {pattern}")
        if self.barrier:
            try:
                self.barrier.wait()
            except BrokenBarrierError:
                print(f"[{self.drone_id}] Barrier broken (sync failed). Aborting pattern.")
                return
        self._run_pattern(fn)