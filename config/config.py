import json
import os
from typing import List, Dict, Any

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


DEFAULT_DRONE_SETTINGS = {
    "ip": "10.42.0.1",
    "port": 20556,
    "duration": 60.0,
    "alt": 1.0,
    "size": 1.0,
    "pattern": "hover",
    "reps": 1,
    "interval": 0.05,
    "no_fly": False
}

def load_drones() -> List[Dict[str, Any]]:
    """
    Загружает список дронов из config.json. 
    Если файла нет или он пустой, возвращает пустой список.
    """
    if not os.path.exists(CONFIG_FILE):
        return []
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    return data.get("drones", [])

def save_drones(drones: List[Dict[str, Any]]) -> None:
    """
    Полностью перезаписывает config.json переданным списком дронов.
    indent=4 делает файл красивым и читаемым для человека.
    """
    data = {"drones": drones}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_drone(drone_data: Dict[str, Any]) -> None:
    """
    Добавляет нового дрона в конец списка и сохраняет файл.
    Автоматически генерирует ID, если он не передан.
    """
    drones = load_drones()
    
    # Генерируем уникальный ID (drone_1, drone_2 и т.д.)
    new_id = f"drone_{len(drones) + 1}"
    drone_data["id"] = drone_data.get("id", new_id)
    
    drones.append(drone_data)
    save_drones(drones)

def remove_drone(drone_id: str) -> None:
    """
    Удаляет дрона из списка по его ID и сохраняет файл.
    """
    drones = load_drones()
    # Оставляем только тех дронов, чей ID не совпадает с удаляемым
    drones = [d for d in drones if d.get("id") != drone_id]
    save_drones(drones)

def update_drone(drone_id: str, updated_data: Dict[str, Any]) -> None:
    """
    Обновляет настройки существующего дрона по его ID.
    """
    drones = load_drones()
    for drone in drones:
        if drone.get("id") == drone_id:
            drone.update(updated_data)
            break
    save_drones(drones)

def get_default_settings() -> Dict[str, Any]:
    """
    Возвращает копию настроек по умолчанию (чтобы GUI мог заполнить ими пустые поля).
    """
    return DEFAULT_DRONE_SETTINGS.copy()