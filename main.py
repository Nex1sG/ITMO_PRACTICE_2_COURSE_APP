from utils.parser import parse
from backend.fleet_manager import FleetManager
from config import config

from PySide6.QtWidgets import QApplication
from gui.realtime_plot import RealtimePlot

import sys
import threading


def main():
    args = parse()

    tcp_list = (
        config.get_drone_addresses()
        if args.use_all_drones
        else ["10.42.0.1:20556"][:args.n_drones]
    )

    fleet = FleetManager(
        tcp_list=tcp_list,
        alt=args.alt,
        size=args.size,
        reps=args.reps,
        interval=args.interval,
        pattern=args.pattern,
        duration=args.duration,
        no_fly=args.no_fly
    )

    # 1. СНАЧАЛА создаём Qt
    app = QApplication(sys.argv)

    # 2. Запускаем fleet В ФОНЕ
    fleet_thread = threading.Thread(target=fleet.run, daemon=True)
    fleet_thread.start()

    # 3. ждём пока drones появятся (важно)
    import time
    while not fleet.drones:
        time.sleep(0.1)

    # 4. берём первый контроллер
    controller = fleet.drones[0]

    # 5. создаём GUI
    window = RealtimePlot(controller.get_realtime_data)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()