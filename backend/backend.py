from pioneer_sdk2 import Pioneer


class DroneController:

    # Initialization
    def __init__(self, tcp: str):
        self.tcp = tcp
        self.drone = None


    # --tcp
    def connect(self):
        print(f"Connecting to {self.tcp}...")
        self.drone = Pioneer( tcp=self.tcp, logger=True)
        print("Connected")

    def close(self):
        if self.drone is None: return
        self.drone.close_connection()
        print("Connection closed")

    # telemetry
    def get_telemetry(self):
        return {
            "battery": self.drone.get_battery_status(),
            "orientation": self.drone.get_orientation(),
            "accel": self.drone.get_accel(),
            "gyro": self.drone.get_gyro(),
            "mag": self.drone.get_mag(),
            "altitude": self.drone.get_altitude(),
            "rpm": self.drone.get_motors_rpm(),
        }



