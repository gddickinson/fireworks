"""Regression tests: the burst uses the firework's explosion pattern (models/firework.py)."""
import math
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FireworkConfig  # noqa: E402
from models.firework import Firework  # noqa: E402
from models.patterns import CirclePattern, StarPattern, TextPattern  # noqa: E402


APP = None


def burst(pattern, count=50):
    fw = Firework(400, 600, None, count)
    fw.pattern = pattern
    fw.y = 300
    fw.explode()
    return fw


class TestPatternBurst(unittest.TestCase):

    def test_plain_burst_without_pattern(self):
        self.assertEqual(len(burst(None, 30).particles), 30)

    def test_one_particle_per_pattern_point_outermost_at_max_speed(self):
        fw = burst(CirclePattern(scale=1.5))
        self.assertEqual(len(fw.particles), 36)
        for p in fw.particles:
            self.assertAlmostEqual(math.hypot(p.velocity_x, p.velocity_y), FireworkConfig.PARTICLE_SPEED_MAX * 1.5)

    def test_burst_grows_into_the_shape(self):
        pattern = StarPattern(points=5)
        fw = burst(pattern)
        pts = pattern.get_points(400, 300)
        self.assertEqual(len(fw.particles), len(pts))
        for _ in range(10):
            for p in fw.particles:
                p.gravity = 0.0
                p.update()
        k = 10 * FireworkConfig.PARTICLE_SPEED_MAX / 50  # outermost star point: 50 px from the centre
        for p, (px, py) in zip(fw.particles, pts):
            self.assertAlmostEqual(p.x - 400, (px - 400) * k)
            self.assertAlmostEqual(p.y - 300, (py - 300) * k)

    def test_pattern_without_points_bursts_normally(self):
        self.assertEqual(len(burst(TextPattern("#"), 25).particles), 25)


class TestCanvasAttachesPattern(unittest.TestCase):

    def test_canvas_pattern_reaches_the_burst(self):
        from PyQt6.QtWidgets import QApplication
        global APP
        APP = QApplication.instance() or QApplication([])
        from gui.canvas import FireworksCanvas
        c = FireworksCanvas()
        c.resize(800, 600)
        c.set_auto_launch(False)
        c.set_pattern("Star")
        c.manual_launch()
        fw = c.fireworks[0]
        while not fw.exploded:
            fw.update()
        self.assertEqual(len(fw.particles), 10)


if __name__ == "__main__":
    unittest.main()
