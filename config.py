from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from PyQt6.QtGui import QColor

# RGB values of the default colours (Qt-free, also read by the web app in web/).
DEFAULT_FIREWORK_RGB = (255, 0, 0)
DEFAULT_BACKGROUND_RGB = (0, 0, 20)  # Very dark blue, better for fireworks display


def default_firework_color() -> QColor:
    from PyQt6.QtGui import QColor  # imported here so the physics constants load without Qt
    return QColor(*DEFAULT_FIREWORK_RGB)

def default_background_color() -> QColor:
    from PyQt6.QtGui import QColor
    return QColor(*DEFAULT_BACKGROUND_RGB)

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

    def __post_init__(self):
        if self.MIN_PARTICLES < 1:
            raise ValueError("MIN_PARTICLES must be at least 1")
        if self.MAX_PARTICLES < self.MIN_PARTICLES:
            raise ValueError("MAX_PARTICLES must be >= MIN_PARTICLES")
        if not (self.MIN_PARTICLES <= self.DEFAULT_PARTICLES <= self.MAX_PARTICLES):
            raise ValueError("DEFAULT_PARTICLES must be between MIN_PARTICLES and MAX_PARTICLES")
        if self.FRAME_RATE < 1 or self.FRAME_RATE > 240:
            raise ValueError("FRAME_RATE must be between 1 and 240")
        if not (0.0 <= self.SPAWN_RATE <= 1.0):
            raise ValueError("SPAWN_RATE must be between 0.0 and 1.0")
        if self.LAUNCH_SPEED_MIN > self.LAUNCH_SPEED_MAX:
            raise ValueError("LAUNCH_SPEED_MIN must be <= LAUNCH_SPEED_MAX")
        if self.PARTICLE_SPEED_MIN > self.PARTICLE_SPEED_MAX:
            raise ValueError("PARTICLE_SPEED_MIN must be <= PARTICLE_SPEED_MAX")

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

    def __post_init__(self):
        if self.WINDOW_WIDTH < self.MIN_WINDOW_WIDTH:
            raise ValueError("WINDOW_WIDTH must be >= MIN_WINDOW_WIDTH")
        if self.WINDOW_HEIGHT < self.MIN_WINDOW_HEIGHT:
            raise ValueError("WINDOW_HEIGHT must be >= MIN_WINDOW_HEIGHT")
