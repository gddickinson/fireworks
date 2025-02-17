from abc import ABC, abstractmethod
from typing import List, Tuple
import math
import random

class Pattern(ABC):
    def __init__(self, scale: float = 1.0, rotation: float = 0.0):
        self.scale = scale
        self.rotation = rotation  # in radians

    @abstractmethod
    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        pass

    def _rotate_point(self, x: float, y: float, cx: float, cy: float) -> Tuple[float, float]:
        """Rotate a point around center (cx, cy) by self.rotation radians"""
        dx = x - cx
        dy = y - cy
        rotated_x = dx * math.cos(self.rotation) - dy * math.sin(self.rotation)
        rotated_y = dx * math.sin(self.rotation) + dy * math.cos(self.rotation)
        return (cx + rotated_x, cy + rotated_y)

class CirclePattern(Pattern):
    def __init__(self, scale: float = 1.0, rotation: float = 0.0, num_points: int = 36):
        super().__init__(scale, rotation)
        self.num_points = num_points

    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        points = []
        for i in range(self.num_points):
            angle = 2 * math.pi * i / self.num_points
            px = x + math.cos(angle) * (50 * self.scale)
            py = y + math.sin(angle) * (50 * self.scale)
            points.append(self._rotate_point(px, py, x, y))
        return points

class HeartPattern(Pattern):
    def __init__(self, scale: float = 1.0, rotation: float = 0.0, num_points: int = 36):
        super().__init__(scale, rotation)
        self.num_points = num_points

    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        points = []
        for t in range(0, 360, 360 // self.num_points):
            angle = math.radians(t)
            px = x + self.scale * (16 * math.sin(angle) ** 3)
            py = y + self.scale * (13 * math.cos(angle) - 5 * math.cos(2 * angle) -
                                2 * math.cos(3 * angle) - math.cos(4 * angle))
            points.append(self._rotate_point(px, py, x, y))
        return points

class StarPattern(Pattern):
    def __init__(self, scale: float = 1.0, rotation: float = 0.0, points: int = 5, inner_radius: float = 0.4):
        super().__init__(scale, rotation)
        self.num_points = points
        self.inner_radius = inner_radius

    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        points = []
        for i in range(self.num_points * 2):
            angle = math.pi * i / self.num_points
            radius = (50 * self.scale) if i % 2 == 0 else (50 * self.scale * self.inner_radius)
            px = x + math.cos(angle) * radius
            py = y + math.sin(angle) * radius
            points.append(self._rotate_point(px, py, x, y))
        return points

class SpiralPattern(Pattern):
    def __init__(self, scale: float = 1.0, rotation: float = 0.0, arms: int = 3, rotations: float = 2.0):
        super().__init__(scale, rotation)
        self.arms = arms
        self.rotations = rotations

    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        points = []
        max_radius = 50 * self.scale
        steps = 50

        for arm in range(self.arms):
            arm_offset = 2 * math.pi * arm / self.arms
            for i in range(steps):
                t = i / (steps - 1)
                angle = t * 2 * math.pi * self.rotations + arm_offset
                radius = t * max_radius
                px = x + math.cos(angle) * radius
                py = y + math.sin(angle) * radius
                points.append(self._rotate_point(px, py, x, y))
        return points

class DoubleRingPattern(Pattern):
    def __init__(self, scale: float = 1.0, rotation: float = 0.0,
                 inner_points: int = 12, outer_points: int = 24):
        super().__init__(scale, rotation)
        self.inner_points = inner_points
        self.outer_points = outer_points

    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        points = []
        # Inner ring
        for i in range(self.inner_points):
            angle = 2 * math.pi * i / self.inner_points
            px = x + math.cos(angle) * (25 * self.scale)
            py = y + math.sin(angle) * (25 * self.scale)
            points.append(self._rotate_point(px, py, x, y))
        # Outer ring
        for i in range(self.outer_points):
            angle = 2 * math.pi * i / self.outer_points
            px = x + math.cos(angle) * (50 * self.scale)
            py = y + math.sin(angle) * (50 * self.scale)
            points.append(self._rotate_point(px, py, x, y))
        return points

class RandomPattern(Pattern):
    def __init__(self):
        scale = random.uniform(0.5, 1.5)
        rotation = random.uniform(0, 2 * math.pi)
        super().__init__(scale, rotation)

        self.patterns = [
            CirclePattern(scale, rotation, random.randint(24, 48)),
            HeartPattern(scale, rotation, random.randint(24, 48)),
            StarPattern(scale, rotation, random.randint(4, 8), random.uniform(0.3, 0.6)),
            SpiralPattern(scale, rotation, random.randint(2, 5), random.uniform(1.5, 3.0)),
            DoubleRingPattern(scale, rotation, random.randint(8, 16), random.randint(16, 32))
        ]
        self.selected_pattern = random.choice(self.patterns)

    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        return self.selected_pattern.get_points(x, y)

class TextPattern(Pattern):
    def __init__(self, text: str, scale: float = 1.0, spacing: float = 30.0):
        super().__init__(scale)
        self.text = text
        self.spacing = spacing
        self.char_width = 20 * scale  # Base width for each character
        self.total_width = len(text) * self.char_width

    def get_points(self, x: float, y: float) -> List[Tuple[float, float]]:
        points = []
        start_x = x - (self.total_width / 2)

        for i, char in enumerate(self.text):
            char_x = start_x + (i * self.char_width)
            char_points = self._get_char_points(char, char_x, y)
            points.extend(char_points)

        return points

    def _get_char_points(self, char: str, x: float, y: float) -> List[Tuple[float, float]]:
        # Simplified point-based character representations
        # You can expand this with more detailed character definitions
        points = []
        scale = self.scale * 15  # Scale factor for letters

        if char.upper() == 'A':
            points.extend([
                (x - scale, y + scale),
                (x, y - scale),
                (x + scale, y + scale),
                (x - scale/2, y),
                (x + scale/2, y)
            ])
        # Add more characters as needed...

        return points
