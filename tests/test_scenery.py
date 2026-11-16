"""Realistic scenery (effects/scenery_noise.py, scenery_parts.py, scenery.py) and its use by the desktop realistic
renderer; the Scenery and Lift time controls of the main window (offscreen Qt, temporary QSettings)."""
import os
import sys
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

import gui.main_window as main_window  # noqa: E402
from effects import scenery_noise as N  # noqa: E402
from effects.scenery import SCENERY_HORIZON, build_scenery  # noqa: E402
from effects.scenery_parts import image_array  # noqa: E402
from gui.canvas import FireworksCanvas  # noqa: E402

# Computed with node from web/static/fw_noise.js (2026-11-16).
JS = {
    "hash": [((7, 0), 0.07658816780894995), ((7, 1, 2), 0.3872177500743419), ((7, -5, 3), 0.4353392110206187),
             ((123456789, 100000, -77), 0.284984978614375), ((8, 1280, 5), 0.8999706171452999)],
    "noise1": [((7, 0.3), 0.14603413593024017), ((11, -2.75), 0.6570090231471113), ((42, 123.456), 0.5130202320341204)],
    "noise2": [((7, 0.3, 0.6), 0.6138687869090438), ((9, -1.2, 3.7), 0.34015695451848194),
               ((131, 55.5, -0.01), 0.4862810965382196)],
    "fbm1": [((7, 0.5), 0.33334647599473655), ((18, 3.3, 6), 0.4946363640893129), ((14, 12.34, 4), 0.4109726127153781)],
    "fbm2": [((7, 0.2, 0.9), 0.6615021963871366), ((16, -3.1, 2.2, 3), 0.7329928738587869),
             ((12, 1.5, 0.3, 5), 0.45501424847598976)],
    "ridged1": [((8, 3.6, 7), 0.14457506691968866), ((17, 10.2, 7), 0.5857251295741935),
                ((3, -0.4), 0.12331300058118275)],
}
PRNG7 = [0.011704753153026104, 0.06195825757458806, 0.97690763277933, 0.6990287057124078, 0.5214452685322613,
         0.4055216880515218]
PRNG_MAX = [0.8964226141106337, 0.189478256739676, 0.7156526781618595]     # prng(4294967295)


def _rgba(img):
    """(H, W, 4) array in R, G, B, A order."""
    a = image_array(img)
    return a[..., [2, 1, 0, 3]]


class TestNoiseMatchesJS(unittest.TestCase):

    def test_reference_values(self):
        for name, cases in JS.items():
            fn = getattr(N, name)
            for args, want in cases:
                self.assertAlmostEqual(float(fn(*args)), want, places=13, msg=f"{name}{args}")

    def test_vectorised_equals_scalar(self):
        import numpy as np
        xs = np.array([-3.7, 0.0, 0.25, 9.99, 1234.5])
        v = N.fbm1(21, xs, 6)
        for x, y in zip(xs, v):
            self.assertEqual(float(N.fbm1(21, float(x), 6)), float(y))

    def test_prng(self):
        r = N.prng(7)
        self.assertEqual([r() for _ in range(6)], PRNG7)
        r = N.prng(4294967295)
        self.assertEqual([r() for _ in range(3)], PRNG_MAX)


