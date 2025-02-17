# utils/math_utils.py
from typing import List, Tuple
import math
import numpy as np

class MathUtils:
    @staticmethod
    def bezier_curve(
        points: List[Tuple[float, float]],
        num_points: int = 100
    ) -> List[Tuple[float, float]]:
        """Generate points along a Bezier curve"""
        n = len(points) - 1
        t = np.linspace(0, 1, num_points)
        curve = []

        for t_i in t:
            x = 0
            y = 0
            for i in range(n + 1):
                bernstein = math.comb(n, i) * (t_i ** i) * ((1 - t_i) ** (n - i))
                x += points[i][0] * bernstein
                y += points[i][1] * bernstein
            curve.append((x, y))

        return curve

    @staticmethod
    def polar_to_cartesian(
        r: float,
        theta: float
    ) -> Tuple[float, float]:
        """Convert polar coordinates to cartesian"""
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        return x, y

    @staticmethod
    def cartesian_to_polar(
        x: float,
        y: float
    ) -> Tuple[float, float]:
        """Convert cartesian coordinates to polar"""
        r = math.sqrt(x * x + y * y)
        theta = math.atan2(y, x)
        return r, theta

    @staticmethod
    def rotate_point(
        x: float,
        y: float,
        angle: float,
        origin_x: float = 0,
        origin_y: float = 0
    ) -> Tuple[float, float]:
        """Rotate a point around an origin point"""
        # Translate point to origin
        translated_x = x - origin_x
        translated_y = y - origin_y

        # Rotate
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        rotated_x = translated_x * cos_angle - translated_y * sin_angle
        rotated_y = translated_x * sin_angle + translated_y * cos_angle

        # Translate back
        final_x = rotated_x + origin_x
        final_y = rotated_y + origin_y

        return final_x, final_y
