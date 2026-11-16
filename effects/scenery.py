"""Realistic scenery for the desktop realistic renderer: a QPainter port of web/static/fw_scenery.js.

`build_scenery(name, W, H, seed=7)` paints one background once per size (seeded: the same scene every time, and the
same noise/prng draws as the web version, so the desktop and web scenes look alike) into
  back  - opaque QImage (RGB32): sky, stars, Milky Way, distant terrain/skyline, water with reflections;
  front - transparent QImage (ARGB32_Premultiplied): foreground silhouettes in front of the fireworks;
  mat   - material map (RGB32): red albedo lit by bursts, green water, blue open sky;
plus `horizon` (fraction of the height where shells are launched: the sim's horizon), `water` (px or None) and
`fireflies` ([x frac, y frac, phase, speed]).  Primitives live in effects/scenery_parts.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QImage, QPainterPath, QPen, QRadialGradient

from effects.scenery_noise import fbm1, hash, prng
from effects.scenery_parts import (Layer, broadleaf, conifer, draw_ops, fill_path, jround, mat, milky_way, palm,
                                   range_, rgb, sky, snow, stars, vgrad, water)

SCENERY_HORIZON = {"None": 0.92, "Night Sky": 0.86, "Cityscape": 0.7, "Mountains": 0.76, "Beach": 0.66,
                   "Forest": 0.82}


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


def build_scenery(name: str, W: int, H: int, seed: int = 7) -> Scenery:
    W, H = max(2, jround(W)), max(2, jround(H))
    if name not in PAINTERS:
        name = "None"
    c = Layer(W, H, QImage.Format.Format_RGB32, 0xFF000000)
    f = Layer(W, H)
    m = Layer(W, H, QImage.Format.Format_RGB32, mat(0, 0, 1))
    S = Scenery(name, W, H, c.img, f.img, m.img, SCENERY_HORIZON[name])
    PAINTERS[name](S, c, f, m, seed)
    for layer in (c, f, m):
        layer.end()
    return S


def _dark_sky(c, W, H, horizon, glow, low=(12, 20, 40), glowH=0.3):
    sky(c, W, H, (1, 2, 8), (4, 8, 22), low, horizon, glow, glowH)


def _starry(S, c, seed, horizon, n=1.0, milky=1.0, angle=-0.55, cx=0.62):
    W, H, rnd = S.W, S.H, prng(seed)
    dist = milky_way(c, W, H, seed, horizon, angle, cx, milky) if milky > 0 else None
    stars(c, W, H, rnd, jround(W * H / 260 * n), horizon, milky=dist)


def _fill(layer, path, col):
    fill_path(layer, path, col)


# --- the scenes -----------------------------------------------------------------------------------------------
def _none(S, c, f, m, seed):
    W, H, hz = S.W, S.H, S.horizon * S.H
    _dark_sky(c, W, H, H, (30, 34, 60), glowH=0.2)
    _starry(S, c, seed, H, milky=0.8)
    m.p.fillRect(QRectF(0, hz, W, H - hz), mat(0.15))


def _night_sky(S, c, f, m, seed):
    """Open country: distant hills, a meadow, a few trees."""
    W, H, hz = S.W, S.H, S.horizon * S.H
    _dark_sky(c, W, H, hz, (46, 52, 70), glowH=0.22)
    _starry(S, c, seed, hz, milky=1.1)
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
    _dark_sky(c, W, H, wl, (120, 70, 40), low=(30, 26, 36), glowH=0.38)
    _starry(S, c, seed, wl, n=0.25, milky=0)
    _skyline(c, m, W, H, wl, seed + 1, far=True)
    _skyline(c, m, W, H, wl, seed + 2, far=False)
    _street_lights(c, W, H, wl, seed + 3)
    water(c, m, W, H, wl, seed + 4, tint=(10, 12, 22), reflect=0.7)
    S.water = wl
    f.p.fillRect(QRectF(0, H * 0.965, W, H), rgb(3, 3, 5))      # quay edge
    m.p.fillRect(QRectF(0, H * 0.965, W, H), mat(0.3))


def _mountains(S, c, f, m, seed):
    """Alpine lake under ranges fading into haze."""
    W, H, wl = S.W, S.H, S.horizon * S.H
    _dark_sky(c, W, H, wl, (40, 50, 80), glowH=0.25)
    _starry(S, c, seed, wl, milky=1.2, angle=-0.9, cx=0.4)
    haze = [(38, 44, 66), (28, 33, 52), (18, 22, 36), (10, 12, 20)]
    specs = [dict(base=0.72, amp=0.4, rough=3.2, sharp=0.85), dict(base=0.74, amp=0.28, rough=4.5, sharp=0.8),
             dict(base=0.76, amp=0.15, rough=6, sharp=0.6)]
    for i, sp in enumerate(specs):
        top = haze[i]
        bot = tuple(v * 0.55 for v in top)
        r = range_(c, m, W, H, seed + 10 + i, sp, top, bot, 0.5 - i * 0.1, wl)
        if i < 2:
            snow(c, m, r, H * (sp["base"] - sp["amp"] * 0.5), H * 0.06, seed + 20 + i)
    _tree_line(c, m, W, H, wl, seed + 30, H * 0.025, (8, 10, 14))
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
    _dark_sky(c, W, H, wl, (50, 46, 70), low=(18, 22, 44), glowH=0.2)
    _starry(S, c, seed, wl, milky=1.0, angle=-0.35, cx=0.3)
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
    _surf(c, W, H, wl, seed + 3)
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
    _dark_sky(c, W, H, hz, (36, 44, 60), glowH=0.2)
    _starry(S, c, seed, hz, milky=1.2, angle=-0.7, cx=0.55)
    _tree_line(c, m, W, H, hz - H * 0.02, seed + 1, H * 0.06, (26, 32, 44))
    _tree_line(c, m, W, H, hz, seed + 2, H * 0.08, (14, 18, 24))
    _tree_line(c, m, W, H, hz + H * 0.03, seed + 3, H * 0.1, (6, 8, 10))
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


# --- helpers --------------------------------------------------------------------------------------------------
def _tree_line(c, m, W, H, y, seed, h, col):
    rnd, n = prng(seed), jround(W / (h * 0.22))
    c.p.fillRect(QRectF(0, y - h * 0.15, W, h * 0.2), rgb(*col))
    m.p.fillRect(QRectF(0, y - h * 0.15, W, h * 0.2), mat(0.2))
    cp, mp, cc, mc = c.p, m.p, rgb(*col), mat(0.2)
    cp.setPen(Qt.PenStyle.NoPen)
    mp.setPen(Qt.PenStyle.NoPen)
    for i in range(n):
        x = (i + rnd()) * W / n
        th = h * (0.5 + rnd() * 0.7) * (0.7 + 0.6 * float(fbm1(seed, x / W * 3, 3)))
        path = conifer(x, y + 1, th, prng(seed * 1000 + i))
        cp.setBrush(cc)
        cp.drawPath(path)
        mp.setBrush(mc)
        mp.drawPath(path)


def _skyline(c, m, W, H, wl, seed, far):
    """City skyline on the far bank at wl. Far: lower, hazier, tiny windows. Near: towers with roof details."""
    rnd, sc = prng(seed), H / 800
    centre = 0.3 + rnd() * 0.4
    x = -rnd() * 30 * sc
    while x < W:
        w = (14 + rnd() * 30 if far else 22 + rnd() * 48) * sc
        d = (x / W - centre) / 0.28
        cluster = math.exp(-d * d)
        if far:
            h = (30 + rnd() * 50 + 90 * cluster * rnd()) * sc
        else:
            h = (24 + rnd() * 50 + 170 * cluster * rnd() ** 0.7) * sc
        if not far and rnd() < 0.12:
            h *= 0.35
        _building(c, m, x, wl, w, h, rnd, far, sc)
        x += w + (rnd() * 8 * sc if rnd() < 0.2 else 0)


def _building(c, m, x, base, w, h, rnd, far, sc):
    p, top = c.p, base - h
    col = (24, 24, 36) if far else (9, 10, 16)
    p.fillRect(QRectF(x, top, w, h), QBrush(vgrad(top, base, [(0, rgb(*(v * 1.25 for v in col))), (1, rgb(*col))])))
    m.p.fillRect(QRectF(x, top, w, h), mat(0.25 if far else 0.35))
    roof, r = top, rnd()                                        # roof details
    if not far and r < 0.3 and h > 120 * sc:                    # setbacks
        w2, h2, w3, h3 = w * 0.7, h * 0.12, w * 0.4, h * 0.08
        p.fillRect(QRectF(x + (w - w2) / 2, top - h2, w2, h2), rgb(*col))
        p.fillRect(QRectF(x + (w - w3) / 2, top - h2 - h3, w3, h3), rgb(*col))
        m.p.fillRect(QRectF(x + (w - w2) / 2, top - h2, w2, h2), mat(0.35))
        roof = top - h2 - h3
    elif not far and r < 0.45 and h > 150 * sc:                 # spire
        path = QPainterPath()
        path.moveTo(x + w * 0.3, top)
        path.lineTo(x + w / 2, top - h * 0.22)
        path.lineTo(x + w * 0.7, top)
        path.closeSubpath()
        _fill(c, path, rgb(*col))
        roof = top - h * 0.22
    elif r < 0.65:                                              # plant room / water tank
        p.fillRect(QRectF(x + w * (0.1 + rnd() * 0.4), top - 6 * sc, w * 0.3, 6 * sc), rgb(*col))
    if not far and (r > 0.85 or h > 220 * sc):                  # antenna with a red aviation light
        ax, ay = x + w / 2, roof - 26 * sc
        p.fillRect(QRectF(ax - sc * 0.6, ay, 1.2 * sc, 26 * sc), rgb(20, 20, 26))
        p.setBrush(rgb(255, 40, 30, 0.9))
        p.drawEllipse(QPointF(ax, ay), 1.6 * sc, 1.6 * sc)
        g = QRadialGradient(QPointF(ax, ay), 9 * sc)
        g.setColorAt(0, rgb(255, 40, 30, 0.35))
        g.setColorAt(1, rgb(255, 40, 30, 0))
        p.fillRect(QRectF(ax - 9 * sc, roof - 35 * sc, 18 * sc, 18 * sc), QBrush(g))
    cw, chh = (2.2 if far else 3.2) * sc, (3.2 if far else 4.4) * sc
    lit = 0.06 + rnd() * (0.2 if far else 0.32)
    warm, floor_lit = rnd() < 0.7, rnd() < 0.3
    a0 = 0.35 if far else 0.55
    fy = top + chh
    while fy < base - chh * 1.5:
        whole = floor_lit and rnd() < 0.15
        fx = x + cw * 0.7
        while fx < x + w - cw * 1.2:
            if whole or rnd() < lit:
                if warm:
                    t = (255, 196, 120) if rnd() < 0.85 else (190, 215, 255)
                else:
                    t = (200, 225, 255) if rnd() < 0.7 else (255, 210, 150)
                p.fillRect(QRectF(fx, fy, cw, chh * 0.75), rgb(*t, a0 + rnd() * 0.4))
            fx += cw * 1.7
        fy += chh * 1.6


def _street_lights(c, W, H, wl, seed):
    rnd, sc, p = prng(seed), H / 800, c.p
    x = rnd() * 20 * sc
    while x < W:
        y, r = wl - (2 + rnd() * 3) * sc, (6 + rnd() * 6) * sc
        col = (255, 170, 80) if rnd() < 0.75 else (220, 235, 255)
        g = QRadialGradient(QPointF(x, y), r)
        g.setColorAt(0, rgb(*col, 0.9))
        g.setColorAt(0.15, rgb(*col, 0.35))
        g.setColorAt(1, rgb(*col, 0))
        p.fillRect(QRectF(x - r, y - r, 2 * r, 2 * r), QBrush(g))
        x += (14 + rnd() * 18) * sc


def _surf(c, W, H, wl, seed):
    """Faint foam lines catching the sky light."""
    sc, p = H / 800, c.p
    for i in range(6):
        y, a = wl + (H - wl) * (0.25 + i * 0.13), 0.05 + i * 0.015
        path = QPainterPath()
        for k, x in enumerate(range(0, W + 1, 8)):
            yy = y + math.sin(x / (60 * sc) + i * 1.7) * 3 * sc + (hash(seed, x, i) - 0.5) * 2 * sc
            path.lineTo(x, yy) if k else path.moveTo(x, yy)
        p.setPen(QPen(rgb(160, 175, 210, a), (1 + i * 0.5) * sc))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
