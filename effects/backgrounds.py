# effects/backgrounds.py
import random
from typing import Optional, Tuple, List
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath, QPen, QBrush
from PyQt6.QtCore import Qt, QPointF, QRectF
import math

from .mountains import MountainsBackground

class Background:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def draw(self, painter: QPainter):
        """Draw background - to be implemented by subclasses"""
        pass

class NightSkyBackground(Background):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self.stars = [(random.uniform(0, width), random.uniform(0, height * 0.7))
                     for _ in range(200)]
        self.star_brightness = [random.uniform(0.3, 1.0) for _ in range(200)]

    def draw(self, painter: QPainter):
        # Draw sky gradient
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, QColor(0, 0, 40))  # Dark blue at top
        gradient.setColorAt(1, QColor(20, 20, 60))  # Lighter blue at bottom
        painter.fillRect(0, 0, self.width, self.height, gradient)

        # Draw stars
        for (x, y), brightness in zip(self.stars, self.star_brightness):
            color = QColor(255, 255, 255, int(255 * brightness))
            painter.setPen(color)
            painter.drawPoint(int(x), int(y))

class CityscapeBackground(Background):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self.buildings = self.generate_buildings()
        self.windows = self.generate_windows()

    def generate_buildings(self) -> List[Tuple[int, int, int, int]]:
        buildings = []
        x = 0
        while x < self.width:
            width = random.randint(40, 100)
            height = random.randint(100, 300)
            buildings.append((x, self.height - height, width, height))
            x += width
        return buildings

    def generate_windows(self) -> List[Tuple[int, int, int, int]]:
        windows = []
        for building in self.buildings:
            x, y, width, height = building
            for floor in range(int(height/20)):
                for window in range(int(width/15)):
                    if random.random() < 0.7:  # 70% chance of window being lit
                        window_x = x + window * 15 + 5
                        window_y = y + floor * 20 + 5
                        windows.append((window_x, window_y, 10, 15))
        return windows

    def draw(self, painter: QPainter):
        # Draw sky gradient
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, QColor(0, 0, 40))
        gradient.setColorAt(1, QColor(20, 20, 60))
        painter.fillRect(0, 0, self.width, self.height, gradient)

        # Draw buildings
        for building in self.buildings:
            painter.fillRect(*building, QColor(30, 30, 40))

        # Draw windows
        for window in self.windows:
            painter.fillRect(*window, QColor(255, 255, 150, 100))

