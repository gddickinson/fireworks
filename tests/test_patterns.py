"""Tests for models/patterns.py"""
import math
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.patterns import (
    CirclePattern, HeartPattern, StarPattern,
    SpiralPattern, DoubleRingPattern, RandomPattern, TextPattern
)


class TestCirclePattern(unittest.TestCase):

    def test_returns_correct_number_of_points(self):
        p = CirclePattern(num_points=36)
        points = p.get_points(0, 0)
        self.assertEqual(len(points), 36)

    def test_points_are_tuples(self):
        p = CirclePattern(num_points=12)
        points = p.get_points(0, 0)
        for pt in points:
            self.assertEqual(len(pt), 2)

    def test_centered_at_origin(self):
        """Mean of circle points should be near the center."""
        p = CirclePattern(scale=1.0, num_points=360)
        points = p.get_points(5.0, 10.0)
        mean_x = sum(pt[0] for pt in points) / len(points)
        mean_y = sum(pt[1] for pt in points) / len(points)
        self.assertAlmostEqual(mean_x, 5.0, places=0)
        self.assertAlmostEqual(mean_y, 10.0, places=0)


class TestHeartPattern(unittest.TestCase):

    def test_returns_points(self):
        p = HeartPattern(num_points=36)
        points = p.get_points(0, 0)
        self.assertGreater(len(points), 0)

    def test_upright_on_screen(self):
        """Screen y grows downwards: the tip (t = 180 deg) must be below the centre, the lobes above it."""
        p = HeartPattern(num_points=36)
        points = p.get_points(0, 0)
        tip = points[18]           # t = 180 degrees
        top = points[0]            # t = 0: the dip between the lobes
        self.assertGreater(tip[1], 0)
        self.assertLess(top[1], 0)


class TestStarPattern(unittest.TestCase):

    def test_5_point_star(self):
        p = StarPattern(points=5)
        pts = p.get_points(0, 0)
        self.assertEqual(len(pts), 10)  # 5 outer + 5 inner

    def test_8_point_star(self):
        p = StarPattern(points=8)
        pts = p.get_points(0, 0)
        self.assertEqual(len(pts), 16)


class TestSpiralPattern(unittest.TestCase):

    def test_returns_points(self):
        p = SpiralPattern(arms=3)
        points = p.get_points(0, 0)
        self.assertEqual(len(points), 3 * 50)  # 3 arms * 50 steps


class TestDoubleRingPattern(unittest.TestCase):

    def test_correct_total_points(self):
        p = DoubleRingPattern(inner_points=12, outer_points=24)
        points = p.get_points(0, 0)
        self.assertEqual(len(points), 36)


class TestRandomPattern(unittest.TestCase):

    def test_returns_points(self):
        p = RandomPattern()
        points = p.get_points(0, 0)
        self.assertGreater(len(points), 0)


class TestTextPattern(unittest.TestCase):

    CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def test_every_letter_and_digit_has_a_shape(self):
        shapes = set()
        for ch in self.CHARS:
            pts = TextPattern(ch).get_points(0, 0)
            self.assertGreaterEqual(len(pts), 7, ch)
            shapes.add(tuple(sorted(pts)))
        self.assertEqual(len(shapes), len(self.CHARS), "every character has its own shape")

    def test_lowercase_matches_uppercase_and_unknown_is_empty(self):
        self.assertEqual(TextPattern("hello").get_points(0, 0), TextPattern("HELLO").get_points(0, 0))
        self.assertEqual(TextPattern("#").get_points(0, 0), [])

    def test_text_is_centred_and_letters_do_not_overlap(self):
        pts = TextPattern("HH", scale=2.0).get_points(100, 50)
        xs = [x for x, _ in pts]
        self.assertAlmostEqual((min(xs) + max(xs)) / 2, 100)
        left = [x for x in xs if x < 100]
        right = [x for x in xs if x > 100]
        self.assertEqual(len(left), len(right))
        self.assertGreater(min(right) - max(left), 0)


if __name__ == '__main__':
    unittest.main()
