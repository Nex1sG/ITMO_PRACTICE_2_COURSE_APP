import time
import threading
from threading import Barrier
from backend.drone_controller import DroneController

class FleetManager:
    def __init__(self, tcp_list, alt, size, reps, interval, pattern, duration, no_fly):
        print(f"[FLEET] Инициализация FleetManager...")
        print(f"[FLEET] Параметры: tcp_list={tcp_list}, alt={alt}, pattern={pattern}")
        print(f"[FLEET] size={size}, reps={reps}, interval={interval}, no_fly={no_fly}")
        
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
        self.threads = []
        self.barrier = None
        self.is_running = False
        self.status = "Инициализация"
        
        print(f"[FLEET] FleetManager инициализирован")

    def setup_fleet(self):
        print(f"[FLEET] Настройка флота из {len(self.tcp_list)} дронов...")
        self.status = "Настройка"
        
        for i, tcp in enumerate(self.tcp_list):
            print(f"[FLEET] Создание дрона {i+1}/{len(self.tcp_list)}: {tcp}")
            drone = DroneController(
                tcp=tcp,
                alt=self.alt,
                size=self.size,
                reps=self.reps,
                interval=self.interval,
                no_fly=self.no_fly
            )
            drone.drone_id = f"drone_{i+1}"
            self.drones.append(drone)
            print(f"[FLEET] Дрон {drone.drone_id} создан")
        
        print(f"[FLEET] Создание барьера синхронизации на {len(self.drones)} потоков")
        self.barrier = Barrier(len(self.drones))
        
        for drone in self.drones:
            drone.barrier = self.barrier
        
        self.status = "Готов к запуску"
        print(f"[FLEET] Флот настроен. Всего дронов: {len(self.drones)}")

    def connect_all(self):
        print(f"[FLEET] Подключение всех дронов...")
        self.status = "Подключение"
        connected = 0
        
        for drone in self.drones:
            print(f"[FLEET] Подключение {drone.drone_id}...")
            try:
                if drone.connect():
                    connected += 1
                    print(f"[FLEET] {drone.drone_id} подключён успешно")
            except Exception as e:
                print(f"[FLEET] Ошибка подключения {drone.drone_id}: {e}")
        
        print(f"[FLEET] Подключено {connected}/{len(self.drones)} дронов")
        self.status = f"Подключено {connected} дронов"
        return connected

    def start_all(self):
        print(f"[FLEET] Запуск всех дронов...")
        self.status = "Запуск"
        self.is_running = True
        
        for drone in self.drones:
            print(f"[FLEET] Создание потока для {drone.drone_id}...")
            t = threading.Thread(
                target=drone.execute_pattern,
                args=(self.pattern,),
                daemon=True
            )
            self.threads.append(t)
            print(f"[FLEET] Поток для {drone.drone_id} создан")
        
        print(f"[FLEET] Запуск {len(self.threads)} потоков...")
        for t in self.threads:
            t.start()
        
        print(f"[FLEET] Все потоки запущены")
        self.status = "Полёт"

    def stop_all(self):
        print(f"[FLEET] Экстренная остановка запрошена...")
        self.status = "Остановка"
        self.is_running = False
        
        for drone in self.drones:
            print(f"[FLEET] Остановка {drone.drone_id}...")
            try:
                drone.is_logging.clear()
                if drone.drone:
                    print(f"[FLEET] {drone.drone_id} - посадка")
                    drone.drone.land()
                    time.sleep(2)
                    print(f"[FLEET] {drone.drone_id} - дизарминг")
                    drone.drone.disarm()
            except Exception as e:
                print(f"[FLEET] Ошибка остановки {drone.drone_id}: {e}")
        
        print(f"[FLEET] Остановка завершена")
        self.status = "Остановлено"

    def run(self):
        print(f"[FLEET] === ЗАПУСК ФЛОТА ===")
        print(f"[FLEET] Начало выполнения run()")
        
        try:
            self.setup_fleet()
            print(f"[FLEET] Setup complete")
            
            connected = self.connect_all()
            print(f"[FLEET] Connected: {connected}")
            
            if connected == 0:
                print(f"[FLEET] ОШИБКА: Ни один дрон не подключён!")
                self.status = "Ошибка подключения"
                return
            
            print(f"[FLEET] Подключено {connected} дронов. Старт.")
            self.start_all()
            
            print(f"[FLEET] Ожидание завершения потоков...")
            for t in self.threads:
                t.join()
            
            print(f"[FLEET] Все дроны завершили работу.")
            self.status = "Завершено"
            
        except Exception as e:
            print(f"[FLEET] КРИТИЧЕСКАЯ ОШИБКА: {e}")
            self.status = f"Ошибка: {e}"
        finally:
            print(f"[FLEET] Закрытие соединений...")
            for drone in self.drones:
                drone.close()
            print(f"[FLEET] === ЗАВЕРШЕНИЕ РАБОТЫ ФЛОТА ===")