class TestScenery(unittest.TestCase):

    def test_every_background_at_two_sizes(self):
        for W, H in ((640, 400), (1280, 800)):
            for name, hz in SCENERY_HORIZON.items():
                with self.subTest(name=name, size=(W, H)):
                    t = time.perf_counter()
                    S = build_scenery(name, W, H)
                    self.assertLess(time.perf_counter() - t, 2.0)
                    self.assertEqual((S.W, S.H, S.horizon), (W, H, hz))
                    for img in (S.back, S.front, S.mat):
                        self.assertEqual((img.width(), img.height()), (W, H))
                    back, front, mat = _rgba(S.back), _rgba(S.front), _rgba(S.mat)
                    self.assertTrue((back[..., 3] == 255).all(), "back is opaque")
                    self.assertGreater(back[: H // 2, :, :3].mean(), 1.0, "sky is not black")
                    self.assertLess(back[: H // 2, :, :3].mean(), 60, "but a night sky")
                    cover = (front[..., 3] > 0).mean()
                    if name == "None":
                        self.assertEqual(cover, 0)
                    else:
                        self.assertGreater(cover, 0.02, "foreground silhouettes")
                        self.assertLess(cover, 0.6, "the sky stays visible through the front")
                    self.assertGreater(mat[2:H // 8, :, 2].mean(), 240, "material: the top is open sky (blue)")
                    self.assertGreater(mat[-H // 20:, :, 0].mean(), 15, "material: the ground has albedo (red)")
                    if name in ("Cityscape", "Mountains", "Beach"):
                        self.assertAlmostEqual(S.water, hz * H, places=6)
                        rows = mat[int(S.water) + 3:int(H * 0.9)]
                        self.assertGreater((rows[..., 1] > 200).mean(), 0.4, "material: water (green)")
                    else:
                        self.assertIsNone(S.water)
                        self.assertEqual(int((mat[..., 1] > 200).sum()), 0)
                    self.assertEqual(bool(S.fireflies), name == "Forest")

    def test_seeded_and_deterministic(self):
        a, b = build_scenery("Beach", 320, 200), build_scenery("Beach", 320, 200)
        self.assertEqual(a.back, b.back)
        self.assertNotEqual(a.back, build_scenery("Beach", 320, 200, seed=8).back)

    def test_water_reflects_the_skyline(self):
        S = build_scenery("Cityscape", 640, 400)
        back = _rgba(S.back)[..., :3].astype(float)
        wl = int(S.water)
        self.assertGreater(back[wl + 4:wl + 30].std(axis=1).mean(), 2.0, "lit windows mirrored in the river")


class TestRealisticScenery(unittest.TestCase):

    def _canvas(self, name):
        c = FireworksCanvas()
        c.resize(480, 320)
        c.timer.stop()
        c.set_renderer("Realistic")
        c.set_scenery_mode("Realistic")
        c.set_background(name)
        c.real_show.rand.seed(4)
        return c

    def test_paints_with_the_scenery_and_its_horizon(self):
        for name in ("Night Sky", "Cityscape", "Mountains", "Beach", "Forest"):
            c = self._canvas(name)
            for _ in range(200):
                c.update_animation()
            self.assertAlmostEqual(c.real_show.sim.horizon, SCENERY_HORIZON[name])
            img = c.render_real_image()
            self.assertIs(c._real_painter._albedo_src, c._scenery)
            self.assertEqual((c._scenery.name, c._scenery.W, c._scenery.H), (name, 480, 320))
            self.assertEqual(c._real_painter.albedo.width(), 480 // 4)
            px = _rgba(img)
            self.assertLess(px[-5:, :, :3].mean(), 40, "dark foreground at the bottom")

    def test_classic_scenery_keeps_the_old_backgrounds(self):
        c = self._canvas("Beach")
        c.set_scenery_mode("Classic")
        c.update_animation()
        self.assertAlmostEqual(c.real_show.sim.horizon, 0.7)
        c.render_real_image()
        self.assertIsNone(c._scenery)

    def test_resize_rebuilds_the_scenery(self):
        c = self._canvas("Forest")
        c.render_real_image()
        first = c._scenery
        c._resized_at = 0.0                     # the resize has settled
        c.resize(400, 300)
        c._resized_at = 0.0
        c.render_real_image()
        self.assertIsNot(c._scenery, first)
        self.assertEqual((c._scenery.W, c._scenery.H), (400, 300))

    def test_lift_time_maps_to_the_sim(self):
        c = self._canvas("Night Sky")
        self.assertEqual(c.real_show.sim.lift_time, 3.0)
        c.set_lift_time(1.5)
        self.assertEqual(c.real_show.sim.lift_time, 1.5)
        c.set_lift_time(5.0)
        self.assertIsNone(c.real_show.sim.lift_time, "5 s means real time")


class TestMainWindowSceneryControls(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ini = os.path.join(self.tmp.name, "fireworks.ini")
        self._orig = main_window.QSettings
        main_window.QSettings = lambda *a: QSettings(self.ini, QSettings.Format.IniFormat)

    def tearDown(self):
        main_window.QSettings = self._orig
        self.tmp.cleanup()

    def test_defaults_and_controls(self):
        w = main_window.FireworksApp()
        w.canvas.timer.stop()
        self.assertEqual(w.canvas.scenery_mode, "Realistic")
        self.assertEqual(w.canvas.real_show.sim.lift_time, 3.0)
        w.controls.lift_slider.setValue(5)
        self.assertEqual(w.canvas.real_show.sim.lift_time, 2.5)
        self.assertIn("2.5 s", w.controls.lift_label.text())
        w.controls.lift_slider.setValue(w.controls.lift_slider.maximum())
        self.assertIsNone(w.canvas.real_show.sim.lift_time)
        self.assertIn("real time", w.controls.lift_label.text())
        w.controls.scenery_combo.setCurrentText("Classic")
        self.assertEqual(w.canvas.scenery_mode, "Classic")
        values = w.controls.get_current_values()
        self.assertEqual((values["scenery"], values["lift_time"]), ("Classic", 5.0))

    def test_settings_are_loaded(self):
        s = QSettings(self.ini, QSettings.Format.IniFormat)
        s.setValue("scenery", "Classic")
        s.setValue("lift_time", 2.0)
        s.sync()
        w = main_window.FireworksApp()
        w.canvas.timer.stop()
        self.assertEqual(w.controls.scenery_combo.currentText(), "Classic")
        self.assertEqual(w.canvas.scenery_mode, "Classic")
        self.assertEqual(w.canvas.real_show.sim.lift_time, 2.0)


if __name__ == "__main__":
    unittest.main()
