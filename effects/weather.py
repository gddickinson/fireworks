# effects/weather.py
import math
from typing import List, Optional, Tuple
import random
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient
from utils.physics import PhysicsUtils
from utils.math import MathUtils

from PyQt6.QtCore import Qt, QPointF, QRectF


class WeatherParticle:
    def __init__(self, x: float, y: float, speed: float, angle: float):
        self.x = x
        self.y = y
        self.speed = speed
        self.angle = angle
        self.active = True

class WeatherEffect:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.particles: List[WeatherParticle] = []

    def update(self):
        """Update particle positions - to be implemented by subclasses"""
        pass

    def draw(self, painter: QPainter):
        """Draw weather effect - to be implemented by subclasses"""
        pass

    def resize(self, width: int, height: int):
        """Update dimensions and regenerate particles if needed"""
        old_width, old_height = self.width, self.height
        self.width = width
        self.height = height
        # Regenerate particles for new dimensions
        old_particles = self.particles
        self.particles = []

        # Reposition existing particles to fit new dimensions
        for particle in old_particles:
            # Scale particle position to new dimensions
            particle.x = (particle.x / old_width) * width
            particle.y = (particle.y / old_height) * height
            if (0 <= particle.x <= width and
                0 <= particle.y <= height):
                self.particles.append(particle)

        # Add new particles if needed (top up to the previous count, never more)
        if len(self.particles) < len(old_particles):
            self.init_particles()
            del self.particles[len(old_particles):]

    def init_particles(self):
        """Initialize particles - to be implemented by subclasses"""
        pass



class RainEffect(WeatherEffect):
    def __init__(self, width: int, height: int, intensity: float = 1.0):
        super().__init__(width, height)
        self.intensity = intensity
        self.droplet_count = int(100 * intensity)
        self.init_particles()

    def init_particles(self):
        for _ in range(self.droplet_count):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            speed = random.uniform(10, 15)
            angle = math.pi * 0.25  # 45 degrees
            self.particles.append(WeatherParticle(x, y, speed, angle))

    def update(self):
        for particle in self.particles:
            if particle.active:
                particle.x -= particle.speed * math.cos(particle.angle)
                particle.y += particle.speed * math.sin(particle.angle)

                # Reset particle if it goes off screen
                if particle.y > self.height or particle.x < 0:
                    particle.x = random.uniform(0, self.width)
                    particle.y = 0

    def draw(self, painter: QPainter):
        painter.setPen(QPen(QColor(200, 200, 255, 150), 1))
        for particle in self.particles:
            if particle.active:
                start_x = particle.x
                start_y = particle.y
                end_x = start_x - 5 * math.cos(particle.angle)
                end_y = start_y + 5 * math.sin(particle.angle)
                painter.drawLine(int(start_x), int(start_y),
                               int(end_x), int(end_y))

class SnowEffect(WeatherEffect):
    def __init__(self, width: int, height: int, intensity: float = 1.0):
        super().__init__(width, height)
        self.intensity = intensity
        self.flake_count = int(50 * intensity)
        self.init_particles()
        self.wind_offset = 0
        self.wind_speed = 0.1

    def init_particles(self):
        for _ in range(self.flake_count):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            speed = random.uniform(1, 3)
            angle = math.pi / 2  # 90 degrees
            self.particles.append(WeatherParticle(x, y, speed, angle))

    def update(self):
        self.wind_offset += self.wind_speed
        for particle in self.particles:
            if particle.active:
                # Add gentle swaying motion
                sway = math.sin(particle.y * 0.05 + self.wind_offset) * 0.5
                particle.x += sway
                particle.y += particle.speed

                # Reset particle if it goes off screen
                if particle.y > self.height:
                    particle.x = random.uniform(0, self.width)
                    particle.y = 0

    def draw(self, painter: QPainter):
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        for particle in self.particles:
            if particle.active:
                painter.drawPoint(int(particle.x), int(particle.y))

