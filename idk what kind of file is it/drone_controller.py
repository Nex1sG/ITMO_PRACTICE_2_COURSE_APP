from pioneer_sdk2 import Pioneer
from backend.data_logger import DataLogger

class DroneController:

    def __init__(self, tcp: str):
        self.tcp = tcp    # format: "ip:port"
        self.drone = None


    def connect(self):
        print(f"Connecting to {self.tcp}...")
        self.drone = Pioneer( tcp=self.tcp, logger=True)
        print("Connected")


    def close(self):
        if self.drone is None: return
        self.drone.close_connection()
        print("Connection closed")


    def get_telemetry(self):
        return {
            "Заряд батареи": self.drone.get_battery_status(),
            "Ориентация в пространстве": self.drone.get_orientation(),
            "Ускорение с акселерометра": self.drone.get_accel(),
            "Угловая скорость (gyro)": self.drone.get_gyro(),
            "Магнитометр (mag)": self.drone.get_mag(),
            "Высота": self.drone.get_altitude(),
            "Обороты (rpm)": self.drone.get_motors_rpm()}



