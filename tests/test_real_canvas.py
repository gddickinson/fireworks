"""The desktop realistic renderer (gui/canvas_real.py, real_show.py, real_painter.py, text_points.py), offscreen Qt.

Main-window tests use QSettings in a temporary INI file, never the user's real settings.
"""
import os
import random
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

import gui.main_window as main_window  # noqa: E402
from effects.backgrounds import BeachBackground  # noqa: E402
from gui.canvas import FireworksCanvas  # noqa: E402
from gui.real_painter import RealPainter  # noqa: E402
from gui.real_show import RealShow  # noqa: E402
from gui.text_points import clean_text, text_points  # noqa: E402
from models.pyro import FOCAL  # noqa: E402

W, H = 480, 320


def _canvas(seed=1):
    c = FireworksCanvas()
    c.resize(W, H)
    c.timer.stop()
    c.set_renderer("Realistic")
    c.real_show.rand.seed(seed)
    return c


def _brightness(img: QImage) -> float:
    tot = 0
    for y in range(0, img.height(), 4):
        for x in range(0, img.width(), 4):
            c = img.pixelColor(x, y)
            tot += c.red() + c.green() + c.blue()
    return tot


class TestRealisticCanvas(unittest.TestCase):

    def test_steps_and_paints_into_an_image(self):
        c = _canvas()
        c.set_background("Cityscape")
        for _ in range(240):
            c.update_animation()
        self.assertGreater(len(c.real_show.sim.stars), 0, "auto launch fires shells")
        self.assertEqual(c.fireworks, [], "the classic model is not used")
        img = c.render_real_image()
        self.assertEqual((img.width(), img.height()), (W, H))
        self.assertGreater(c._real_painter.drawn, 0)

    def test_bursts_brighten_the_frame(self):
        c = _canvas(2)
        c.set_auto_launch(False)
        dark = _brightness(c.render_real_image())
        c.manual_launch()
        sim = c.real_show.sim
        burst_frame = None
        for f in range(400):
            c.update_animation()
            if any(e[0] == "burst" for e in sim.events):
                burst_frame = f
                break
        self.assertIsNotNone(burst_frame, "the shell bursts")
        for _ in range(8):
            c.update_animation()
            img = c.render_real_image()
        self.assertGreater(_brightness(img), dark * 1.05)

    def test_auto_launch_off_and_click_launch(self):
        c = _canvas()
        c.set_auto_launch(False)
        for _ in range(300):
            c.update_animation()
        self.assertEqual(c.real_show.sim.stars, [])
        c._real_launch(W * 0.75)                       # what a click at x = 0.75 W does
        shell = c.real_show.sim.stars[0]
        sx = W / 2 + FOCAL * H * shell.x / shell.z
        self.assertAlmostEqual(sx, W * 0.75, delta=W * 0.05)

    def test_settings_map_like_the_web(self):
        c = _canvas()
        c.set_particle_count(150)
        c.set_gravity(0.2)
        c.set_launch_speed(20.0)
        c.set_random_colors(False)
        c.set_firework_color(QColor(10, 20, 30))
        c.set_pattern("Heart")
        c.update_animation()
        sim, d = c.real_show.sim, c.real_show.director
        self.assertAlmostEqual(sim.star_scale, 2.0)
        self.assertAlmostEqual(sim.gravity_scale, 2.0)
        self.assertAlmostEqual(sim.height_scale, 1.3)
        self.assertEqual(d.color, (10, 20, 30))
        self.assertIs(d.pattern, c.pattern)
        c.set_random_colors(True)
        c.set_pattern("Random")
        c.update_animation()
        self.assertIsNone(d.color)
        self.assertIsNone(d.pattern, "'Random' without Randomize Patterns: real shell types")
        c.set_shell_type("Willow")
        self.assertEqual(d.shell_type, "willow")

    def test_finale_launches_shells(self):
        c = _canvas()
        c.set_auto_launch(False)
        c.start_finale()
        launches = 0
        for _ in range(60 * 8):                       # opening pairs, then the fan of palms
            c.update_animation()
            launches += sum(e[0] == "launch" for e in c.real_show.sim.events)
        self.assertGreaterEqual(launches, 10)

    def test_message_stars_hold_near_their_targets(self):
        c = _canvas()
        c.set_auto_launch(False)
        self.assertTrue(c.show_message("HI"))
        self.assertFalse(c.show_message("   "))
        sim = c.real_show.sim
        held = []
        for _ in range(60 * 10):
            c.update_animation()
            held = [s for s in sim.stars if s.target is not None and s.glide + 1.0 < s.age < s.hold]
            if len(held) > 100:
                break
        self.assertGreater(len(held), 100, "message stars are holding")
        err = sorted(((s.x - s.target[0]) ** 2 + (s.y - s.target[1]) ** 2) ** 0.5 for s in held)
        self.assertLess(err[len(err) // 2], 2.0, "median distance to the letter dot under 2 m")

    def test_beach_reflection_and_horizon(self):
        c = _canvas()
        c.set_background("Beach")
        self.assertIsInstance(c.background, BeachBackground)
        for _ in range(120):
            c.update_animation()
        self.assertAlmostEqual(c.real_show.sim.horizon, 0.7)
        c.render_real_image()

    def test_trails_fade_away(self):
        show = RealShow(1.5, 0.9, random.Random(3))
        show.sync(50, 0.1, 10.0, None, None, 1.0, False)
        show.launch()
        rp = RealPainter()
        img = QImage(150, 100, QImage.Format.Format_ARGB32_Premultiplied)
        for f in range(150):
            show.step()
            p = QPainter(img)
            rp.render(p, 150, 100, show)
            p.end()
        show.sim.stars.clear()
        for f in range(40):
            p = QPainter(img)
            rp.render(p, 150, 100, show)
            p.end()
        t = rp.trail
        mx = max(max(t.pixelColor(x, y).red(), t.pixelColor(x, y).green(), t.pixelColor(x, y).blue())
                 * t.pixelColor(x, y).alpha() // 255 for y in range(0, 100, 2) for x in range(0, 150, 2))
        self.assertEqual(mx, 0, "no permanent residue in the trail buffer")

    def test_classic_is_the_default_and_unchanged(self):
        c = FireworksCanvas()
        c.resize(W, H)
        c.timer.stop()
        self.assertEqual(c.renderer, "Classic")
        c.set_auto_launch(False)
        c.manual_launch()
        self.assertEqual(len(c.fireworks), 1)
        c.update_animation()
        self.assertIsNone(c._real, "classic mode never builds the realistic show")


class TestTextSampler(unittest.TestCase):

    def test_points_fit_the_view_and_count(self):
        aspect, horizon = 1000 / 700, 0.9
        for text in ("HI", "Happy New Year 2027"):
            pts = text_points(text, aspect, horizon)
            self.assertTrue(250 <= len(pts) <= 600, (text, len(pts)))
            us = [p[0] for p in pts]
            vs = [p[1] for p in pts]
            self.assertLessEqual(max(us) - min(us), 0.86 * 450 * aspect / FOCAL)
            self.assertLessEqual(max(vs) - min(vs), 0.62 * 450 * horizon / FOCAL)
            self.assertAlmostEqual((max(us) + min(us)) / 2, 0.0, delta=10.0)
            self.assertTrue(all(0 <= v <= 255 for p in pts for v in p[2:]))
        self.assertGreater(len({tuple(p[2:]) for p in text_points("RAINBOW", aspect, horizon)}), 10)

    def test_empty_and_cleaning(self):
        self.assertEqual(text_points("  \n ", 1.5, 0.9), [])
        self.assertEqual(clean_text(" a \n\n b\x07 "), "a\nb")


class TestMainWindowRealistic(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ini = os.path.join(self.tmp.name, "fireworks.ini")
        self._orig = main_window.QSettings
        main_window.QSettings = lambda *a: QSettings(ini, QSettings.Format.IniFormat)

    def tearDown(self):
        main_window.QSettings = self._orig
        self.tmp.cleanup()

    def test_window_starts_realistic_and_controls_drive_the_canvas(self):
        w = main_window.FireworksApp()
        self.assertTrue(w.settings.fileName().startswith(self.tmp.name))
        w.canvas.timer.stop()
        self.assertEqual(w.canvas.renderer, "Realistic")
        w.controls.shell_combo.setCurrentText("Palm")
        self.assertEqual(w.canvas.real_show.director.shell_type, "palm")
        w.controls.message_input.setText("OK")
        w.controls.message_button.click()
        self.assertIn("message", [c[1] for c in w.canvas.real_show.director.cues])  # after the opening show
        w.controls.finale_button.click()
        self.assertEqual(w.canvas.real_show.director.mode, "finale")
        w.controls.renderer_combo.setCurrentText("Classic")
        self.assertEqual(w.canvas.renderer, "Classic")
        self.assertFalse(w.controls.finale_button.isEnabled())

    def test_png_and_gif_export(self):
        from gui import export
        w = main_window.FireworksApp()
        w.canvas.timer.stop()
        w.canvas.resize(320, 200)
        png = os.path.join(self.tmp.name, "f.png")
        self.assertTrue(export.save_frame(w.canvas, png))
        self.assertFalse(QImage(png).isNull())
        frames = export.gif_frames(w.canvas, seconds=0.4, fps=15, width=120)
        self.assertEqual(len(frames), 6)
        self.assertEqual(frames[0].width(), 120)
        try:
            import PIL  # noqa: F401
        except ImportError:
            return
        gif = os.path.join(self.tmp.name, "f.gif")
        self.assertEqual(export.export_gif(w.canvas, gif, seconds=0.4, fps=15, width=120), 6)
        self.assertGreater(os.path.getsize(gif), 0)


if __name__ == "__main__":
    unittest.main()


def test_message_with_opening_show_from_the_controls():
    """The Opening show option queues opener shells before the message shell (desktop)."""
    c = _canvas()
    assert c.show_message("HI", opener="short")
    cues = c.real_show.director.cues
    first_msg = next(i for i, q in enumerate(cues) if q[1] == "message")
    assert first_msg > 5 and cues[first_msg][0] > 6.0
