# utils/physics.py
import math
from typing import Tuple, List
import random

class PhysicsUtils:
    @staticmethod
    def calculate_trajectory(
        start_x: float,
        start_y: float,
        velocity_x: float,
        velocity_y: float,
        gravity: float,
        time: float
    ) -> Tuple[float, float]:
        """Calculate position after time t given initial conditions"""
        final_x = start_x + (velocity_x * time)
        final_y = start_y + (velocity_y * time) + (0.5 * gravity * time * time)
        return final_x, final_y

    @staticmethod
    def calculate_velocity_components(
        speed: float,
        angle: float
    ) -> Tuple[float, float]:
        """Calculate x and y velocity components from speed and angle"""
        velocity_x = speed * math.cos(angle)
        velocity_y = speed * math.sin(angle)
        return velocity_x, velocity_y

    @staticmethod
    def calculate_distance(
        x1: float,
        y1: float,
        x2: float,
        y2: float
    ) -> float:
        """Calculate distance between two points"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
    def random_velocity(
        min_speed: float,
        max_speed: float,
        min_angle: float = 0,
        max_angle: float = 2 * math.pi
    ) -> Tuple[float, float]:
        """Generate random velocity components within given ranges"""
        speed = random.uniform(min_speed, max_speed)
        angle = random.uniform(min_angle, max_angle)
        return PhysicsUtils.calculate_velocity_components(speed, angle)
