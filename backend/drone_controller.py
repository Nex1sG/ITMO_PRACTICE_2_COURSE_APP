import time
import math
import threading
from pioneer_sdk2 import Pioneer
from backend.data_logger import DataLogger


class DroneController:

    def __init__(
            self, tcp: str, alt: float = 1.0, size: float = 1.0,
            reps: int = 1, interval: float = 0.05, no_fly: bool = False):

        # for experiment initialization(flight)
        self.tcp = tcp
        self.alt = alt
        self.size = size
        self.reps = reps
        self.interval = interval
        self.no_fly = no_fly
        self.drone = None

        # logging system
        self.logs = []
        self.logs_lock = threading.Lock()
        self.logger = DataLogger()
        self.is_logging = threading.Event()
        self.log_thread = None
        self.experiment_start_time = None

        # metadata
        self.experiment_id = None
        self.drone_id = None
        self.pattern = None

    # utils for connection and copter moving
    def _require_connection(self):
        if self.drone is None:
            raise RuntimeError("Drone is not connected")

    def goto(self, x, y, z, yaw=0, wait=3):
        self._require_connection()
        self.drone.go_to_local_point(x=x, y=y, z=z, yaw=yaw)
        time.sleep(wait)

    def takeoff_and_hover(self):
        self._require_connection()
        if not self.drone.arm():
            raise RuntimeError("Arm failed")
        time.sleep(2)
        if not self.drone.takeoff():
            raise RuntimeError("Takeoff failed")
        time.sleep(5)
        self.goto(0, 0, self.alt)

    # utils for thread logging
    def start_logging(self):
        self.logs.clear()
        self.is_logging.set()

        self.experiment_start_time = time.time()

        self.log_thread = threading.Thread(
            target=self.monitor,
            daemon=True
        )
        self.log_thread.start()

    def stop_logging(self):
        self.is_logging.clear()
        if self.log_thread and self.log_thread.is_alive():
            self.log_thread.join(timeout=2)

    # --tcp
    def connect(self):
        print(f"Connecting to {self.tcp}...")
        self.drone = Pioneer(tcp=self.tcp, logger=True)
        print("Connected")

        if self.drone_id is None:
            self.drone_id = self.tcp

    def close(self):
        if self.drone is None:
            return
        self.drone.close_connection()
        self.logger.close()
        print(f"Connection closed for {self.drone_id}")

    # telemetry
    def get_telemetry(self):
        pos = self.drone.get_position()

        position = None
        if pos is not None:
            position = {
                "x": getattr(pos, "x", None),
                "y": getattr(pos, "y", None),
                "z": getattr(pos, "z", None),
            }

        return {
            "battery": self.drone.get_battery_status(),
            "orientation": self.drone.get_orientation(),
            "accel": self.drone.get_accel(),
            "gyro": self.drone.get_gyro(),
            "mag": self.drone.get_mag(),
            "rpm": self.drone.get_motors_rpm(),
            "position": position
        }

    def make_log(self):
        telemetry = self.get_telemetry()

        log = {
            "experiment_id": self.experiment_id,
            "drone_id": self.drone_id,
            "pattern": self.pattern,
            "timestamp": time.time(),
            "t": time.time() - (self.experiment_start_time or time.time()),
            "position": telemetry.get("position"),
            "attitude": telemetry.get("orientation"),
            "battery": telemetry.get("battery"),
        }

        self.logger.write(log)
        return log

    def monitor(self):
        if self.drone is None:
            return

        while self.is_logging.is_set():
            try:
                log_entry = self.make_log()
                with self.logs_lock:
                    self.logs.append(log_entry)
            except Exception as e:
                print(f"[{self.drone_id}] Monitor error: {e}")

            time.sleep(self.interval)

    # migration work
    def hover(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                time.sleep(15)
                self.drone.land()
        finally:
            self.stop_logging()

    def line(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                s = min(self.size, 0.4)
                for _ in range(self.reps):
                    self.goto(s, 0, self.alt)
                    self.goto(0, 0, self.alt)
                self.drone.land()
        finally:
            self.stop_logging()

    def backforth(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                s = min(self.size, 0.4)
                for _ in range(self.reps):
                    self.goto(s, 0, self.alt)
                    self.goto(-s, 0, self.alt)
                    self.goto(0, 0, self.alt)
                self.drone.land()
        finally:
            self.stop_logging()

    def square(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                s = min(self.size, 0.35)
                for _ in range(self.reps):
                    self.goto(s, s, self.alt)
                    self.goto(-s, s, self.alt)
                    self.goto(-s, -s, self.alt)
                    self.goto(s, -s, self.alt)
                self.goto(0, 0, self.alt)
                self.drone.land()
        finally:
            self.stop_logging()

    def rectangle(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                w = min(self.size, 0.45)
                h = w / 2
                for _ in range(self.reps):
                    self.goto(w, h, self.alt)
                    self.goto(-w, h, self.alt)
                    self.goto(-w, -h, self.alt)
                    self.goto(w, -h, self.alt)
                self.goto(0, 0, self.alt)
                self.drone.land()
        finally:
            self.stop_logging()

    def triangle(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                s = min(self.size, 0.4)
                for _ in range(self.reps):
                    self.goto(0, s, self.alt)
                    self.goto(-s, -s, self.alt)
                    self.goto(s, -s, self.alt)
                self.goto(0, 0, self.alt)
                self.drone.land()
        finally:
            self.stop_logging()

    def circle(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                r = min(self.size, 0.3)
                for _ in range(self.reps):
                    for i in range(24):
                        a = 2 * math.pi * i / 24
                        self.goto(r * math.cos(a), r * math.sin(a), self.alt, wait=0.5)
                self.goto(0, 0, self.alt)
                self.drone.land()
        finally:
            self.stop_logging()

    def figure8(self):
        self.start_logging()
        try:
            if not self.no_fly:
                self.takeoff_and_hover()
                r = min(self.size, 0.25)
                for _ in range(self.reps):
                    for i in range(48):
                        t = 2 * math.pi * i / 48
                        x = r * math.sin(t)
                        y = r * math.sin(t) * math.cos(t)
                        self.goto(x, y, self.alt, wait=0.4)
                self.goto(0, 0, self.alt)
                self.drone.land()
        finally:
            self.stop_logging()

    def execute_pattern(self, pattern):
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

        if pattern not in patterns:
            raise ValueError(f"Unknown pattern: {pattern}")

        patterns[pattern]()