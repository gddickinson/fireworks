"""Seeded runs of the real Python models, for checking the JavaScript port (web/static/fw_*.js).

The Python code draws random numbers through the ``random`` module (``random.uniform``, ``randint``, ``random``,
``choice``).  `seeded()` swaps that module, in each model module's namespace, for `PyRand`: a Python copy of the
mulberry32 generator in ``static/core.js`` (``rng()``) with the same four methods as ``static/fw_rand.js``. Given the
same seed the JS port then consumes the identical random stream and must land on the same state. Everything else
(`Firework`, `Particle`, the patterns, the weather effects, the backgrounds' scene generation, `ColorUtils`) is the
unmodified package code.

Two groups of cases:
  * core (Qt-free): explosion patterns and a firework show (the loop of ``FireworksCanvas.update_animation``);
  * qt (needs PyQt6, whose modules effects/ and utils/color.py import): weather, backgrounds, random colours.
    When PyQt6 is missing (e.g. the Linux CI) `fixture()` leaves the qt group out.

Used by the web API (/api/reference/..., the Verify page) and by scripts/make_js_fixtures.py (node-test fixtures).
"""
from __future__ import annotations

import contextlib
import importlib
import json
import math
from dataclasses import fields

from config import FireworkConfig
from models import patterns as P
from models.firework import Firework

M32 = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return (a * b) & M32


class PyRand:
    """mulberry32 (bit-for-bit ``rng(seed)`` in core.js) offering the ``random``-module calls the models use."""

    def __init__(self, seed: int) -> None:
        self.a = seed & M32

    def random(self) -> float:
        self.a = (self.a + 0x6D2B79F5) & M32
        a = self.a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296.0

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()  # as CPython's random.uniform

    def randint(self, a: int, b: int) -> int:
        return a + int(self.random() * (b - a + 1))

    def choice(self, seq):
        return seq[int(self.random() * len(seq))]


CORE_MODULES = ["models.firework", "models.patterns"]
QT_MODULES = ["effects.weather", "effects.backgrounds", "effects.mountains", "utils.color"]


def has_qt() -> bool:
    try:
        importlib.import_module("PyQt6.QtGui")
        return True
    except ImportError:
        return False


@contextlib.contextmanager
def seeded(seed: int, modules=CORE_MODULES):
    """Point ``random`` inside *modules* at one PyRand(seed); restore the real module afterwards."""
    rand = PyRand(seed)
    mods = [importlib.import_module(m) for m in modules]
    saved = [m.random for m in mods]
    for m in mods:
        m.random = rand
    try:
        yield rand
    finally:
        for m, r in zip(mods, saved):
            m.random = r


# --- core: patterns -------------------------------------------------------------------------------------------------
PATTERN_CASES = [
    ("Circle", {"scale": 1.3, "rotation": 0.7, "num_points": 24}),
    ("Circle", {}),
    ("Heart", {}),
    ("Heart", {"scale": 2.0, "rotation": 1.1, "num_points": 24}),
    ("Star", {}),
    ("Star", {"scale": 1.5, "rotation": 0.3, "points": 7, "inner_radius": 0.5}),
    ("Spiral", {}),
    ("Spiral", {"scale": 0.8, "rotation": 2.0, "arms": 4, "rotations": 2.5}),
    ("Double Ring", {}),
    ("Double Ring", {"scale": 1.2, "rotation": 0.4, "inner_points": 10, "outer_points": 20}),
    ("Text", {"text": "A a", "scale": 1.2}),
    ("Text", {"text": "Hello"}),
    ("Text", {"text": "AZ 09 fireworks!", "scale": 0.8}),
]
PATTERN_CLASSES = {"Circle": P.CirclePattern, "Heart": P.HeartPattern, "Star": P.StarPattern,
                   "Spiral": P.SpiralPattern, "Double Ring": P.DoubleRingPattern, "Text": P.TextPattern}
CENTER = (400.0, 300.0)


