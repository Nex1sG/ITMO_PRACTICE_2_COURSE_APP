from collections import deque
from pioneer_sdk2 import Pioneer
class RealtimeTelemetryProcessor:
    def __init__(self, buffer_size=300):
        self.buffer_size = buffer_size

        # time
        self.t = deque(maxlen=buffer_size)

        # position
        self.x = deque(maxlen=buffer_size)
        self.y = deque(maxlen=buffer_size)
        self.z = deque(maxlen=buffer_size)

        # velocity
        self.vx = deque(maxlen=buffer_size)
        self.vy = deque(maxlen=buffer_size)
        self.vz = deque(maxlen=buffer_size)

        # accel
        self.ax = deque(maxlen=buffer_size)
        self.ay = deque(maxlen=buffer_size)
        self.az = deque(maxlen=buffer_size)

        # battery
        self.battery = deque(maxlen=buffer_size)

        # optional callbacks (GUI, plots)
        self.callbacks = []

    # -------------------------
    # core update method
    # -------------------------
    def update(self, log: dict):
        self.t.append(log.get("t"))

        self.x.append(log.get("x"))
        self.y.append(log.get("y"))
        self.z.append(log.get("z"))

        self.vx.append(log.get("vx"))
        self.vy.append(log.get("vy"))
        self.vz.append(log.get("vz"))

        self.ax.append(log.get("ax"))
        self.ay.append(log.get("ay"))
        self.az.append(log.get("az"))

        self.battery.append(log.get("battery"))

        # notify GUI
        for cb in self.callbacks:
            try:
                cb(log)
            except Exception as e:
                print(f"[RealtimeTelemetryProcessor] callback error: {e}")

    # -------------------------
    # GUI access
    # -------------------------
    def get_series(self):
        return {
            "t": list(self.t),

            "position": {
                "x": list(self.x),
                "y": list(self.y),
                "z": list(self.z),
            },

            "velocity": {
                "x": list(self.vx),
                "y": list(self.vy),
                "z": list(self.vz),
            },

            "accel": {
                "x": list(self.ax),
                "y": list(self.ay),
                "z": list(self.az),
            },

            "battery": list(self.battery),
        }

    def subscribe(self, callback):
        self.callbacks.append(callback)