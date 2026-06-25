import json

DEFAULT_SETTINGS = {
    "ip": "10.42.0.1",
    "port": 20556
}

def get_drone_addresses():

    with open("config.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    drones_data = data["drones"]
    
    addresses = []
    for drone_name, drone_settings in drones_data.items():

        ip = drone_settings["ip"]
        port = drone_settings["port"]
        
        addresses.append(f"{ip}:{port}")
        
    return addresses