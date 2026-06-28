from dataclasses import dataclass, field
from typing import List

@dataclass
class DroneConfig:
    ip: str
    port: int
    
    duration: float = 60.0
    alt: float = 1.0
    size: float = 1.0
    pattern: str = "hover"
    reps: int = 1
    interval: float = 0.05
    no_fly: bool = False

@dataclass
class FleetConfig:
    drones: List[DroneConfig] = field(default_factory=list)
    
    log_directory: str = "logs"
    use_gui: bool = True