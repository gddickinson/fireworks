"""Tests for utils/math.py"""
import math
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.math import MathUtils


class TestMathUtils(unittest.TestCase):

    def test_polar_to_cartesian_origin(self):
        """r=0 should give the origin."""
        x, y = MathUtils.polar_to_cartesian(0, 0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.0)

    def test_polar_to_cartesian_x_axis(self):
        """theta=0 should be along x-axis."""
        x, y = MathUtils.polar_to_cartesian(5.0, 0.0)
        self.assertAlmostEqual(x, 5.0)
        self.assertAlmostEqual(y, 0.0)

    def test_polar_to_cartesian_y_axis(self):
        """theta=pi/2 should be along y-axis."""
        x, y = MathUtils.polar_to_cartesian(5.0, math.pi / 2)
        self.assertAlmostEqual(x, 0.0, places=5)
        self.assertAlmostEqual(y, 5.0, places=5)

    def test_cartesian_to_polar_origin(self):
        """Origin should give r=0."""
        r, theta = MathUtils.cartesian_to_polar(0, 0)
        self.assertAlmostEqual(r, 0.0)

    def test_cartesian_to_polar_roundtrip(self):
        """Convert polar -> cartesian -> polar should preserve r."""
        r_in, theta_in = 3.0, math.pi / 4
        x, y = MathUtils.polar_to_cartesian(r_in, theta_in)
        r_out, theta_out = MathUtils.cartesian_to_polar(x, y)
        self.assertAlmostEqual(r_in, r_out, places=5)
        self.assertAlmostEqual(theta_in, theta_out, places=5)

    def test_rotate_point_360(self):
        """Rotating 360 degrees should return the original point."""
        x, y = MathUtils.rotate_point(3.0, 4.0, 2 * math.pi)
        self.assertAlmostEqual(x, 3.0, places=5)
        self.assertAlmostEqual(y, 4.0, places=5)

    def test_rotate_point_90(self):
        """Rotating (1,0) by 90 degrees around origin gives (0,1)."""
        x, y = MathUtils.rotate_point(1.0, 0.0, math.pi / 2)
        self.assertAlmostEqual(x, 0.0, places=5)
        self.assertAlmostEqual(y, 1.0, places=5)

    def test_bezier_curve_linear(self):
        """Bezier with 2 points should be a straight line."""
        points = [(0.0, 0.0), (10.0, 10.0)]
        curve = MathUtils.bezier_curve(points, num_points=11)
        self.assertEqual(len(curve), 11)
        # First and last points should match control points
        self.assertAlmostEqual(curve[0][0], 0.0, places=3)
        self.assertAlmostEqual(curve[0][1], 0.0, places=3)
        self.assertAlmostEqual(curve[-1][0], 10.0, places=3)
        self.assertAlmostEqual(curve[-1][1], 10.0, places=3)


if __name__ == '__main__':
    unittest.main()
