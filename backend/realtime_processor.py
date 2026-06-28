from collections import deque
import threading

class RealtimeTelemetryProcessor:
    def __init__(self, buffer_size=300):
        self.buffer_size = buffer_size
        self._lock = threading.Lock()
        
        self.t = deque(maxlen=buffer_size)
        self.x = deque(maxlen=buffer_size)
        self.y = deque(maxlen=buffer_size)
        self.z = deque(maxlen=buffer_size)
        self.vx = deque(maxlen=buffer_size)
        self.vy = deque(maxlen=buffer_size)
        self.vz = deque(maxlen=buffer_size)
        self.ax = deque(maxlen=buffer_size)
        self.ay = deque(maxlen=buffer_size)
        self.az = deque(maxlen=buffer_size)
        self.battery = deque(maxlen=buffer_size)
        self.callbacks = []

    def update(self, log: dict):
        with self._lock:
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
        
        for cb in self.callbacks:
            try:
                cb(log)
            except Exception as e:
                print(f"[RealtimeTelemetryProcessor] callback error: {e}")

    def get_series(self):
        with self._lock:
            return {
                "t": list(self.t),
                "position": {"x": list(self.x), "y": list(self.y), "z": list(self.z)},
                "velocity": {"x": list(self.vx), "y": list(self.vy), "z": list(self.vz)},
                "accel": {"x": list(self.ax), "y": list(self.ay), "z": list(self.az)},
                "battery": list(self.battery),
            }

    def subscribe(self, callback):
        self.callbacks.append(callback)