class BeachBackground:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.stars = self._generate_stars()
        self.waves = self._generate_waves()
        self.palm_trees = self._generate_palm_trees()
        self.time = 0  # For wave animation

    def _generate_stars(self) -> List[Tuple[float, float, float]]:
        """Generate random stars with positions and brightness"""
        stars = []
        star_count = int((self.width * self.height) / 2000)

        for _ in range(star_count):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height * 0.6)  # Only in sky
            brightness = random.uniform(0.3, 1.0)
            stars.append((x, y, brightness))
        return stars

    def _generate_waves(self) -> List[List[Tuple[float, float]]]:
        """Generate multiple wave lines"""
        waves = []
        wave_count = 5
        wave_height = self.height * 0.1
        base_y = self.height * 0.7  # Water line

        for i in range(wave_count):
            wave = []
            segments = 20
            for j in range(segments + 1):
                x = (j / segments) * self.width
                y = base_y + (i * wave_height)
                wave.append((x, y))
            waves.append(wave)
        return waves

    def _generate_palm_trees(self) -> List[Tuple[float, float, float]]:
        """Generate palm tree positions and sizes"""
        trees = []
        tree_count = random.randint(3, 5)

        for _ in range(tree_count):
            x = random.uniform(0, self.width)
            y = self.height * 0.7  # At water line
            size = random.uniform(0.8, 1.2)  # Size variation
            trees.append((x, y, size))
        return trees

    def draw(self, painter: QPainter):
        """Draw the complete beach scene"""
        # Sky gradient
        sky_gradient = QLinearGradient(0, 0, 0, self.height * 0.7)
        sky_gradient.setColorAt(0, QColor(0, 0, 40))
        sky_gradient.setColorAt(0.5, QColor(20, 20, 80))
        sky_gradient.setColorAt(1, QColor(40, 40, 100))
        painter.fillRect(
            QRectF(0, 0, self.width, self.height * 0.7),
            sky_gradient
        )

        # Draw stars
        for x, y, brightness in self.stars:
            color = QColor(255, 255, 255, int(255 * brightness))
            painter.setPen(color)
            painter.drawPoint(int(x), int(y))

        # Draw water
        water_gradient = QLinearGradient(
            0, self.height * 0.7,
            0, self.height
        )
        water_gradient.setColorAt(0, QColor(0, 50, 100))
        water_gradient.setColorAt(1, QColor(0, 100, 150))
        painter.fillRect(
            QRectF(0, self.height * 0.7,
                  self.width, self.height * 0.3),
            water_gradient
        )

        # Draw waves
        painter.setPen(QPen(QColor(200, 200, 255, 100), 2))
        self.time += 0.1
        for wave in self.waves:
            path = QPainterPath()
            path.moveTo(QPointF(wave[0][0], wave[0][1]))
            for i in range(1, len(wave)):
                x = wave[i][0]
                y = wave[i][1] + math.sin(x/100 + self.time) * 5
                path.lineTo(x, y)
            painter.drawPath(path)

        # Draw sand
        sand_path = QPainterPath()
        sand_path.moveTo(0, self.height)
        sand_path.lineTo(0, self.height * 0.75)
        sand_path.quadTo(
            self.width/2, self.height * 0.68,
            self.width, self.height * 0.75
        )
        sand_path.lineTo(self.width, self.height)
        painter.fillPath(sand_path, QColor(255, 220, 170))

        # Draw palm trees
        for x, y, size in self.palm_trees:
            self._draw_palm_tree(painter, x, y, size)

    def _draw_palm_tree(self, painter: QPainter, x: float, y: float, size: float):
        """Draw a single palm tree"""
        trunk_height = 100 * size
        trunk_width = 15 * size

        # Draw trunk
        trunk = QPainterPath()
        trunk.moveTo(x, y)
        trunk.quadTo(x - 10, y - trunk_height/2,
                    x + 20, y - trunk_height)
        painter.setPen(QPen(QColor(110, 80, 50), trunk_width))
        painter.drawPath(trunk)

        # Draw palm fronds
        painter.setPen(QPen(QColor(0, 100, 0), 2))
        painter.setBrush(QColor(0, 120, 0))

        for i in range(5):
            angle = math.pi/6 + (i * math.pi/4)
            frond = QPainterPath()
            frond.moveTo(x + 20, y - trunk_height)

            # Create curved palm frond
            end_x = x + 20 + math.cos(angle) * 80 * size
            end_y = y - trunk_height + math.sin(angle) * 80 * size

            control_x = x + 20 + math.cos(angle) * 40 * size
            control_y = y - trunk_height + math.sin(angle) * 20 * size

            frond.quadTo(control_x, control_y, end_x, end_y)
            painter.drawPath(frond)


