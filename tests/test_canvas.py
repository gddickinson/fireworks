"""Regression tests for the display canvas and its wiring to the control panel (offscreen Qt)."""
import os
import random
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

from effects.backgrounds import NightSkyBackground  # noqa: E402
from gui.canvas import FireworksCanvas  # noqa: E402
from models.firework import Firework  # noqa: E402
from models.patterns import RandomPattern, TextPattern  # noqa: E402


class TestAutoLaunch(unittest.TestCase):

    def test_auto_launch_off_keeps_animating_and_manual_launch_works(self):
        c = FireworksCanvas()
        c.resize(800, 600)
        c.set_auto_launch(False)
        self.assertTrue(c.timer.isActive(), "turning auto launch off must not freeze the display")
        for _ in range(200):
            c.update_animation()
        self.assertEqual(c.fireworks, [], "no automatic launches")
        c.manual_launch()
        fw = c.fireworks[0]
        y0 = fw.y
        c.update_animation()
        self.assertLess(fw.y, y0, "a manually launched rocket moves")


class TestPhysicsControls(unittest.TestCase):

    def test_firework_gravity_and_launch_speed(self):
        random.seed(3)
        base = Firework(0, 600, None, 10)
        random.seed(3)
        fast = Firework(0, 600, None, 10, gravity=0.5, launch_speed=20.0)
        self.assertAlmostEqual(fast.velocity_y, 2 * base.velocity_y)
        fast.update()
        self.assertAlmostEqual(fast.velocity_y, 2 * base.velocity_y + 0.5)
        fast.explode()
        self.assertTrue(all(p.gravity == 0.5 for p in fast.particles))

    def test_sliders_reach_new_fireworks(self):
        from gui.main_window import FireworksApp
        w = FireworksApp()
        w.controls.gravity_slider.setValue(50)
        w.controls.speed_slider.setValue(200)
        self.assertAlmostEqual(w.canvas.gravity, 0.5)
        self.assertAlmostEqual(w.canvas.launch_speed, 20.0)
        w.canvas.add_firework()
        fw = w.canvas.fireworks[-1]
        self.assertAlmostEqual(fw.gravity, 0.5)
        self.assertGreater(-fw.velocity_y, 15.0)  # 8-12 range doubled


    def test_zero_gravity_rockets_are_dropped_off_screen(self):
        c = FireworksCanvas()
        c.resize(800, 600)
        c.set_auto_launch(False)
        c.set_gravity(0.0)
        c.manual_launch()
        for _ in range(300):
            c.update_animation()
        self.assertEqual(c.fireworks, [])


class TestPatternsAndStartup(unittest.TestCase):

    def test_text_updates_the_text_pattern_without_launching(self):
        c = FireworksCanvas()
        c.set_auto_launch(False)
        c.set_pattern("Text")
        c.set_text_pattern("AB")
        self.assertIsInstance(c.pattern, TextPattern)
        self.assertEqual(c.pattern.text, "AB")
        self.assertEqual(c.fireworks, [])

    def test_canvas_starts_with_the_settings_shown_in_the_controls(self):
        from gui.main_window import FireworksApp
        w = FireworksApp()
        v = w.controls.get_current_values()
        if v["background"] == "Night Sky":
            self.assertIsInstance(w.canvas.background, NightSkyBackground)
        self.assertIsNotNone(w.canvas.background)
        if v["pattern"] == "Random":
            self.assertIsInstance(w.canvas.pattern, RandomPattern)
        self.assertEqual(w.canvas.particle_count, v["particle_count"])
        self.assertEqual(w.canvas.auto_launch, v["auto_launch"])


if __name__ == "__main__":
    unittest.main()