def pattern_points() -> list:
    out = [{"name": n, "kwargs": kw, "points": PATTERN_CLASSES[n](**kw).get_points(*CENTER)}
           for n, kw in PATTERN_CASES]
    for seed in (1, 2, 3, 4, 5, 6):
        with seeded(seed):
            rp = P.RandomPattern()
            out.append({"name": "Random", "seed": seed, "selected": rp.patterns.index(rp.selected_pattern),
                        "points": rp.get_points(*CENTER)})
    return out


# --- core: a firework show --------------------------------------------------------------------------------------
SHOW_CASES = [
    {"name": "default", "seed": 7, "width": 800, "height": 600, "particles": 50, "steps": 300, "snap_every": 50},
    {"name": "dense", "seed": 21, "width": 1200, "height": 700, "particles": 200, "steps": 240, "snap_every": 60},
    {"name": "physics", "seed": 5, "width": 900, "height": 600, "particles": 40, "steps": 300, "snap_every": 50,
     "gravity": 0.04, "launch_speed": 7.5},
    {"name": "star", "seed": 13, "width": 800, "height": 600, "particles": 50, "steps": 240, "snap_every": 60,
     "pattern": "Star", "pattern_kwargs": {"scale": 1.2, "rotation": 0.5, "points": 6}},
    {"name": "random_patterns", "seed": 17, "width": 800, "height": 600, "particles": 50, "steps": 240,
     "snap_every": 60, "random_each": True},
    {"name": "text", "seed": 19, "width": 800, "height": 600, "particles": 50, "steps": 240, "snap_every": 60,
     "pattern": "Text", "pattern_kwargs": {"text": "HI 42", "scale": 1.0}},
]
SHOW_BY_NAME = {c["name"]: c for c in SHOW_CASES}


def _snap(fws: list) -> list:
    snap = []
    for fw in fws:
        ps = fw.particles
        snap.append({
            "x": fw.x, "y": fw.y, "vy": fw.velocity_y, "exploded": fw.exploded, "n": len(ps),
            "sx": math.fsum(p.x for p in ps), "sy": math.fsum(p.y for p in ps),
            "svx": math.fsum(p.velocity_x for p in ps), "svy": math.fsum(p.velocity_y for p in ps),
            "life": ps[0].current_life if ps else None,
        })
    return snap


def run_show(case: dict) -> dict:
    """The FireworksCanvas.update_animation loop (fixed colour, optional pattern) with the real Firework/Particle."""
    from config import DEFAULT_LAUNCH_SPEED
    g, ls = case.get("gravity", FireworkConfig.GRAVITY), case.get("launch_speed", DEFAULT_LAUNCH_SPEED)
    w, h = case["width"], case["height"]
    fws: list = []
    snaps = []
    with seeded(case["seed"]) as rand:
        pattern = None
        if case.get("random_each"):
            P.RandomPattern()  # FireworksCanvas.set_random_patterns(True)
        elif case.get("pattern"):
            pattern = PATTERN_CLASSES[case["pattern"]](**case.get("pattern_kwargs", {}))
        for step in range(case["steps"] + 1):
            if step % case["snap_every"] == 0:
                snaps.append({"step": step, "fireworks": _snap(fws)})
            fws = [fw for fw in fws if fw.update() and (fw.exploded or fw.y > -h)]
            if rand.random() < FireworkConfig.SPAWN_RATE:  # FireworksCanvas.add_firework
                fw = Firework(rand.randint(0, w), h, (255, 0, 0), case["particles"], gravity=g, launch_speed=ls)
                if case.get("random_each"):
                    fw.pattern = P.RandomPattern()
                elif pattern is not None:
                    fw.pattern = pattern
                fws.append(fw)
    return {"case": case, "snapshots": snaps}


