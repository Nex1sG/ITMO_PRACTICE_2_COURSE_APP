
import threading
from pioneer_sdk2 import Pioneer
import os
import csv

class DataLogger:

    COLUMNS = [
        "timestamp", "t", "drone_id", "experiment_id", "pattern",

        "x", "y", "z",

        "vx", "vy", "vz",

        "roll", "pitch", "yaw",

        "ax", "ay", "az",
        "gx", "gy", "gz",
        "mx", "my", "mz",

        "rpm1", "rpm2", "rpm3", "rpm4",

        "battery",
    ]

    def __init__(self, filename):
        self._lock = threading.Lock()
        os.makedirs("logs", exist_ok=True)
        self._file = open(os.path.join("logs", filename), "a", newline="")
        self._writer = csv.writer(self._file)

        if self._file.tell() == 0:
            self._writer.writerow(self.COLUMNS)
            self._file.flush()

    def write(self, log: dict):
        row = [
            log.get("timestamp"),
            log.get("t"),
            log.get("drone_id"),
            log.get("experiment_id"),
            log.get("pattern"),

            log.get("x"),
            log.get("y"),
            log.get("z"),

            log.get("vx"),
            log.get("vy"),
            log.get("vz"),

            log.get("roll"),
            log.get("pitch"),
            log.get("yaw"),

            log.get("ax"),
            log.get("ay"),
            log.get("az"),

            log.get("gx"),
            log.get("gy"),
            log.get("gz"),

            log.get("mx"),
            log.get("my"),
            log.get("mz"),

            log.get("rpm1"),
            log.get("rpm2"),
            log.get("rpm3"),
            log.get("rpm4"),

            log.get("battery"),
        ]

        with self._lock:
            self._writer.writerow(row)
            self._file.flush()