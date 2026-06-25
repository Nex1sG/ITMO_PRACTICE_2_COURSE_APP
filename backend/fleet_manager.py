import time
import math
import threading
from collections import deque
from pioneer_sdk2 import Pioneer
from backend.drone_controller import DroneController


class FleetManager:

    def __init__(self, tcp_list, alt, size, reps, interval, pattern, duration, no_fly):
        if isinstance(tcp_list, str):
            tcp_list = [tcp_list]

        self.tcp_list = tcp_list
        self.alt = alt
        self.size = size
        self.reps = reps
        self.interval = interval
        self.pattern = pattern
        self.duration = duration
        self.no_fly = no_fly

        self.drones = []

    def setup_fleet(self, n=None):
        if n is None:
            n = len(self.tcp_list)

        for i in range(min(n, len(self.tcp_list))):
            drone = DroneController(
                tcp=self.tcp_list[i],
                alt=self.alt,
                size=self.size,
                reps=self.reps,
                interval=self.interval,
                no_fly=self.no_fly
            )
            drone.drone_id = f"drone_{i+1}"
            drone.pattern = self.pattern
            self.drones.append(drone)

    def run(self):
        self.setup_fleet()

        for d in self.drones:
            d.connect()

        time.sleep(0.5)

        threads = []
        for d in self.drones:
            t = threading.Thread(
                target=d.execute_pattern,
                args=(self.pattern,)
            )
            t.start()
            threads.append(t)

        for t in threads:
            t.join()