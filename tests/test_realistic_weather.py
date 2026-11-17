"""Realistic weather plug-ins of the desktop (effects/wx_*.py, ports of web/static/fw_wx_*.js): seeded, deterministic
update(), bounds, wind response, snow accumulation, lightning flashes, and painting (offscreen Qt)."""
import os
import sys
import time
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtGui import QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

from effects import wx_all  # noqa: E402
from effects.fx_base import WEATHER, FxEnv  # noqa: E402
from effects.scenery import build_scenery  # noqa: E402
from effects.scenery_parts import image_array  # noqa: E402
from effects.wx_lightning import make_lightning  # noqa: E402
from effects.wx_util import scene_geometry  # noqa: E402

LIGHTS = [(160, 90, 60, 1.5, (255, 180, 80)), (280, 70, 45, 0.8, (120, 200, 255))]
SCENE = build_scenery("Cityscape", 400, 280)


def _env(scenery=SCENE, wind=2.0, seed=12345, W=400, H=280):
    return FxEnv(W, H, scenery, list(LIGHTS), wind=wind, seed=seed)


def _run(name, scenery=SCENE, wind=2.0, n=300, seed=12345):
    env = _env(scenery, wind, seed)
    P = WEATHER[name][1](env)
    for i in range(n):
        env.time = i / 60
        P.update(1 / 60, env)
    return P, env


def _part(P, cls_name):
    parts = getattr(P, "parts", [P])
    return next(p for p in parts if type(p).__name__ == cls_name)


def _same(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray):
        return np.array_equal(a, b)
    return a == b


class TestWeatherUpdate(unittest.TestCase):

    def test_all_registered(self):
        for name in wx_all.NAMES:
            self.assertIn(name, WEATHER)
        self.assertEqual(WEATHER["Storm"][0], "Thunderstorm")

    def test_deterministic(self):
        for name in wx_all.NAMES:
            for scenery in (SCENE, None):
                with self.subTest(name=name, scenery=scenery is not None):
                    a, _ = _run(name, scenery)
                    b, _ = _run(name, scenery)
                    sa = a.state() if hasattr(a, "state") else None
                    self.assertTrue(_same(sa, b.state()))
                    c, _ = _run(name, scenery, seed=999)
                    if name not in ("Lightning",):   # (may have no strike yet at either seed)
                        self.assertFalse(_same(sa, c.state()), "another seed gives another run")

    def test_rain_bounds_and_slant(self):
        for wind in (3.0, -3.0):
            P, env = _run("Rain", wind=wind)
            for L in P.layers:
                self.assertTrue((L.x >= -20).all() and (L.x <= env.W + 20).all())
                self.assertTrue((L.y >= -env.H * 0.2).all() and (L.y <= env.H * 1.3).all())
            self.assertEqual(np.sign(P.stats()["vx"]), np.sign(wind), "streaks slant with the wind")
            st = P.stats()
            self.assertGreater(st["count"], 100)
            self.assertGreater(st["splashes"], 0)
        storm = _part(_run("Storm")[0], "Rain")
        self.assertGreater(storm.stats()["count"], P.stats()["count"], "storm rain is heavier")

    def test_snow_bounds_and_accumulation(self):
        P, env = _run("Snow", n=60)
        acc0 = P.stats()["acc"]
        for _ in range(600):
            P.update(1 / 60, env)
        f = P.state()
        self.assertTrue((f["x"] >= -20).all() and (f["x"] <= env.W + 20).all())
        self.assertTrue((f["y"] <= env.H + 20).all() and (f["y"] >= -30).all())
        self.assertTrue(((f["z"] >= 3) & (f["z"] <= 63)).all())
        self.assertGreater(P.stats()["acc"], acc0, "snow builds up")
        self.assertGreater(P.stats()["vx"], 0)

    def test_fog_and_clouds_scroll_with_the_wind(self):
        for name in ("Fog", "Mist", "Clouds"):
            for wind in (2.0, -2.0):
                env = _env(wind=wind)
                P = WEATHER[name][1](env)
                before = list(P.state())
                for _ in range(60):
                    P.update(1 / 60, env)
                moved = [a - b for a, b in zip(P.state(), before)]
                self.assertTrue(all(np.sign(m) == np.sign(wind) for m in moved), name)

    def test_lightning_flashes(self):
        env = _env()
        shared = {}
        P = make_lightning(env, shared, interval=(0.5, 1.0), ground=1.0)
        peak, bolts = 0.0, 0
        for _ in range(60 * 6):
            P.update(1 / 60, env)
            peak = max(peak, shared["flash"])
            bolts = max(bolts, P.stats()["bolts"])
        self.assertGreater(peak, 0.5)
        self.assertGreater(bolts, 0)
        tops = scene_geometry(env).tops
        for s in P.strikes:
            if s["bolt"]:
                self.assertLessEqual(s["bolt"][0][1], tops.max())
        env.reduced = True
        P.update(1 / 60, env)
        self.assertEqual(shared["flash"], 0.0, "no flashes with reduced motion")

    def test_scene_geometry(self):
        geo = scene_geometry(_env())
        self.assertEqual(len(geo.tops), 400)
        self.assertTrue((geo.tops < 280).all() and (geo.tops > 50).all(), "skyline / waterline in every column")
        self.assertGreater(len(geo.edges), 400)
        m = geo.mask(4)
        self.assertEqual((m.width(), m.height()), (100, 70))
        a = image_array(m)[..., 3]
        self.assertGreater(a[:5].mean(), 200, "open sky at the top")
        self.assertLess(a[-5:].mean(), 30, "no sky at the bottom")


class TestWeatherPaint(unittest.TestCase):

    def _paint(self, P, env, W, H):
        img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0xFF000000)
        p = QPainter(img)
        t = time.perf_counter()
        for name in ("draw_sky", "draw_over"):
            if hasattr(P, name):
                p.save()
                getattr(P, name)(p, env)
                p.restore()
        ms = (time.perf_counter() - t) * 1000
        p.end()
        return img, ms

    def test_paints_and_changes_pixels(self):
        for name in wx_all.NAMES:
            for scenery in (SCENE, None):
                with self.subTest(name=name, scenery=scenery is not None):
                    P, env = _run(name, scenery, n=120)
                    img, _ = self._paint(P, env, 400, 280)
                    self.assertGreater(image_array(img)[..., :3].astype(float).mean(), 0.5)

    def test_paint_time_at_1000x700(self):
        S = build_scenery("Cityscape", 1000, 700)
        lts = [(400, 250, 120, 1.5, (255, 180, 80)), (700, 200, 90, 0.8, (120, 200, 255))]
        out = []
        for name in wx_all.NAMES:
            env = FxEnv(1000, 700, S, lts, wind=2.0, seed=5)
            P = WEATHER[name][1](env)
            for _ in range(120):
                P.update(1 / 60, env)
            self._paint(P, env, 1000, 700)                    # first paint builds the textures
            ms = min(self._paint(P, env, 1000, 700)[1] for _ in range(3))
            out.append(f"{name} {ms:.1f} ms")
            self.assertLess(ms, 60, name)
        print("\nweather paint at 1000x700: " + ", ".join(out))


if __name__ == "__main__":
    unittest.main()
