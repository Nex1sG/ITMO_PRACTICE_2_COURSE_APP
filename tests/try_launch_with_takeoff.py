from pioneer_sdk2 import Pioneer
from time import sleep

pioneer = Pioneer(tcp="10.42.0.1:20556", wait_callback=True, safety_command=True)

def launch(pion):

    print("Запуск двигателей...")
    if not pion.arm(): raise RuntimeError("Не удалось запустить двигатели")
    print("Взлет...")

    if not pion.takeoff(): raise RuntimeError("Не удалось взлететь")
    print("Коптер в воздухе")
    sleep(3)
    print("Посадка...")

    if not pion.land(): raise RuntimeError("Не удалось выполнить посадку")
    print("Посадка завершена")

try:
    launch(pioneer)

except Exception as e:
    print(f"Ошибка: {e}")

finally:
    pioneer.disarm()
    pioneer.close_connection()