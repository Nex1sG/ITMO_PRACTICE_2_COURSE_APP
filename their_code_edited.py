
#ГЛЕЕЕЕЕЕБ
#я тут захардкодил внешний файл в код, чтобы код работал без него
#также я убрал потребность в библиотеке telemetry, так как он у меня не работал (и не скачивался)







"""
run_experiment.py — repeatable data-collection flights for the vibration ML study.
It connects to the Pioneer ONCE and, in a single thread, both commands the drone
and logs every sensor channel. 
!!  SAFETY  !!
- This ARMS and FLIES a real drone. Use a clear, netted area; props can injure.
- Indoor flights need a working local nav system (LPS / optical flow).
- On any error or Ctrl+C the script lands, disarms, and turns the vibrator off.
"""
import os
import sys
import time
import math
import signal
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_STOP = False

def _request_stop(signum=None, frame=None):
    global _STOP
    if not _STOP:
        print("\n[INFO] Stop requested -- finishing this step and landing…", flush=True)
        _STOP = True

# ---------- vibrator (over SSH) ----------
def set_vibrator(settings, on):
    """Turn the Radxa vibration motor fully on/off via SSH (best-effort)."""
    try:
        from telemetry.radxa import _make_client
    except Exception as e:
        print(f"[WARN] vibrator control unavailable: {e}")
        return

    action = "on" if on else "off"
    script = settings.get("remote_motor_script", "~/vibration_motor.py")
    
    try:
        client = _make_client(settings, timeout=6.0)
        stdin, out, _err = client.exec_command(f"sudo -S python3 {script} {action}")
        stdin.write(settings["ssh_password"] + "\n")
        stdin.flush()
        out.channel.recv_exit_status()
        client.close()
        print(f"[OK] vibrator {action.upper()}")
    except Exception as e:
        print(f"[WARN] could not set vibrator {action}: {e}")

# ---------- sensor read ----------
def read_sample(drone):
    s = {}
    o = drone.get_orientation()
    if o:
        s["roll"], s["pitch"], s["yaw"] = o
        
    b = drone.get_battery_status()
    if b:
        if b[0] is not None:
            s["battery"] = b[0]
        if len(b) > 1 and b[1] is not None:
            s["batt_temp"] = b[1]
            
    alt = drone.get_dist_sensor_data()
    if alt is None:
        alt = drone.get_altitude()
    if alt is not None:
        s["altitude"] = alt
        
    a = drone.get_accel()
    if a:
        s["ax"], s["ay"], s["az"] = a
        
    g = drone.get_gyro()
    if g:
        s["gx"], s["gy"], s["gz"] = g
        
    m = drone.get_mag()
    if m:
        s["mx"], s["my"], s["mz"] = m
        
    s["rpm"] = drone.get_motors_rpm()
    s["mode"] = "EXPERIMENT"
    return s

# ---------- flight patterns (local LPS coordinates, metres) ----------
def square_path(side, alt):
    h = side / 2.0
    return [(0.0, 0.0, alt),
            (h, h, alt), (h, -h, alt), (-h, -h, alt), (-h, h, alt), (h, h, alt),
            (0.0, 0.0, alt)]

def figure8_path(size, alt):
    h = size / 2.0
    pts = [(0.0, 0.0, alt)]
    for k in range(1, 17):
        th = 2 * math.pi * k / 16
        pts.append((h * math.sin(2 * th), h * math.sin(th), alt))
    pts.append((0.0, 0.0, alt))
    return pts

def path_for(pattern, size, alt):
    if pattern == "square":
        return square_path(size, alt)
    if pattern == "figure8":
        return figure8_path(size, alt)
    return [(0.0, 0.0, alt)]

def _sample(drone, vib_on):
    s = read_sample(drone)
    s["motor_on"] = vib_on
    s["motor_strength"] = 100 if vib_on else 0
    # Запись в CSV удалена. Данные просто считываются.
    return s

def log_for(drone, vib_on, seconds, interval):
    """Hold position and log for `seconds` (hover / bench)."""
    end = time.time() + seconds
    nxt = time.perf_counter()
    while time.time() < end and not _STOP:
        _sample(drone, vib_on)
        nxt += interval
        sl = nxt - time.perf_counter()
        if sl > 0:
            time.sleep(sl)
        else:
            nxt = time.perf_counter()

