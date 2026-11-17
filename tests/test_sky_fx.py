"""Sky effects (effects/sky_fx.py, sky_aurora.py) and scene animations (effects/scene_fx.py): seeded, deterministic
update() state, bounds, masking to the open sky / water (effects/fx_masks.py), and paint time (offscreen Qt)."""
import math
import os
import sys
import time
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PyQt6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

from effects import fx_masks  # noqa: E402
from effects.fx_base import SCENE_FX, SKY_FX, FxEnv  # noqa: E402
from effects.scene_fx import SCENE_MAKERS, Beacons, Boats, Smoke, Turbines, paint_boat  # noqa: E402
from effects.sky_aurora import Aurora  # noqa: E402
from effects.sky_fx import SKY_MAKERS, Lanterns, Meteors, Moon, moon_disc  # noqa: E402
from effects.scenery_noise import prng  # noqa: E402

DT = 1 / 60


def stand_in(W=400, H=280, time_of_day="night"):
    """A scenery stand-in: sky (blue) above 0.6 H, land (red albedo) 0.6-0.7 H, water (green) below 0.7 H."""
    mat = QImage(W, H, QImage.Format.Format_RGB32)
    mat.fill(QColor(0, 0, 255))
    p = QPainter(mat)
    p.fillRect(0, int(H * 0.6), W, int(H * 0.1) + 1, QColor(60, 0, 0))
    p.fillRect(0, int(H * 0.7), W, H, QColor(30, 255, 0))
    p.end()
    return types.SimpleNamespace(
        name="Harbour", W=W, H=H, mat=mat, horizon=0.6, water=H * 0.7, time=time_of_day,
        chimneys=[(100, 150, 6), (300, 160, 8)], beacons=[(50, 120, 2), (200, 100, 2), (350, 130, 2)],
        boats=[(120, 210, 40, 97), (260, 230, 50, 98)], turbines=[(80, 160, 20), (240, 150, 24)],
        lighthouse=(370, 150), bridge=None)


def env_for(S, W=None, H=None, seed=1234, wind=1.5):
    return FxEnv(W or S.W, H or S.H, scenery=S, lights=[], time=0.0, wind=wind, seed=seed)


def run(make, S, steps=300, seed=1234):
    env = env_for(S, seed=seed)
    fx = make(env)
    for i in range(steps):
        env.time = i * DT
        fx.update(DT, env)
    return fx, env


def arr(img):
    ptr = img.constBits()
    ptr.setsize(img.sizeInBytes())
    return np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)[:, :img.width()].copy()


def paint(fx, env, which="draw_sky"):
    img = QImage(int(env.W), int(env.H), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(0, 0, 0, 255))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    getattr(fx, which)(p, env)
    p.end()
    return arr(img)


class TestRegistry(unittest.TestCase):

    def test_registered_like_the_web(self):
        self.assertEqual({k: v[0] for k, v in SKY_FX.items() if k in ("moon", "meteors", "lanterns", "aurora")},
                         {"moon": "Moon", "meteors": "Shooting stars", "lanterns": "Sky lanterns", "aurora": "Aurora"})
        for name in ("Harbour", "Snowy Village", "River Bridge", "Waterfront", "Cityscape", "Countryside"):
            self.assertIn(name, SCENE_FX)


class TestDeterminism(unittest.TestCase):

    def test_same_seed_same_state(self):
        makers = dict(SKY_MAKERS, aurora=Aurora, **{"scene " + k: v for k, v in SCENE_MAKERS.items()})
        for name, make in makers.items():
            with self.subTest(name=name):
                a, _ = run(make, stand_in())
                b, _ = run(make, stand_in())
                self.assertEqual(a.state(), b.state())
                c, _ = run(make, stand_in(), seed=99)
                if name in ("moon", "meteors", "lanterns", "aurora"):
                    self.assertNotEqual(a.state(), c.state(), "the seed matters")


