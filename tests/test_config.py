"""Tests for config.py validation."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FireworkConfig, DisplayConfig


class TestFireworkConfigValidation(unittest.TestCase):

    def test_default_config_is_valid(self):
        """Default config should not raise."""
        config = FireworkConfig()
        self.assertEqual(config.DEFAULT_PARTICLES, 50)

    def test_invalid_min_particles(self):
        with self.assertRaises(ValueError):
            FireworkConfig(MIN_PARTICLES=0)

    def test_max_less_than_min(self):
        with self.assertRaises(ValueError):
            FireworkConfig(MIN_PARTICLES=100, MAX_PARTICLES=50)

    def test_default_out_of_range(self):
        with self.assertRaises(ValueError):
            FireworkConfig(MIN_PARTICLES=10, MAX_PARTICLES=20, DEFAULT_PARTICLES=50)

    def test_invalid_frame_rate(self):
        with self.assertRaises(ValueError):
            FireworkConfig(FRAME_RATE=0)

    def test_invalid_spawn_rate(self):
        with self.assertRaises(ValueError):
            FireworkConfig(SPAWN_RATE=1.5)

    def test_launch_speed_inverted(self):
        with self.assertRaises(ValueError):
            FireworkConfig(LAUNCH_SPEED_MIN=15.0, LAUNCH_SPEED_MAX=5.0)


class TestDisplayConfigValidation(unittest.TestCase):

    def test_default_config_is_valid(self):
        config = DisplayConfig()
        self.assertEqual(config.WINDOW_WIDTH, 800)

    def test_width_too_small(self):
        with self.assertRaises(ValueError):
            DisplayConfig(WINDOW_WIDTH=100, MIN_WINDOW_WIDTH=400)

    def test_height_too_small(self):
        with self.assertRaises(ValueError):
            DisplayConfig(WINDOW_HEIGHT=100, MIN_WINDOW_HEIGHT=300)


if __name__ == '__main__':
    unittest.main()
