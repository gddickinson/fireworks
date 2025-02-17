# effects/particle_effects.py
import random
from typing import List, Optional
from PyQt6.QtGui import QPainter, QColor
from utils.physics import PhysicsUtils
from utils.color import ColorUtils

class SmokeParticle:
    def __init__(self, x: float, y: float, lifetime: int = 100):
        self.x = x
        self.y = y
        self.lifetime = lifetime
        self.current_life = lifetime
        self.size = random.uniform(2, 5)
        self.velocity_x = random.uniform(-0.5, 0.5)
        self.velocity_y = random.uniform(-0.5, 0)
        self.active = True

class SmokeEffect:
    def __init__(self, x: float, y: float, particle_count: int = 20):
        self.particles: List[SmokeParticle] = []
        self.x = x
        self.y = y
        self.particle_count = particle_count
        self.init_particles()

    def init_particles(self):
        for _ in range(self.particle_count):
            self.particles.append(SmokeParticle(self.x, self.y))

    def update(self):
        for particle in self.particles:
            if particle.active:
                particle.x += particle.velocity_x
                particle.y += particle.velocity_y
                particle.current_life -= 1
                particle.active = particle.current_life > 0

    def draw(self, painter: QPainter):
        for particle in self.particles:
            if particle.active:
                opacity = particle.current_life / particle.lifetime
                color = QColor(150, 150, 150, int(100 * opacity))
                painter.setPen(color)
                painter.setBrush(color)
                painter.drawEllipse(
                    int(particle.x - particle.size/2),
                    int(particle.y - particle.size/2),
                    int(particle.size),
                    int(particle.size)
                )
