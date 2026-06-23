# from pioneer_sdk2 import Pioneer
# drone = Pioneer(tcp="10.42.0.1:20556")
# print([m for m in dir(drone) if not m.startswith('_')])
from pioneer_sdk2 import Pioneer
import time

drone = Pioneer(tcp="10.42.0.1:20556")
time.sleep(2)  # Дайте дрону время на инициализацию

print("=== ДИАГНОСТИКА ДРОНА ===")
print(f"Батарея: {drone.get_battery_status()}%")
print(f"Высота: {drone.get_altitude()} м")
print(f"Позиция (LPS): {drone.get_local_position_lps()}")
print(f"Статус навигации: {drone.get_nav_status_lps()}")
print(f"Состояние полета: {drone.get_fly_state()}")
print(f"IMU статус: {drone.get_accel()}, {drone.get_gyro()}")
print(f"Время полета: {drone.flight_time()} сек")
print("========================")