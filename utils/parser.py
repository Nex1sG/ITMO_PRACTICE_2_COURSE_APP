import argparse
from config import config


def parse():
    ap = argparse.ArgumentParser(description="Parser for flight experiment")

    try:
        addresses = config.get_drone_addresses()
        default_tcp = addresses[0] if addresses else f"{config.DEFAULT_SETTINGS['ip']}:{config.DEFAULT_SETTINGS['port']}"
    except (FileNotFoundError, KeyError):
        default_tcp = f"{config.DEFAULT_SETTINGS['ip']}:{config.DEFAULT_SETTINGS['port']}"

    ap.add_argument(
        "--tcp",
        default=default_tcp,
        help=f"drone TCP address (default {default_tcp})"
    )

    ap.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="test time (default 60.0 sec.)"
    )

    ap.add_argument(
        "--alt",
        type=float,
        default=1.0,
        help="flight altitude in metres (default 1.0 m)"
    )

    ap.add_argument(
        "--size",
        type=float,
        default=1.0,
        help="pattern size in metres (default 1.0 m)"
    )

    ap.add_argument(
        "--pattern",
        choices=[
            "hover", "line", "backforth",
            "square", "rectangle", "triangle",
            "circle", "ellipse", "figure8"
        ],
        default="hover",
        help="flight trajectory pattern"
    )

    ap.add_argument(
        "--reps",
        type=int,
        default=1,
        help="pattern repetitions"
    )

    ap.add_argument(
        "--interval",
        type=float,
        default=0.05,
        help="log interval s (0.05 = 20 Hz)"
    )

    ap.add_argument(
        "--no_fly",
        action="store_true",
        help="do not arm/fly, only log sensors"
    )

    ap.add_argument(
        "--n_drones",
        type=int,
        default=1,
        help="number of drones to use from config (default 1)"
    )

    ap.add_argument(
        "--use_all_drones",
        action="store_true",
        help="use all drones from config.json"
    )

    return ap.parse_args()