"""The seven newer realistic scenes and dusk (effects/scenery_more.py, scenery_land.py, scenery_sky.py), the gusty
wind of the desktop realistic show, and the main window's scene controls (time of day, realistic-only scenes and
weathers, sky effects, ground devices) with their QSettings (offscreen Qt, temporary settings)."""
import math
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
import ui_specs as U  # noqa: E402
from effects.fx_base import WEATHER, gusty_wind  # noqa: E402
from effects.scenery import NEW_SCENERY_HORIZON, SCENE_HORIZON, SCENERY_HORIZON, build_scenery  # noqa: E402
from effects.scenery_parts import image_array  # noqa: E402
from gui.canvas import FireworksCanvas  # noqa: E402
from gui.real_show import WIND_BASE, RealShow  # noqa: E402

WATER = {"Harbour", "River Bridge", "Waterfront"}


def _rgba(img):
    return image_array(img)[..., [2, 1, 0, 3]]


class TestNewScenes(unittest.TestCase):

    def test_every_new_scene_at_two_sizes_and_dusk(self):
        for W, H in ((640, 400), (1280, 800)):
            for name, hz in NEW_SCENERY_HORIZON.items():
                skies = {}
                for tod in ("night", "dusk"):
                    with self.subTest(name=name, size=(W, H), time=tod):
                        t = time.perf_counter()
                        S = build_scenery(name, W, H, time=tod)
                        self.assertLess(time.perf_counter() - t, 2.0)
                        self.assertEqual((S.name, S.W, S.H, S.horizon, S.time), (name, W, H, hz, tod))
                        back, front, mat = _rgba(S.back), _rgba(S.front), _rgba(S.mat)
                        self.assertTrue((back[..., 3] == 255).all())
                        skies[tod] = back[: H // 3, :, :3].mean()
                        self.assertGreater(skies[tod], 1.0)
                        cover = (front[..., 3] > 0).mean()
                        self.assertGreater(cover, 0.02, "foreground silhouettes")
                        self.assertLess(cover, 0.75, "the sky stays visible")
                        self.assertGreater(mat[2:H // 10, :, 2].mean(), 240, "open sky at the top")
                        self.assertGreater(mat[-H // 20:, :, 0].mean(), 15, "albedo at the bottom")
                        if name in WATER:
                            self.assertAlmostEqual(S.water, hz * H, places=6)
                            rows = mat[int(S.water) + 3:int(H * 0.88)]
                            self.assertGreater((rows[..., 1] > 200).mean(), 0.3, "material: water")
                        else:
                            self.assertIsNone(S.water)
                        self.assertEqual(S.bridge is not None, name == "River Bridge")
                self.assertGreater(skies["dusk"], skies["night"] * 1.4, f"{name}: the blue hour is brighter")

    def test_scene_objects_for_the_animations(self):
        S = {n: build_scenery(n, 800, 500) for n in NEW_SCENERY_HORIZON}
        self.assertEqual(len(S["Harbour"].boats), 3)
        self.assertIsNotNone(S["Harbour"].lighthouse)
        self.assertGreater(len(S["Snowy Village"].chimneys), 5)
        self.assertGreater(len(S["Countryside"].turbines), 3)
        self.assertEqual(S["Countryside"].chimneys, [], "the farm's chimneys are dropped, as in the web")
        self.assertGreaterEqual(len(S["River Bridge"].beacons), 2)
        self.assertGreater(len(S["Waterfront"].beacons), 3)
        self.assertAlmostEqual(S["River Bridge"].bridge, 0.07 * 150 / 1.5)

    def test_seeded_and_deterministic(self):
        a, b = build_scenery("Castle", 320, 200), build_scenery("Castle", 320, 200)
        self.assertEqual(a.back, b.back)
        self.assertEqual(a.front, b.front)
        self.assertNotEqual(a.back, build_scenery("Castle", 320, 200, seed=8).back)

    def test_original_scenes_unchanged_at_night_and_lighter_at_dusk(self):
        self.assertEqual(set(SCENE_HORIZON), set(SCENERY_HORIZON) | set(NEW_SCENERY_HORIZON))
        for name in SCENERY_HORIZON:
            night, default = build_scenery(name, 320, 200, time="night"), build_scenery(name, 320, 200)
            self.assertEqual(night.back, default.back)
            dusk = build_scenery(name, 320, 200, time="dusk")
            self.assertGreater(_rgba(dusk.back)[:60, :, :3].mean(), _rgba(night.back)[:60, :, :3].mean())


class TestGustyWind(unittest.TestCase):

    def test_formula_like_the_web(self):
        t, seed = 12.5, 1234
        ph = (seed % 1000) * 0.01
        swell = 0.25 * math.sin(t * 0.21 + ph) + 0.15 * math.sin(t * 0.53 + 2 * ph)
        gust = max(0.0, math.sin(t * 0.11 + ph * 3)) ** 6 * 0.8
        self.assertAlmostEqual(gusty_wind(1.5, t, seed), 1.5 * (1 + swell + gust), places=12)
        vals = [gusty_wind(1.5, i / 60, 7) for i in range(60 * 120)]
        self.assertGreater(min(vals), 1.5 * 0.59)
        self.assertLess(max(vals), 1.5 * 2.21)
        self.assertGreater(max(vals) - min(vals), 0.3, "it gusts")

    def test_show_sets_the_wind_every_step(self):
        a, b = RealShow(rand=__import__("random").Random(3), seed=99), RealShow(rand=__import__("random").Random(3),
                                                                                  seed=99)
        for _ in range(90):
            a.step()
            b.step()
            self.assertEqual(a.sim.wind, gusty_wind(WIND_BASE, a.sim.time, 99))
        self.assertEqual(a.sim.wind, b.sim.wind)


class TestCanvasFx(unittest.TestCase):

    def _canvas(self, scene, weather="None", sky=()):
        c = FireworksCanvas()
        c.resize(480, 320)
        c.timer.stop()
        c.set_renderer("Realistic")
        c.set_scenery_mode("Realistic")
        c.set_background(scene)
        c.set_weather(weather)
        c.set_sky_effects(sky)
        c.real_show.rand.seed(5)
        return c

    def test_new_scene_weather_and_sky_effects_paint(self):
        for weather in [w for w in U.REAL_WEATHER if w != "None"]:
            with self.subTest(weather=weather):
                c = self._canvas("Harbour", weather, ("moon", "aurora"))
                c.render_real_image()
                for _ in range(30):
                    c.update_animation()
                img = c.render_real_image()
                self.assertEqual((img.width(), img.height()), (480, 320))
                self.assertEqual(c._scenery.name, "Harbour")
                self.assertAlmostEqual(c.real_show.sim.horizon, NEW_SCENERY_HORIZON["Harbour"])
                self.assertIsNone(c.weather_effect if weather in ("Mist", "Clouds", "Storm") else None)
                names = [type(p).__name__ for p in c._fx.plugins]
                self.assertEqual(len(names), 4, names)     # scene animations, moon, aurora, weather
                self.assertIs(c._fx_key[1], weather)

    def test_dusk_rebuilds_the_scenery(self):
        c = self._canvas("Castle")
        c.render_real_image()
        self.assertEqual(c._scenery.time, "night")
        c.set_time_of_day("Dusk")
        c.render_real_image()
        self.assertEqual(c._scenery.time, "dusk")

    def test_classic_scenery_keeps_classic_weather(self):
        c = self._canvas("Cityscape", "Rain")
        c.set_scenery_mode("Classic")
        c.update_animation()
        c.render_real_image()
        self.assertIsNone(c.fx_layers(480, 320))
        self.assertIsNotNone(c.weather_effect)

    def test_ground_devices_and_the_bridge(self):
        c = self._canvas("River Bridge")
        c.render_real_image()
        c.set_ground_effects(True)
        c.update_animation()
        d = c.real_show.director
        self.assertTrue(d.ground)
        self.assertAlmostEqual(d.niagara_height, c._scenery.bridge)
        c.fire_ground("Niagara falls")
        e = c.real_show.sim.emitters[-1]
        self.assertEqual(e.kind, "niagara")
        self.assertAlmostEqual(e.y, c._scenery.bridge)
        c.set_background("Desert")
        c.render_real_image()
        c.update_animation()
        self.assertIsNone(d.niagara_height, "no bridge, no niagara in the finale")


class TestMainWindowSceneControls(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ini = os.path.join(self.tmp.name, "fireworks.ini")
        self._orig = main_window.QSettings
        main_window.QSettings = lambda *a: QSettings(self.ini, QSettings.Format.IniFormat)

    def tearDown(self):
        main_window.QSettings = self._orig
        self.tmp.cleanup()

    def _items(self, combo):
        return [combo.itemText(i) for i in range(combo.count())]

    def test_lists_follow_renderer_and_scenery(self):
        w = main_window.FireworksApp()
        w.canvas.timer.stop()
        c = w.controls
        self.assertEqual(self._items(c.background_combo), U.REAL_BACKGROUNDS)
        self.assertEqual(self._items(c.weather_combo), U.REAL_WEATHER)
        c.background_combo.setCurrentText("Snowy Village")
        c.weather_combo.setCurrentText("Storm")
        self.assertEqual((w.canvas.background_name, w.canvas.weather_name), ("Snowy Village", "Storm"))
        self.assertEqual(w.canvas.scene_name(), "Snowy Village")
        c.scenery_combo.setCurrentText("Classic")
        self.assertEqual(self._items(c.background_combo), U.BACKGROUNDS)
        self.assertEqual(self._items(c.weather_combo), U.WEATHER)
        self.assertEqual((w.canvas.background_name, w.canvas.weather_name), ("Night Sky", "None"))
        self.assertFalse(c.time_combo.isEnabled())
        c.scenery_combo.setCurrentText("Realistic")
        c.renderer_combo.setCurrentText("Classic")
        self.assertEqual(self._items(c.background_combo), U.BACKGROUNDS)
        self.assertFalse(c.fire_button.isEnabled())

    def test_controls_drive_the_canvas_and_persist(self):
        w = main_window.FireworksApp()
        w.canvas.timer.stop()
        c = w.controls
        c.background_combo.setCurrentText("River Bridge")
        c.weather_combo.setCurrentText("Mist")
        c.time_combo.setCurrentText("Dusk")
        c.sky_checks["moon"].setChecked(True)
        c.sky_checks["lanterns"].setChecked(True)
        c.ground_check.setChecked(True)
        c.device_combo.setCurrentIndex(U.GROUND_DEVICES.index("cake"))
        cv = w.canvas
        self.assertEqual(cv.time_of_day, "dusk")
        self.assertEqual(cv.sky_fx, ("moon", "lanterns"))
        self.assertTrue(cv.ground_on)
        c.fire_button.click()
        self.assertEqual(cv.real_show.sim.emitters[-1].kind, "cake")
        values = c.get_current_values()
        for key, value in values.items():
            w.settings.setValue(key, value)
        w.settings.sync()
        w2 = main_window.FireworksApp()
        w2.canvas.timer.stop()
        c2 = w2.controls
        self.assertEqual(c2.background_combo.currentText(), "River Bridge")
        self.assertEqual(c2.weather_combo.currentText(), "Mist")
        self.assertEqual(c2.time_combo.currentText(), "Dusk")
        self.assertEqual(c2.sky_effects(), ["moon", "lanterns"])
        self.assertTrue(c2.ground_check.isChecked())
        self.assertEqual(c2.ground_device(), "cake")
        self.assertEqual((w2.canvas.time_of_day, w2.canvas.sky_fx, w2.canvas.ground_on, w2.canvas.weather_name),
                         ("dusk", ("moon", "lanterns"), True, "Mist"))
        self.assertIn("Mist", WEATHER)


if __name__ == "__main__":
    unittest.main()
