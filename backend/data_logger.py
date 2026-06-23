import csv
import os
import threading


class DataLogger:

    def __init__(self, filename="logs.csv"):
        self.filename = filename
        self._lock = threading.Lock()
        self._file = None
        self._writer = None
        self._init_file()

    def _init_file(self):
        file_exists = os.path.exists(self.filename)
        self._file = open(self.filename, "a", newline="")
        self._writer = csv.writer(self._file)
        if not file_exists:
            self._writer.writerow([
                "timestamp", "t",
                "drone_id", "experiment_id",
                "x", "y", "z",
                "battery"
            ])
            self._file.flush()

    def write(self, log):
        pos = log.get("position") or {}
        row = [
            log.get("timestamp"),
            log.get("t"),
            log.get("drone_id"),
            log.get("experiment_id"),
            pos.get("x"),
            pos.get("y"),
            pos.get("z"),
            log.get("battery"),
        ]
        with self._lock:
            self._writer.writerow(row)
            self._file.flush()

    def close(self):
        with self._lock:
            if self._file and not self._file.closed:
                self._file.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass