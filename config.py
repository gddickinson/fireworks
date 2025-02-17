from dataclasses import dataclass, field
from typing import Callable
from PyQt6.QtGui import QColor

def default_firework_color() -> QColor:
    return QColor(255, 0, 0)

def default_background_color() -> QColor:
    return QColor(0, 0, 20)  # Very dark blue, better for fireworks display

@dataclass
class FireworkConfig:
    MIN_PARTICLES: int = 20
    MAX_PARTICLES: int = 200
    DEFAULT_PARTICLES: int = 50
    DEFAULT_COLOR: QColor = field(default_factory=default_firework_color)
    GRAVITY: float = 0.1
    LAUNCH_SPEED_MIN: float = 8.0
    LAUNCH_SPEED_MAX: float = 12.0
    PARTICLE_SPEED_MIN: float = 2.0
    PARTICLE_SPEED_MAX: float = 5.0
    SPAWN_RATE: float = 0.1  # 10% chance per frame
    FRAME_RATE: int = 60

@dataclass
class DisplayConfig:
    WINDOW_WIDTH: int = 800
    WINDOW_HEIGHT: int = 600
    WINDOW_TITLE: str = "Fireworks Simulator"
    BACKGROUND_COLOR: QColor = field(default_factory=default_background_color)
    MIN_WINDOW_WIDTH: int = 400
    MIN_WINDOW_HEIGHT: int = 300
    DEFAULT_WINDOW_X: int = 100
    DEFAULT_WINDOW_Y: int = 100
