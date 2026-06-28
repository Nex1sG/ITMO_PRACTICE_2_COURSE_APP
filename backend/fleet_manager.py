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
        self.status = "Готов"

    def setup_fleet(self, n=None):
        self.status = "Инициализация..."
        if n is None:
            n = len(self.tcp_list)
        shared_barrier = Barrier(len(self.tcp_list), timeout=10.0)
        for i, ip_port in enumerate(self.tcp_list):
            drone = DroneController(
                tcp=ip_port,
                alt=self.alt, size=self.size,
                reps=self.reps, interval=self.interval,
                no_fly=self.no_fly
            )
            drone.drone_id = f"drone_{i+1}"
            drone.pattern = self.pattern
            drone.barrier = shared_barrier
            self.drones.append(drone)

    def run(self):
        print(f"[Диспетчер] Запуск флота: {len(self.tcp_list)} дронов.")
        self.setup_fleet()
        self.status = "Подключение..."
        connected_count = 0
        
        for d in self.drones:
            try:
                print(f"[Диспетчер] Подключение {d.drone_id}...")
                d.connect()
                connected_count += 1
                # 🔥 ВАЖНО: Даём дрону время на инициализацию
                time.sleep(2)
            except Exception as e:
                print(f"[Диспетчер] Не удалось подключить {d.drone_id}: {e}")
        
        if connected_count == 0:
            self.status = "Ошибка подключения"
            return
        
        self.status = "Запуск миссии..."
        print(f"[Диспетчер] Подключено {connected_count} дронов. Старт.")
        
        threads = []
        for d in self.drones:
            t = threading.Thread(target=d.execute_pattern, args=(self.pattern,), daemon=True)
            t.start()
            threads.append(t)
            # 🔥 Небольшая задержка между запусками потоков
            time.sleep(0.5)
        
        self.status = "Полёт"
        
        for t in threads:
            t.join()
        
        self.status = "Миссия завершена"
        print("[Диспетчер] Все дроны завершили работу.")

    def stop_all(self):
        print("[Диспетчер] Экстренная остановка запрошена.")
        self.status = "Остановка..."
        for d in self.drones:
            try:

                d.is_logging.clear()

                if d.drone is not None:
                    try:
                        d.drone.land()
                        time.sleep(2)
                        d.drone.disarm()
                    except Exception:
                        pass
            except Exception:
                pass
        self.status = "Остановлено"