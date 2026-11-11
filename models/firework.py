# models/firework.py
from __future__ import annotations

import random
import math
from typing import TYPE_CHECKING, List
from models.particle import Particle
from config import DEFAULT_LAUNCH_SPEED, FireworkConfig

if TYPE_CHECKING:
    from PyQt6.QtGui import QColor

class Firework:
    def __init__(self, x: float, y: float, color: QColor,
                 particle_count: int = FireworkConfig.DEFAULT_PARTICLES,
                 gravity: float | None = None, launch_speed: float | None = None):
        self.x = x
        self.y = y
        self.color = color
        self.particles: List[Particle] = []
        self.exploded = False
        self.velocity_y = -random.uniform(
            FireworkConfig.LAUNCH_SPEED_MIN,
            FireworkConfig.LAUNCH_SPEED_MAX
        )
        # Launch Speed control: DEFAULT_LAUNCH_SPEED keeps the configured range, other values scale it
        if launch_speed is not None and launch_speed != DEFAULT_LAUNCH_SPEED:
            self.velocity_y *= launch_speed / DEFAULT_LAUNCH_SPEED
        self.gravity = FireworkConfig.GRAVITY if gravity is None else gravity
        self.particle_count = particle_count

    def explode(self) -> None:
        self.exploded = True
        for _ in range(self.particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(
                FireworkConfig.PARTICLE_SPEED_MIN,
                FireworkConfig.PARTICLE_SPEED_MAX
            )
            self.particles.append(Particle(self.x, self.y, angle, speed, self.color,
                                           gravity=self.gravity))

    def update(self) -> bool:
        if not self.exploded:
            self.y += self.velocity_y
            self.velocity_y += self.gravity
            if self.velocity_y >= 0:
                self.explode()
        else:
            self.particles = [p for p in self.particles if p.update()]
        return len(self.particles) > 0 or not self.exploded