class FogLayer:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.velocity = random.uniform(-0.5, 0.5)  # Horizontal movement
        self.opacity = random.uniform(0.2, 0.6)    # Layer transparency
        # Create some random control points for Bezier curves
        self.control_points = self._generate_control_points()

    def _generate_control_points(self) -> List[Tuple[float, float]]:
        """Generate random control points for creating natural fog shapes"""
        points = []
        num_points = 5
        for i in range(num_points):
            x = self.x + (i * self.width / (num_points - 1))
            y_offset = random.uniform(-self.height/4, self.height/4)
            points.append((x, self.y + y_offset))
        return points

    def update(self, width: int):
        """Update fog layer position and handle wrapping"""
        self.x += self.velocity

        # Wrap around screen edges (the control points jump with the layer)
        shift = self.velocity
        if self.velocity > 0 and self.x > width:
            shift += -self.width - self.x
            self.x = -self.width
        elif self.velocity < 0 and self.x + self.width < 0:
            shift += width - self.x
            self.x = width

        # Update control points
        for i in range(len(self.control_points)):
            x, y = self.control_points[i]
            self.control_points[i] = (x + shift, y)

class FogEffect(WeatherEffect):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self.fog_layers: List[FogLayer] = []
        self.time = 0
        self.init_layers()

    def init_layers(self):
        """Initialize multiple fog layers"""
        num_layers = 5
        layer_height = self.height / num_layers

        for i in range(num_layers):
            # Create overlapping layers
            layer_width = self.width * 1.5  # Make layers wider than screen
            x = random.uniform(-self.width/2, 0)  # Random starting position
            y = i * layer_height
            self.fog_layers.append(FogLayer(x, y, layer_width, layer_height))

    def update(self):
        """Update fog layer positions"""
        self.time += 0.01
        for layer in self.fog_layers:
            layer.update(self.width)

    def draw(self, painter: QPainter):
        """Draw the fog effect"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for layer in self.fog_layers:
            # Create fog path
            fog_path = QPainterPath()

            # Start at the leftmost point
            start_x = layer.x
            start_y = layer.y + layer.height/2
            fog_path.moveTo(start_x, start_y)

            # Add curves between control points
            for i in range(len(layer.control_points) - 1):
                x1, y1 = layer.control_points[i]
                x2, y2 = layer.control_points[i + 1]

                # Add some vertical oscillation based on time
                y1 += math.sin(self.time + i) * 5
                y2 += math.sin(self.time + i + 1) * 5

                # Create control points for quadratic curve
                ctrl_x = (x1 + x2) / 2
                ctrl_y = y1 + random.uniform(-10, 10)  # Add some randomness

                fog_path.quadTo(ctrl_x, ctrl_y, x2, y2)

            # Complete the path by closing the shape
            fog_path.lineTo(layer.x + layer.width, layer.y + layer.height)
            fog_path.lineTo(layer.x, layer.y + layer.height)
            fog_path.closeSubpath()

            # Create gradient for natural fog appearance
            gradient = QLinearGradient(
                layer.x, layer.y,
                layer.x, layer.y + layer.height
            )

            # Add gradient stops for more natural fog appearance
            fog_color = QColor(200, 200, 200)
            gradient.setColorAt(0, QColor(fog_color.red(),
                                        fog_color.green(),
                                        fog_color.blue(),
                                        int(0)))
            gradient.setColorAt(0.2, QColor(fog_color.red(),
                                          fog_color.green(),
                                          fog_color.blue(),
                                          int(255 * layer.opacity)))
            gradient.setColorAt(0.8, QColor(fog_color.red(),
                                          fog_color.green(),
                                          fog_color.blue(),
                                          int(255 * layer.opacity)))
            gradient.setColorAt(1, QColor(fog_color.red(),
                                        fog_color.green(),
                                        fog_color.blue(),
                                        int(0)))

            # Draw the fog layer
            painter.fillPath(fog_path, gradient)

    def resize(self, width: int, height: int):
        """Handle window resize"""
        scale_x = width / self.width
        scale_y = height / self.height
        super().resize(width, height)

        # Adjust fog layers for new dimensions
        for layer in self.fog_layers:

            layer.width *= scale_x
            layer.height *= scale_y
            layer.x *= scale_x
            layer.y *= scale_y

            # Update control points
            layer.control_points = [
                (x * scale_x, y * scale_y)
                for x, y in layer.control_points
            ]

        self.width = width
        self.height = height


class LightningBolt:
    def __init__(self, start_x: float, start_y: float, end_x: float, end_y: float):
        self.start = (start_x, start_y)
        self.end = (end_x, end_y)
        self.segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        self.branches: List['LightningBolt'] = []
        self.lifetime = random.randint(3, 6)  # Frames the bolt exists
        self.current_life = self.lifetime
        self.generate_path()

    def generate_path(self):
        """Generate a realistic lightning path with segments"""
        self.segments = []
        points = [self.start]
        current = self.start
        target = self.end

        while math.dist(current, target) > 10:
            # Calculate direction vector
            dx = target[0] - current[0]
            dy = target[1] - current[1]
            length = math.sqrt(dx * dx + dy * dy)

            # Normalize and scale
            dx /= length
            dy /= length
            step_length = random.uniform(20, 50)

            # Add randomness to direction
            deviation = random.uniform(-30, 30)
            angle = math.atan2(dy, dx) + math.radians(deviation)

            # Calculate new point
            new_x = current[0] + math.cos(angle) * step_length
            new_y = current[1] + math.sin(angle) * step_length
            new_point = (new_x, new_y)

            # Add segment
            self.segments.append((current, new_point))
            points.append(new_point)
            current = new_point

            # Possibly create a branch
            if random.random() < 0.2:  # 20% chance
                branch_length = length * random.uniform(0.3, 0.7)
                branch_angle = angle + math.radians(random.uniform(-45, 45))
                branch_end_x = current[0] + math.cos(branch_angle) * branch_length
                branch_end_y = current[1] + math.sin(branch_angle) * branch_length
                branch = LightningBolt(current[0], current[1], branch_end_x, branch_end_y)
                self.branches.append(branch)

        # Connect to end point
        self.segments.append((current, self.end))

class LightningEffect(WeatherEffect):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self.active_bolts: List[LightningBolt] = []
        self.flash_intensity = 0.0
        self.time_since_last = 0
        self.next_strike = random.uniform(50, 200)  # Frames until next strike

    def update(self):
        """Update lightning state"""
        self.time_since_last += 1

        # Update existing bolts
        for bolt in self.active_bolts[:]:
            bolt.current_life -= 1
            if bolt.current_life <= 0:
                self.active_bolts.remove(bolt)

        # Create new lightning when time
        if self.time_since_last >= self.next_strike:
            self.create_lightning()
            self.time_since_last = 0
            self.next_strike = random.uniform(50, 200)

        # Update flash effect
        if self.flash_intensity > 0:
            self.flash_intensity *= 0.9  # Fade out

    def create_lightning(self):
        """Create a new lightning bolt"""
        # Start from a random point at the top
        start_x = random.uniform(0, self.width)
        start_y = 0

        # End at a random point lower in the scene
        end_x = start_x + random.uniform(-200, 200)
        end_y = random.uniform(self.height * 0.5, self.height * 0.8)

        # Create the bolt
        bolt = LightningBolt(start_x, start_y, end_x, end_y)
        self.active_bolts.append(bolt)

        # Create flash effect
        self.flash_intensity = 1.0

    def draw(self, painter: QPainter):
        """Draw lightning effect"""
        # Draw overall flash
        if self.flash_intensity > 0:
            flash_color = QColor(255, 255, 255, int(60 * self.flash_intensity))
            painter.fillRect(
                QRectF(0, 0, self.width, self.height),
                flash_color
            )

        # Draw each bolt
        for bolt in self.active_bolts:
            self._draw_bolt(painter, bolt)

    def _draw_bolt(self, painter: QPainter, bolt: LightningBolt):
        """Draw a single lightning bolt and its branches"""
        # Calculate opacity based on remaining lifetime
        opacity = (bolt.current_life / bolt.lifetime) * 255

        # Draw main bolt
        for i, (start, end) in enumerate(bolt.segments):
            # Create gradient effect from center to edge
            thickness = 3 * (bolt.current_life / bolt.lifetime)

            # Core (bright white)
            painter.setPen(QPen(
                QColor(255, 255, 255, int(opacity)),
                thickness,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            ))
            painter.drawLine(
                int(start[0]), int(start[1]),
                int(end[0]), int(end[1])
            )

            # Outer glow (blue tint)
            painter.setPen(QPen(
                QColor(200, 225, 255, int(opacity * 0.5)),
                thickness * 2,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            ))
            painter.drawLine(
                int(start[0]), int(start[1]),
                int(end[0]), int(end[1])
            )

        # Draw branches
        for branch in bolt.branches:
            self._draw_bolt(painter, branch)