class ForestBackground:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.stars = self._generate_stars()
        self.trees = self._generate_trees()
        self.fireflies = self._generate_fireflies()
        self.time = 0  # For firefly animation

    def _generate_stars(self) -> List[Tuple[float, float, float]]:
        """Generate random stars with positions and brightness"""
        stars = []
        star_count = int((self.width * self.height) / 2000)

        for _ in range(star_count):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height * 0.5)
            brightness = random.uniform(0.3, 1.0)
            stars.append((x, y, brightness))
        return stars

    def _generate_trees(self) -> List[Tuple[float, float, float, int]]:
        """Generate tree positions, sizes and types"""
        trees = []
        tree_count = int(self.width / 50)  # Adjust density

        # Create three layers of trees
        for layer in range(3):
            base_y = self.height * (0.6 + layer * 0.1)
            layer_count = tree_count - (layer * 5)

            for _ in range(layer_count):
                x = random.uniform(0, self.width)
                size = random.uniform(0.8, 1.2) * (1 - layer * 0.2)
                tree_type = random.randint(0, 2)  # Different tree shapes
                trees.append((x, base_y, size, tree_type))

        # Sort trees by y position for correct layering
        trees.sort(key=lambda t: t[1])
        return trees

    def _generate_fireflies(self) -> List[Tuple[float, float, float]]:
        """Generate firefly positions and phases"""
        fireflies = []
        firefly_count = int(self.width / 100)

        for _ in range(firefly_count):
            x = random.uniform(0, self.width)
            y = random.uniform(self.height * 0.5, self.height * 0.8)
            phase = random.uniform(0, 2 * math.pi)  # Random starting phase
            fireflies.append((x, y, phase))
        return fireflies

    def draw(self, painter: QPainter):
        """Draw the complete forest scene"""
        # Sky gradient
        sky_gradient = QLinearGradient(0, 0, 0, self.height)
        sky_gradient.setColorAt(0, QColor(0, 0, 40))
        sky_gradient.setColorAt(0.5, QColor(10, 10, 50))
        sky_gradient.setColorAt(1, QColor(20, 30, 60))
        painter.fillRect(
            QRectF(0, 0, self.width, self.height),
            sky_gradient
        )

        # Draw stars
        for x, y, brightness in self.stars:
            color = QColor(255, 255, 255, int(255 * brightness))
            painter.setPen(color)
            painter.drawPoint(int(x), int(y))

        # Draw ground
        ground_gradient = QLinearGradient(
            0, self.height * 0.6,
            0, self.height
        )
        ground_gradient.setColorAt(0, QColor(20, 40, 20))
        ground_gradient.setColorAt(1, QColor(10, 30, 10))
        painter.fillRect(
            QRectF(0, self.height * 0.6,
                  self.width, self.height * 0.4),
            ground_gradient
        )

        # Draw trees
        for x, y, size, tree_type in self.trees:
            self._draw_tree(painter, x, y, size, tree_type)

        # Draw fireflies with animation
        self.time += 0.1
        for x, y, phase in self.fireflies:
            brightness = (math.sin(self.time + phase) + 1) / 2
            if brightness > 0.7:
                color = QColor(255, 255, 100, int(255 * brightness))
                painter.setPen(QPen(color, 2))
                painter.drawPoint(int(x), int(y))

    def _draw_tree(self, painter: QPainter, x: float, y: float, size: float, tree_type: int):
        """Draw a single tree with variation based on type"""
        if tree_type == 0:
            # Pine tree
            self._draw_pine_tree(painter, x, y, size)
        elif tree_type == 1:
            # Rounded tree
            self._draw_rounded_tree(painter, x, y, size)
        else:
            # Tall thin tree
            self._draw_tall_tree(painter, x, y, size)

    def _draw_pine_tree(self, painter: QPainter, x: float, y: float, size: float):
        """Draw a pine tree"""
        trunk_height = 40 * size
        tree_width = 60 * size
        tree_height = 100 * size

        # Draw trunk
        painter.setPen(QPen(QColor(60, 40, 20), 4))
        painter.drawLine(int(x), int(y), int(x), int(y - trunk_height))

        # Draw triangular sections
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 50, 20))

        sections = 3
        for i in range(sections):
            section_height = tree_height * (0.4 + i * 0.2)
            section_width = tree_width * (0.4 + i * 0.3)
            section_y = y - trunk_height - (tree_height * i/sections)

            triangle = QPainterPath()
            triangle.moveTo(x, section_y - section_height)
            triangle.lineTo(x - section_width/2, section_y)
            triangle.lineTo(x + section_width/2, section_y)
            painter.fillPath(triangle, painter.brush())

    def _draw_rounded_tree(self, painter: QPainter, x: float, y: float, size: float):
        """Draw a tree with a rounded canopy"""
        trunk_height = 30 * size
        canopy_radius = 35 * size

        # Draw trunk
        painter.setPen(QPen(QColor(60, 40, 20), 4))
        painter.drawLine(int(x), int(y), int(x), int(y - trunk_height))

        # Draw canopy
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 60, 30))

        canopy = QPainterPath()
        canopy.addEllipse(x - canopy_radius, y - trunk_height - canopy_radius*2,
                         canopy_radius*2, canopy_radius*2)
        painter.fillPath(canopy, painter.brush())

    def _draw_tall_tree(self, painter: QPainter, x: float, y: float, size: float):
        """Draw a tall, thin tree"""
        trunk_height = 80 * size
        canopy_width = 30 * size
        canopy_height = 100 * size

        # Draw trunk
        painter.setPen(QPen(QColor(60, 40, 20), 3))
        painter.drawLine(int(x), int(y), int(x), int(y - trunk_height))

        # Draw canopy
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(25, 55, 25))

        canopy = QPainterPath()
        canopy.moveTo(x, y - trunk_height - canopy_height)
        canopy.quadTo(x - canopy_width, y - trunk_height - canopy_height/2,
                     x - canopy_width/2, y - trunk_height)
        canopy.quadTo(x, y - trunk_height - canopy_height/4,
                     x + canopy_width/2, y - trunk_height)
        canopy.quadTo(x + canopy_width, y - trunk_height - canopy_height/2,
                     x, y - trunk_height - canopy_height)
        painter.fillPath(canopy, painter.brush())

        # Add some detail/highlight
        painter.setPen(QPen(QColor(35, 65, 35), 1))
        detail_path = QPainterPath()
        detail_path.moveTo(x, y - trunk_height - canopy_height)
        detail_path.quadTo(x - canopy_width * 0.7, y - trunk_height - canopy_height/2,
                         x, y - trunk_height - canopy_height/4)
        painter.drawPath(detail_path)
