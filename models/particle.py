# models/particle.py
import math
from PyQt6.QtGui import QColor
from config import FireworkConfig

class Particle:
    def __init__(self, x: float, y: float, angle: float, speed: float,
                 color: QColor, lifetime: int = 100):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.color = color
        self.lifetime = lifetime
        self.current_life = lifetime
        self.gravity = FireworkConfig.GRAVITY
        self.velocity_x = math.cos(angle) * speed
        self.velocity_y = math.sin(angle) * speed

    def update(self) -> bool:
        self.velocity_y += self.gravity
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.current_life -= 1
        return self.current_life > 0

    def get_color(self) -> QColor:
        fade = self.current_life / self.lifetime
        return QColor(
            self.color.red(),
            self.color.green(),
            self.color.blue(),
            int(255 * fade)
        )
