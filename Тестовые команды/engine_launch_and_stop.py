from pioneer_sdk2 import Pioneer, Event
from time import sleep

'''
Эта часть кода должна запускаться на Radxa,
 так как подписка на события работает только при локальном подключении к беспилотнику.
'''

test_function = lambda : print("Сработала подписка на события")

pioneer = Pioneer(tcp="10.42.0.1:20556", wait_callback=True, safety_command=True)
pioneer.subscribe(Event.ENGINE_STARTED, test_function)

try:
    print("Попытка запустить двигатели...")
    if not pioneer.arm():
        raise RuntimeError("Не удалось запустить двигатели")
    print("Двигатели успешно запущены!")

except RuntimeError:
    print("Не удалось запустить двигатели")

finally:
    pioneer.disarm()
    pioneer.close_connection
    print("Двигатели остановлены и соединение закрыто.")