# --- qt: weather, backgrounds, colours ----------------------------------------------------------------------------
def weather_runs(seed: int = 3, w: int = 800, h: int = 600) -> dict:
    from effects import weather as W
    out = {}
    with seeded(seed, QT_MODULES):
        for name, cls, steps in (("Rain", W.RainEffect, 40), ("Snow", W.SnowEffect, 40), ("Fog", W.FogEffect, 60)):
            eff = cls(w, h)
            eff.resize(w, h)  # FireworksCanvas.set_weather does this right after creating the effect
            for _ in range(steps):
                eff.update()
            out[name] = {"steps": steps,
                         "particles": [[p.x, p.y, p.speed] for p in eff.particles],
                         "layers": [[L.x, L.y, L.width, L.height, L.velocity, L.opacity, L.control_points]
                                    for L in getattr(eff, "fog_layers", [])]}
        eff = W.LightningEffect(w, h)
        eff.resize(w, h)
        strikes = []
        for step in range(600):
            eff.update()
            for b in eff.active_bolts:
                if b.current_life == b.lifetime:
                    strikes.append({"step": step, "bolt": _bolt(b)})
        out["Lightning"] = {"steps": 600, "strikes": strikes, "next_strike": eff.next_strike,
                            "flash": eff.flash_intensity}
    return out


def _bolt(b) -> dict:
    return {"segments": [[*s, *e] for s, e in b.segments], "lifetime": b.lifetime,
            "branches": [_bolt(x) for x in b.branches]}


def background_scenes(seed: int = 5, w: int = 800, h: int = 600) -> dict:
    from effects import backgrounds as B
    out = {}
    with seeded(seed, QT_MODULES):
        bg = B.NightSkyBackground(w, h)
        out["Night Sky"] = {"stars": [[x, y, b] for (x, y), b in zip(bg.stars, bg.star_brightness)]}
        bg = B.CityscapeBackground(w, h)
        out["Cityscape"] = {"buildings": bg.buildings, "windows": bg.windows}
        bg = B.MountainsBackground(w, h)
        out["Mountains"] = {"mountains": bg.mountains, "stars": bg.stars}
        bg = B.BeachBackground(w, h)
        out["Beach"] = {"stars": bg.stars, "waves": bg.waves, "palm_trees": bg.palm_trees}
        bg = B.ForestBackground(w, h)
        out["Forest"] = {"stars": bg.stars, "trees": bg.trees, "fireflies": bg.fireflies}
    return out


def random_colors(seed: int = 9, n: int = 24) -> list:
    from utils.color import ColorUtils
    with seeded(seed, QT_MODULES):
        cols = [ColorUtils.random_color(min_saturation=0.7, min_value=0.8) for _ in range(n)]  # as the canvas
    return [[c.red(), c.green(), c.blue()] for c in cols]


def glyphs_js() -> str:
    """web/static/fw_glyphs.js: the TextPattern glyphs of models/glyphs.py as an ES module."""
    from models.glyphs import COLS, GLYPHS, ROWS
    rows = "\n".join(f"  {json.dumps(k)}: {json.dumps(list(v))}," for k, v in GLYPHS.items())
    return ("// Generated from models/glyphs.py by scripts/make_js_fixtures.py: do not edit (tests/test_web.py checks it).\n"
            f"export const COLS = {COLS}, ROWS = {ROWS};\nexport const GLYPHS = {{\n{rows}\n}};\n")


def mulberry_stream(seed: int = 1, n: int = 16) -> list:
    r = PyRand(seed)
    return [r.random() for _ in range(n)]


def fixture(include_qt: bool | None = None) -> dict:
    """Everything the node tests compare against (written to tests/fixtures/fw_reference.json)."""
    config = {f.name: getattr(FireworkConfig, f.name) for f in fields(FireworkConfig) if not f.name.endswith("_COLOR")}
    data = {"mulberry32_seed1": mulberry_stream(), "config": config, "patterns": pattern_points(),
            "shows": [run_show(c) for c in SHOW_CASES]}
    if include_qt is None:
        include_qt = has_qt()
    if include_qt:
        data["qt"] = {"weather": weather_runs(), "backgrounds": background_scenes(), "colors": random_colors()}
    return data
