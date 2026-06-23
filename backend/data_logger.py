import csv
import os


class DataLogger:

    def __init__(self, filename="logs.csv"):
        self.filename = filename

        if not os.path.exists(filename):
            with open(filename, "w") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "t",
                    "drone_id", "experiment_id",
                    "x", "y", "z",
                    "battery"
                ])

    def write(self, log):
        pos = log.get("position") or {}

        with open(self.filename, "a") as f:
            writer = csv.writer(f)

            writer.writerow([
                log["timestamp"],
                log.get("t"),
                log["drone_id"],
                log["experiment_id"],
                pos.get("x"),
                pos.get("y"),
                pos.get("z"),
                log.get("battery"),
            ])