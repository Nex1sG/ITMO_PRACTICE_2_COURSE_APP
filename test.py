from pioneer_sdk2 import Pioneer
import time

# Если скрипт выполняется на самой Radxa:
drone = Pioneer(
    tcp="127.0.0.1:20556",
    wait_callback=True,
    safety_command=True
)

try:
    print("ARM...")
    if not drone.arm():
        raise RuntimeError("Не удалось запустить моторы")

    print("TAKEOFF...")
    if not drone.takeoff():
        raise RuntimeError("Не удалось взлететь")

    print("Зависание 5 секунд")
    time.sleep(5)

    print("LAND...")
    drone.land()

finally:
    drone.close()