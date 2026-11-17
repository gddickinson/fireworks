"""Realistic scenery for the desktop realistic renderer: a QPainter port of web/static/fw_scenery.js.

`build_scenery(name, W, H, seed=7, time="night")` paints one background once per size (seeded: the same scene every
time, and the same noise/prng draws as the web version, so the desktop and web scenes look alike) into
  back  - opaque QImage (RGB32): sky, stars, Milky Way, distant terrain/skyline, water with reflections;
  front - transparent QImage (ARGB32_Premultiplied): foreground silhouettes in front of the fireworks;
  mat   - material map (RGB32): red albedo lit by bursts, green water, blue open sky;
plus `horizon` (fraction of the height where shells are launched: the sim's horizon), `water` (px or None),
`fireflies` ([x frac, y frac, phase, speed]), `time` ("night" | "dusk", the blue hour: effects/scenery_sky.py), the
positions used by the scene plug-ins (effects/scene_fx.py; scenery px): `chimneys`, `beacons`, `boats`, `turbines`,
`lighthouse`, and `bridge` (River Bridge: deck height in m, models.director niagara_height).
Scenes: the original five + "None" here (SCENERY_HORIZON, unchanged at night), the seven newer ones in
effects/scenery_more.py (Harbour, River Bridge, Waterfront) and effects/scenery_land.py (Desert, Snowy Village,
Castle, Countryside); SCENE_HORIZON has them all.  Primitives: scenery_parts.py, scenery_sky.py, scenery_city.py,
scenery_props.py, scenery_houses.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QImage

from effects.scenery_city import skyline, street_lights
from effects.scenery_land import LAND_SCENES
from effects.scenery_more import WATER_SCENES
from effects.scenery_noise import fbm1, prng
from effects.scenery_parts import (Layer, broadleaf, conifer, draw_ops, fill_path, jround, mat, palm, range_, rgb,
                                   snow, water)
from effects.scenery_props import surf, tree_line
from effects.scenery_sky import dark_sky, starry

SCENERY_HORIZON = {"None": 0.92, "Night Sky": 0.86, "Cityscape": 0.7, "Mountains": 0.76, "Beach": 0.66,
                   "Forest": 0.82}
NEW_SCENERY_HORIZON = {"Harbour": 0.72, "River Bridge": 0.74, "Waterfront": 0.7, "Desert": 0.8,
                       "Snowy Village": 0.76, "Castle": 0.8, "Countryside": 0.8}
SCENE_HORIZON = {**SCENERY_HORIZON, **NEW_SCENERY_HORIZON}
TIMES = ("night", "dusk")


@dataclass
class Scenery:
    name: str
    W: int
    H: int
    back: QImage
    front: QImage
    mat: QImage
    horizon: float
    water: float | None = None
    fireflies: list = field(default_factory=list)
    time: str = "night"
    chimneys: list = field(default_factory=list)
    beacons: list = field(default_factory=list)
    boats: list = field(default_factory=list)
    turbines: list = field(default_factory=list)
    lighthouse: tuple | None = None
    bridge: float | None = None
    moon: dict | None = None        # set by the Moon sky effect (effects/sky_fx.py), view px


def build_scenery(name: str, W: int, H: int, seed: int = 7, time: str = "night") -> Scenery:
    W, H = max(2, jround(W)), max(2, jround(H))
    if name not in PAINTERS:
        name = "None"
    c = Layer(W, H, QImage.Format.Format_RGB32, 0xFF000000)
    f = Layer(W, H)
    m = Layer(W, H, QImage.Format.Format_RGB32, mat(0, 0, 1))
    S = Scenery(name, W, H, c.img, f.img, m.img, SCENE_HORIZON[name], time="dusk" if time == "dusk" else "night")
    PAINTERS[name](S, c, f, m, seed)
    for layer in (c, f, m):
        layer.end()
    return S


def _fill(layer, path, col):
    fill_path(layer, path, col)


# --- the scenes -----------------------------------------------------------------------------------------------
def _none(S, c, f, m, seed):
    W, H, hz = S.W, S.H, S.horizon * S.H
    dark_sky(S, c, H, (30, 34, 60), glowH=0.2)
    starry(S, c, seed, H, milky=0.8)
    m.p.fillRect(QRectF(0, hz, W, H - hz), mat(0.15))


def _night_sky(S, c, f, m, seed):
    """Open country: distant hills, a meadow, a few trees."""
    W, H, hz = S.W, S.H, S.horizon * S.H
    dark_sky(S, c, hz, (46, 52, 70), glowH=0.22)
    starry(S, c, seed, hz, milky=1.1)
    range_(c, m, W, H, seed + 1, dict(base=S.horizon + 0.005, amp=0.05, rough=2.5, sharp=0.3),
           (26, 32, 46), (14, 18, 28), 0.25)
    range_(c, m, W, H, seed + 2, dict(base=S.horizon + 0.03, amp=0.035, rough=4, sharp=0.2),
           (12, 16, 22), (6, 8, 12), 0.3)
    range_(f, m, W, H, seed + 3, dict(base=0.95, amp=0.06, rough=1.4, sharp=0.1), (7, 9, 10), (3, 4, 5), 0.35)
    rnd = prng(seed + 4)
    for i in range(5):
        x = rnd() * W
        y = H * (0.93 - 0.05 * float(fbm1(seed + 3, x / W * 1.4, 5))) + 6
        h = H * (0.08 + rnd() * 0.08)
        kind = conifer if rnd() < 0.5 else broadleaf
        rnd()          # the web draws the material's tree type separately; the draw is kept, the shape is shared
        path = kind(x, y, h, prng(seed + 40 + i))
        _fill(f, path, rgb(4, 5, 6))
        _fill(m, path, mat(0.2))


def _cityscape(S, c, f, m, seed):
    """A harbour: skyline on the far bank, river in front."""
    W, H, wl = S.W, S.H, S.horizon * S.H
    dark_sky(S, c, wl, (120, 70, 40), low=(30, 26, 36), glowH=0.38)
    starry(S, c, seed, wl, n=0.25, milky=0)
    skyline(c, m, W, H, wl, seed + 1, far=True, S=S)
    skyline(c, m, W, H, wl, seed + 2, far=False, S=S)
    street_lights(c, W, H, wl, seed + 3)
    water(c, m, W, H, wl, seed + 4, tint=(10, 12, 22), reflect=0.7)
    S.water = wl
    f.p.fillRect(QRectF(0, H * 0.965, W, H), rgb(3, 3, 5))      # quay edge
    m.p.fillRect(QRectF(0, H * 0.965, W, H), mat(0.3))


def _mountains(S, c, f, m, seed):
    """Alpine lake under ranges fading into haze."""
    W, H, wl = S.W, S.H, S.horizon * S.H
    dark_sky(S, c, wl, (40, 50, 80), glowH=0.25)
    starry(S, c, seed, wl, milky=1.2, angle=-0.9, cx=0.4)
    haze = [(38, 44, 66), (28, 33, 52), (18, 22, 36), (10, 12, 20)]
    specs = [dict(base=0.72, amp=0.4, rough=3.2, sharp=0.85), dict(base=0.74, amp=0.28, rough=4.5, sharp=0.8),
             dict(base=0.76, amp=0.15, rough=6, sharp=0.6)]
    for i, sp in enumerate(specs):
        top = haze[i]
        bot = tuple(v * 0.55 for v in top)
        r = range_(c, m, W, H, seed + 10 + i, sp, top, bot, 0.5 - i * 0.1, wl)
        if i < 2:
            snow(c, m, r, H * (sp["base"] - sp["amp"] * 0.5), H * 0.06, seed + 20 + i)
    tree_line(c, m, W, H, wl, seed + 30, H * 0.025, (8, 10, 14))
    water(c, m, W, H, wl, seed + 5, tint=(8, 12, 22), reflect=0.6)
    S.water = wl
    range_(f, m, W, H, seed + 6, dict(base=1.0, amp=0.06, rough=1.5, sharp=0.2), (5, 6, 8), (2, 2, 3), 0.25)
    rnd = prng(seed + 7)
    for i in range(9):
        x = (rnd() * 0.18 if i < 5 else 0.82 + rnd() * 0.18) * W
        h = H * (0.18 + rnd() * 0.16)
        path = conifer(x, H * 1.01, h, prng(seed + 70 + i))
        _fill(f, path, rgb(3, 4, 5))
        _fill(m, path, mat(0.15))


def _beach(S, c, f, m, seed):
    """The sea to the horizon, a headland, palms on the sand."""
    W, H, wl = S.W, S.H, S.horizon * S.H
    dark_sky(S, c, wl, (50, 46, 70), low=(18, 22, 44), glowH=0.2)
    starry(S, c, seed, wl, milky=1.0, angle=-0.35, cx=0.3)
    for k in (c, m):                                            # headland on the left
        k.p.save()
        k.p.setClipRect(QRectF(0, 0, W * 0.4, H))
    head = dict(base=S.horizon + 0.004, amp=0.1, rough=1.6, sharp=0.5,
                taper=lambda u: (1 - (u / 0.4) ** 2).clip(min=0))
    range_(c, m, W, H, seed + 1, head, (18, 22, 34), (10, 12, 20), 0.25, wl + 1)
    c.p.restore()
    m.p.restore()
    water(c, m, W, H, wl, seed + 2, tint=(8, 14, 30), reflect=0.65)
    S.water = wl
    surf(c, W, H, wl, seed + 3)
    range_(f, m, W, H, seed + 4, dict(base=1.0, amp=0.12, rough=0.7, sharp=0.0), (26, 22, 22), (10, 9, 10), 0.55)
    rnd = prng(seed + 5)
    for i in range(3):
        x = (0.05 + rnd() * 0.12 if i == 0 else 0.8 + rnd() * 0.15 if i == 1 else 0.18 + rnd() * 0.1) * W
        h = H * (0.38 + rnd() * 0.2)
        lean = (1 if x < W / 2 else -1) * (0.3 + rnd() * 0.4)
        ops = palm(x, H * 1.02, h, lean, prng(seed + 50 + i))
        draw_ops(f, ops, rgb(4, 4, 6))
        draw_ops(m, ops, mat(0.15))


def _forest(S, c, f, m, seed):
    """A clearing in a conifer forest, fireflies."""
    W, H, hz = S.W, S.H, S.horizon * S.H
    dark_sky(S, c, hz, (36, 44, 60), glowH=0.2)
    starry(S, c, seed, hz, milky=1.2, angle=-0.7, cx=0.55)
    tree_line(c, m, W, H, hz - H * 0.02, seed + 1, H * 0.06, (26, 32, 44))
    tree_line(c, m, W, H, hz, seed + 2, H * 0.08, (14, 18, 24))
    tree_line(c, m, W, H, hz + H * 0.03, seed + 3, H * 0.1, (6, 8, 10))
    c.p.fillRect(QRectF(0, hz + H * 0.03, W, H), rgb(4, 6, 6))
    m.p.fillRect(QRectF(0, hz + H * 0.03, W, H), mat(0.25))
    rnd = prng(seed + 4)
    for i in range(10):
        side = rnd() * 0.12 if i % 2 else 0.88 + rnd() * 0.12
        x, h = side * W, H * (0.3 + rnd() * 0.35)
        path = conifer(x, H * 1.02, h, prng(seed + 60 + i))
        _fill(f, path, rgb(2, 3, 3))
        _fill(m, path, mat(0.12))
    for _ in range(jround(W / 60)):
        S.fireflies.append([rnd(), S.horizon + 0.04 + rnd() * 0.12, rnd() * 6.28, 0.5 + rnd()])


PAINTERS = {"None": _none, "Night Sky": _night_sky, "Cityscape": _cityscape, "Mountains": _mountains,
            "Beach": _beach, "Forest": _forest}
PAINTERS.update(WATER_SCENES)
PAINTERS.update(LAND_SCENES)
