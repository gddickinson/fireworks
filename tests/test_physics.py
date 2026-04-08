"""Tests for utils/physics.py"""
import math
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.physics import PhysicsUtils


class TestPhysicsUtils(unittest.TestCase):

    def test_calculate_trajectory_no_gravity(self):
        """Object at constant velocity with no gravity."""
        x, y = PhysicsUtils.calculate_trajectory(0, 0, 1.0, 0.0, 0.0, 5.0)
        self.assertAlmostEqual(x, 5.0)
        self.assertAlmostEqual(y, 0.0)

    def test_calculate_trajectory_with_gravity(self):
        """Falling object with gravity."""
        x, y = PhysicsUtils.calculate_trajectory(0, 0, 0.0, 0.0, 9.8, 2.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.5 * 9.8 * 4.0)

    def test_calculate_trajectory_start_offset(self):
        """Non-zero starting position."""
        x, y = PhysicsUtils.calculate_trajectory(10, 20, 1.0, 1.0, 0.0, 1.0)
        self.assertAlmostEqual(x, 11.0)
        self.assertAlmostEqual(y, 21.0)

    def test_velocity_components_zero_angle(self):
        """Velocity at angle 0 should be all in x."""
        vx, vy = PhysicsUtils.calculate_velocity_components(5.0, 0.0)
        self.assertAlmostEqual(vx, 5.0)
        self.assertAlmostEqual(vy, 0.0)

    def test_velocity_components_90_degrees(self):
        """Velocity at pi/2 should be all in y."""
        vx, vy = PhysicsUtils.calculate_velocity_components(5.0, math.pi / 2)
        self.assertAlmostEqual(vx, 0.0, places=5)
        self.assertAlmostEqual(vy, 5.0, places=5)

    def test_calculate_distance_same_point(self):
        """Distance from a point to itself is 0."""
        d = PhysicsUtils.calculate_distance(3.0, 4.0, 3.0, 4.0)
        self.assertAlmostEqual(d, 0.0)

    def test_calculate_distance_3_4_5(self):
        """Classic 3-4-5 triangle."""
        d = PhysicsUtils.calculate_distance(0, 0, 3, 4)
        self.assertAlmostEqual(d, 5.0)

    def test_random_velocity_returns_tuple(self):
        """random_velocity should return a 2-tuple of floats."""
        vx, vy = PhysicsUtils.random_velocity(1.0, 5.0)
        self.assertIsInstance(vx, float)
        self.assertIsInstance(vy, float)

    def test_random_velocity_speed_range(self):
        """Resulting speed should be within the given range."""
        for _ in range(50):
            vx, vy = PhysicsUtils.random_velocity(2.0, 4.0)
            speed = math.sqrt(vx**2 + vy**2)
            self.assertGreaterEqual(speed, 2.0 - 1e-9)
            self.assertLessEqual(speed, 4.0 + 1e-9)


if __name__ == '__main__':
    unittest.main()
