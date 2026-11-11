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
        self.pattern = None  # explosion shape (models/patterns.py), set by the canvas

    def explode(self) -> None:
        self.exploded = True
        if self.pattern is not None and self._explode_pattern():
            return
        for _ in range(self.particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(
                FireworkConfig.PARTICLE_SPEED_MIN,
                FireworkConfig.PARTICLE_SPEED_MAX
            )
            self.particles.append(Particle(self.x, self.y, angle, speed, self.color,
                                           gravity=self.gravity))

    def _explode_pattern(self) -> bool:
        """One particle per pattern point, moving outwards so the burst grows into the shape; the outermost point
        moves at PARTICLE_SPEED_MAX x pattern scale. Returns False (plain burst) if the pattern has no points."""
        points = self.pattern.get_points(self.x, self.y)
        radius = max((math.hypot(px - self.x, py - self.y) for px, py in points), default=0.0)
        if not points or radius == 0:
            return False
        k = FireworkConfig.PARTICLE_SPEED_MAX * self.pattern.scale / radius
        for px, py in points:
            dx, dy = px - self.x, py - self.y
            self.particles.append(Particle(self.x, self.y, math.atan2(dy, dx), math.hypot(dx, dy) * k,
                                           self.color, gravity=self.gravity))
        return True

    def update(self) -> bool:
        if not self.exploded:
            self.y += self.velocity_y
            self.velocity_y += self.gravity
            if self.velocity_y >= 0:
                self.explode()
        else:
            self.particles = [p for p in self.particles if p.update()]
        return len(self.particles) > 0 or not self.exploded
