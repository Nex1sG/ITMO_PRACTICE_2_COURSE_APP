import time
import threading
from threading import Barrier
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
        shared_barrier = Barrier(n, timeout=5.0)
        
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
            drone.barrier = shared_barrier
            self.drones.append(drone)

    def run(self):
        print(f"[FleetManager] Setting up fleet with {len(self.tcp_list)} drones...")
        self.setup_fleet()
        
        print("[FleetManager] Connecting to drones...")
        for i, d in enumerate(self.drones):
            try:
                d.connect()
                print(f"[FleetManager] Drone {i+1} connected")
            except Exception as e:
                print(f"[FleetManager] Failed to connect drone {i+1}: {e}")
            time.sleep(0.5)
        
        print("[FleetManager] Starting flight threads...")
        threads = []
        for i, d in enumerate(self.drones):
            t = threading.Thread(
                target=d.execute_pattern,
                args=(self.pattern,)
            )
            t.start()
            threads.append(t)
            print(f"[FleetManager] Thread started for drone {i+1}")
        
        print("[FleetManager] Waiting for all drones to complete...")
        for i, t in enumerate(threads):
            t.join()
            print(f"[FleetManager] Drone {i+1} completed")
        
        print("[FleetManager] All drones finished")