class TestBounds(unittest.TestCase):

    def test_moon_disc_and_published_position(self):
        n, px = moon_disc(20, 7, 1.05, 1, 0.2)
        self.assertEqual(px.shape, (n, n, 4))
        self.assertEqual(int(px[0, 0, 3]), 0, "transparent corner")
        self.assertEqual(int(px[n // 2, n // 2, 3]), 255)
        S = stand_in()
        fx, env = run(Moon, S, 10)
        self.assertEqual(S.moon["time"], env.time)
        self.assertLess(S.moon["y"], S.horizon * S.H)

    def test_meteors(self):
        fx, env = run(Meteors, stand_in(), 60 * 120)
        self.assertLessEqual(len(fx.list), 6)
        self.assertGreater(fx.next, fx.t)
        for m in fx.list:
            self.assertLess(m["age"], m["life"])

    def test_lanterns_stay_in_view_or_are_reborn(self):
        S = stand_in()
        fx, env = run(Lanterns, S, 60 * 60)
        self.assertEqual(len(fx.list), Lanterns.N)
        for L in fx.list:
            self.assertGreaterEqual(L["y"], -20)
            self.assertLessEqual(L["y"], S.horizon * S.H + 4 + 1e-9)
            self.assertTrue(-60 <= L["x"] <= S.W + 60)

    def test_aurora_time_and_columns(self):
        fx, env = run(Aurora, stand_in(), 120)
        self.assertAlmostEqual(fx.t, 2.0)
        col = fx.column(fx.curtains[0], np.linspace(0, 1, 50))
        self.assertTrue((col["b"] >= 0).all() and (col["h"] > 0).all())
        buf = fx.buffer(100, 40, 1.0)
        self.assertGreater(buf[..., 3].max(), 1.0, "rays are drawn")

    def test_scene_animations(self):
        S = stand_in()
        b, _ = run(Beacons, S, 200)
        self.assertEqual(len(b.state()["on"]), 3)
        flips = set()
        for i in range(120):
            b.update(DT)
            flips.add(tuple(b.state()["on"]))
        self.assertGreater(len(flips), 1, "they blink")
        sm, _ = run(Smoke, S, 60 * 20)
        self.assertGreater(sm.state()["n"], 0)
        self.assertLessEqual(sm.state()["n"], 2 * (6 / 0.32 + 2))
        tu, _ = run(Turbines, S, 600)
        self.assertTrue(all(0 <= a < 2 * math.pi for a in tu.state()["rot"]))
        bo, _ = run(Boats, S, 100)
        self.assertTrue(all(abs(bob) <= 1.6 * 1.15 + 1e-9 for bob, _ in bo.state()["boats"]))

    def test_boat_painter(self):
        img = QImage(80, 100, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        top = paint_boat(p, 40, 85, 40, 1.0, prng(5), sail=True)
        p.end()
        self.assertLess(top[1], -40 * 0.16 * 1.9 + 1e-9, "the mast is above the cabin")
        self.assertGreater((arr(img)[..., 3] > 0).mean(), 0.05)


class TestPainting(unittest.TestCase):

    def test_moon_stays_in_the_sky(self):
        S = stand_in(time_of_day="night")
        S.water = None
        fx, env = run(Moon, S, 5)
        px = paint(fx, env)
        hz = int(S.horizon * S.H)
        self.assertGreater(px[:hz, :, :3].max(), 200, "the moon is bright")
        self.assertEqual(int(px[hz + 2:, :, :3].max()), 0, "nothing below the skyline")

    def test_sky_effects_and_scenes_paint(self):
        S = stand_in()
        for name, make in dict(SKY_MAKERS, aurora=Aurora, **SCENE_MAKERS).items():
            with self.subTest(name=name):
                fx, env = run(make, S, 400)
                px = paint(fx, env)
                if name != "meteors":
                    self.assertGreater(int(px[..., :3].max()), 0, f"{name} draws something")

    def test_with_a_real_scenery(self):
        from effects.scenery import build_scenery
        S = build_scenery("Cityscape", 400, 280)
        for attr, default in (("time", "night"), ("beacons", [(100, 50, 2)]), ("chimneys", []), ("boats", []),
                              ("turbines", []), ("lighthouse", None)):
            if not hasattr(S, attr):
                setattr(S, attr, default)
        for make in (Moon, Aurora, Lanterns, Beacons):
            fx, env = run(make, S, 60)
            paint(fx, env)

    def test_paint_time_at_1000x700(self):
        S = stand_in(1000, 700)
        times = {}
        for name, make in dict(SKY_MAKERS, aurora=Aurora, **SCENE_MAKERS).items():
            fx, env = run(make, S, 400)
            paint(fx, env)                                    # caches (masks, moon image, sprites)
            t = time.perf_counter()
            for _ in range(5):
                paint(fx, env)
            times[name] = (time.perf_counter() - t) / 5 * 1000
        print("\npaint ms at 1000x700 (incl. a 1000x700 image fill):",
              ", ".join(f"{k} {v:.1f}" for k, v in times.items()))
        for name, ms in times.items():
            self.assertLess(ms, 120, name)


if __name__ == "__main__":
    unittest.main()
