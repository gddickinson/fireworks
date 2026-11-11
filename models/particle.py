# models/particle.py
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from config import FireworkConfig

if TYPE_CHECKING:
    from PyQt6.QtGui import QColor

class Particle:
    def __init__(self, x: float, y: float, angle: float, speed: float,
                 color: QColor, lifetime: int = 100, gravity: float | None = None):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.color = color
        self.lifetime = lifetime
        self.current_life = lifetime
        self.gravity = FireworkConfig.GRAVITY if gravity is None else gravity
        self.velocity_x = math.cos(angle) * speed
        self.velocity_y = math.sin(angle) * speed

    def update(self) -> bool:
        self.velocity_y += self.gravity
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.current_life -= 1
        return self.current_life > 0

    def get_color(self) -> QColor:
        from PyQt6.QtGui import QColor  # imported here so the physics loads without Qt (web app)
        fade = self.current_life / self.lifetime
        return QColor(
            self.color.red(),
            self.color.green(),
            self.color.blue(),
            int(255 * fade)
        )
