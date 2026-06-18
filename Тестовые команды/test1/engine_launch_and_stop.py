from pioneer_sdk2 import Pioneer, Event
from time import sleep

'''
Чтобы исполнить код, нужно:
1) Вставить АКБ и дождаться wifi с именем  «RaZero-…..»
2) Подключиться к wifi с паролем geoscan123
3) Для доступа к функционалу модуля, введите в строку браузера IP-адрес и порт:
10.42.0.1:(9090 - главное меню, 2020 - Блочное программирование,
9999 - программирование в вс коде, 7777 - загрузка модели ИИ)

В Случае обычного запуска через локалку порт будет 20556
4) Подключение происходит по tcp="10.42.0.1:20556"
5) Дальше, чтобы команды все-так передавались коптеру, нужно открыть терминал
6) Если на винде и делаете впервые, нужно установить установить OpenSSH Server
7) Введите команду ssh pioneer@10.42.0.1
8) Введите пароль geoscan123
9) Подключение по SSH завершено!

Если вы используете Windows и получаете ответ «Connection closed by 10.42.0.1 port 22», 
то вам требуется включить правило брандмауэра с именем «OpenSSH-Server-In-TCP»
'''


def test_of_subscribe_function(*args):
    print("ENGINE_STARTED")
    print(args)

pioneer = Pioneer(tcp="10.42.0.1:20556", wait_callback=True, safety_command=True)
pioneer.subscribe(Event.ENGINE_STARTED, test_of_subscribe_function)

try:
    print("Попытка запустить двигатели...")
    if not pioneer.arm():
        raise RuntimeError("Не удалось запустить двигатели")

    sleep(3)
    print("Двигатели успешно запущены!")

except Exception as e:
    print(f"Ошибка: {e}")

finally:
    pioneer.disarm()
    pioneer.close_connection()
    print("Двигатели остановлены и соединение закрыто.")