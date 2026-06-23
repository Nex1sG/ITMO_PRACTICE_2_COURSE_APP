from utils.parser import parse
from backend.fleet_manager import FleetManager
from config import config


def main():
    args = parse()

    if args.use_all_drones:
        tcp_list = config.get_drone_addresses()
    else:
        try:
            # all_addresses = config.get_drone_addresses()
            all_addresses = ["10.42.0.1:20556"]
            tcp_list = all_addresses[:args.n_drones]
        except FileNotFoundError:
            tcp_list = [args.tcp]

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

    fleet.run()


if __name__ == "__main__":
    main()