import time
import threading
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

        if not self.drones:
            print("No drones configured!")
            return

        # Подключаем всех
        for d in self.drones:
            try:
                d.connect()
            except Exception as e:
                print(f"Failed to connect {d.drone_id}: {e}")

        # Синхронизируем время старта
        start_time = time.time()
        for d in self.drones:
            d.experiment_start_time = start_time
            d.experiment_id = "exp_001"

        # Запускаем параллельно
        threads = []
        for d in self.drones:
            t = threading.Thread(
                target=d.execute_pattern,
                args=(self.pattern,),
                name=d.drone_id
            )
            t.start()
            threads.append(t)

        # Ждём завершения всех
        for t in threads:
            t.join()

        # Отключаем всех
        for d in self.drones:
            d.close()

        print("All drones finished.")