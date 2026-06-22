import argparse
import config


def parse():

    ap = argparse.ArgumentParser(description="Parser for flight experiment")

    '''
    tcp - Drone TCP address in format IP:PORT
    Used to connect to the Pioneer drone
    Default: 10.42.0.1:20556
    '''
    ap.add_argument(
        "--tcp",
        default=f"{config.DEFAULT_SETTINGS['ip']}:{config.DEFAULT_SETTINGS['port']}",
        help="drone TCP address (default 10.42.0.1:20556)"
    )

    '''
    duration - Experiment duration in seconds.
    Determines how long telemetry will be collected.
    Default: 60.0 seconds.
    '''
    ap.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="test time (default 60.0 sec.)"
    )

    '''
    alt - Flight altitude in metres.
    Used by all flight patterns.
    Default: 1.0 m.
    '''
    ap.add_argument(
        "--alt",
        type=float,
        default=1.0,
        help="flight altitude in metres (default 1.0 m)"
    )

    '''
    size - Size of the selected flight pattern.
    For example:
    square    -> side length
    rectangle -> width/height base size
    circle    -> radius or diameter (depends on implementation)
    figure8   -> overall pattern size

    Default: 1.0 m.
    '''
    ap.add_argument(
        "--size",
        type=float,
        default=1.0,
        help="pattern size in metres (default 1.0 m)"
    )

    '''
    hover      - Hold position at the current point.
    line       - Fly along a straight line.
    backforth  - Repeatedly fly between two points.
    square     - Fly a square-shaped path.
    rectangle  - Fly a rectangular path.
    triangle   - Fly a triangular path.
    circle     - Fly a circular path.
    ellipse    - Fly an elliptical path.
    figure8    - Fly a figure-eight trajectory.
    '''
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

    '''
    reps - Number of times to repeat the selected pattern.
    Default: 1 repetition.
    '''
    ap.add_argument(
        "--reps",
        type=int,
        default=1,
        help="pattern repetitions"
    )

    '''
    interval - Time between telemetry samples.
    Example:
    0.05 s = 20 Hz
    0.01 s = 100 Hz

    Default: 0.05 s.
    '''
    ap.add_argument(
        "--interval",
        type=float,
        default=0.05,
        help="log interval s (0.05 = 20 Hz)"
    )

    '''
    no_fly - Safe bench-test mode.
    The drone will not arm or take off.
    Only telemetry logging is performed.
    '''
    ap.add_argument(
        "--no_fly",
        action="store_true",
        help="do not arm/fly, only log sensors"
    )

    return ap.parse_args()