def fly_leg(drone, x, y, z, vib_on, interval, max_t=12.0):
    """Fly to (x,y,z) while logging; return when reached, timed out, or stopped."""
    drone.go_to_local_point(x, y, z)
    end = time.time() + max_t
    nxt = time.perf_counter()
    while time.time() < end and not _STOP:
        _sample(drone, vib_on)
        if drone.point_reached():
            return
        nxt += interval
        sl = nxt - time.perf_counter()
        if sl > 0:
            time.sleep(sl)
        else:
            nxt = time.perf_counter()

def smooth_land(drone, x, y, alt, step=0.3, floor=0.4):
    """Descend gradually to `floor` metres before the final landing."""
    print("[INFO] Smooth descent…", flush=True)
    z = max(alt, floor)
    while z > floor:
        z = max(floor, z - step)
        drone.go_to_local_point(x, y, z)
        t0 = time.time()
        while time.time() - t0 < 1.8:
            if drone.point_reached():
                break
            time.sleep(0.1)
    drone.land()
    drone.disarm()

def main():
    ap = argparse.ArgumentParser(description="Vibration-ML data-collection flight.")
    ap.add_argument("--tcp", default="10.42.0.1:20556", help="drone TCP address")
    ap.add_argument("--duration", type=float, default=120.0, help="logging/hover seconds")
    ap.add_argument("--alt", type=float, default=1.0, help="flight altitude (m)")
    ap.add_argument("--size", type=float, default=1.0, help="pattern size in m")
    ap.add_argument("--pattern", choices=["hover", "square", "figure8"], default="hover")
    ap.add_argument("--reps", type=int, default=1, help="pattern repetitions")
    ap.add_argument("--interval", type=float, default=0.05, help="log interval s")
    ap.add_argument("--vibrator", choices=["off", "on"], default="off", help="vibrator state")
    ap.add_argument("--no-fly", action="store_true", help="do NOT arm/fly")
    args = ap.parse_args()

    # Hardcoded settings replacing config module
    settings = {
        "ip": "10.42.0.1",
        "port": "20556",
        "ssh_password": "geoscan123",
        "remote_motor_script": "~/vibration_motor.py"
    }

    vib_on = args.vibrator == "on"
    
    from pioneer_sdk2 import Pioneer
    print(f"[INFO] Connecting to drone at {args.tcp} …")
    drone = Pioneer(tcp=args.tcp, logger=True)

    print(f"[INFO] Condition: vibrator {'ON' if vib_on else 'OFF'} | "
          f"pattern {args.pattern} | {'NO-FLY' if args.no_fly else 'FLY'}")

    signal.signal(signal.SIGINT, _request_stop)
    try:
        signal.signal(signal.SIGBREAK, _request_stop)
    except (AttributeError, ValueError):
        pass

    landed = False
    try:
        if vib_on:
            set_vibrator(settings, True)
            time.sleep(0.5)

        if args.no_fly:
            print(f"[INFO] Bench logging for {args.duration:.0f}s … (Ctrl+C to stop)")
            log_for(drone, vib_on, args.duration, args.interval)
        else:
            print("[INFO] ARM + TAKEOFF …  (Ctrl+C = stop & land)")
            if not drone.arm():
                raise RuntimeError("arm failed — check nav system / safety")
            drone.takeoff()
            fly_leg(drone, 0.0, 0.0, args.alt, vib_on, args.interval)
            
            if args.pattern == "hover":
                log_for(drone, vib_on, args.duration, args.interval)
            else:
                path = path_for(args.pattern, args.size, args.alt)
                for _ in range(max(1, args.reps)):
                    if _STOP:
                        break
                    for (x, y, z) in path:
                        if _STOP:
                            break
                        fly_leg(drone, x, y, z, vib_on, args.interval)
                        
            print("[INFO] LANDING …")
            smooth_land(drone, 0.0, 0.0, args.alt)
            landed = True
            
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        try:
            if not args.no_fly and not landed:
                drone.land()
                drone.disarm()
        except Exception:
            pass
            
        if vib_on:
            set_vibrator(settings, False)
            
        try:
            drone.close_connection()
        except Exception:
            pass

if __name__ == "__main__":
    main()