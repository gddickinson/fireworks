"""Land scenes of the realistic scenery: a QPainter/numpy port of web/static/fw_scenery_land.js.

Desert dunes and mesas under a clear Milky Way, a snowy village (smoking chimneys, a church), a floodlit castle on a
hill above a small town, and countryside with fields, a church spire and wind turbines.  Shells launch from behind
the village / hill / far ridge (the front layer hides the launch points).  Painter signature: (S, c, f, m, seed)
with c/f/m the back/front/material layers (see effects/scenery.py).  Same prng draws as the web.
"""
from __future__ import annotations

import math

import numpy as np

from effects.scenery_city import glow
from effects.scenery_draw import fill, fill_rect, path, poly, polyline, stroke, upper_half
from effects.scenery_houses import castle as castle_, church, cottage, tent, turbine
from effects.scenery_noise import fbm1, prng
from effects.scenery_parts import broadleaf, conifer, jround, mat, range_, rgb, ridge_path, vgrad
from effects.scenery_props import (dunes, fields, fill_ridge, hill_line, mesa_line, oak, ridge_y, size_scale,
                                   snowy_conifer, tree_line)
from effects.scenery_sky import dark_sky, starry, tone


def _lights(S, c, x0, x1, y0, y1, n, sc, seed, ground=None) -> None:
    """Small houses with lit windows scattered over a band (y0..y1 px): distant village / town lights."""
    rnd = prng(seed)
    house = rgb(*tone(S, (14, 14, 20), 0.5))
    for _ in range(n):
        x = x0 + rnd() * (x1 - x0)
        y = max(ground(x) + 3 * sc, y0 + rnd() * (y1 - y0)) if ground else y0 + rnd() * (y1 - y0)
        fill_rect(c, x - 3 * sc, y - 4 * sc, 7 * sc, 4 * sc, house)
        if rnd() < 0.7:
            g = 185 + rnd() * 30
            fill_rect(c, x, y - 2.8 * sc, 1.5 * sc, 1.8 * sc, rgb(255, g, 110, 0.6 + rnd() * 0.35))
        if rnd() < 0.08:
            glow(c, x, y - 2 * sc, 7 * sc, (255, 170, 90), 0.5)


def desert(S, c, f, m, seed) -> None:
    """Dunes and mesas under a clear, dark sky; a glowing tent in a hollow."""
    W, H = S.W, S.H
    hz, sc = S.horizon * H, size_scale(S)
    dark_sky(S, c, hz, (40, 36, 52), low=(16, 18, 34), glowH=0.14, sun_x=0.75)
    starry(S, c, seed, hz, n=1.5, milky=1.6, angle=-1.15, cx=0.48)
    mesa = mesa_line(W, H, seed + 1, base=S.horizon + 0.004, amp=0.13, rough=2.2)
    fill_ridge(c, W, H, mesa, vgrad(H * (S.horizon - 0.13), hz, [(0, rgb(*tone(S, (44, 38, 50), 0.9))),
                                                                 (1, rgb(*tone(S, (20, 18, 28), 0.9)))]))
    fill_ridge(m, W, H, mesa, mat(0.3))
    dunes(c, m, W, H, seed + 2, base=S.horizon + 0.03, amp=0.05, waves=4.5, lit=tone(S, (40, 34, 38), 0.7),
          shade=tone(S, (16, 15, 22), 0.7))
    mid = dunes(f, m, W, H, seed + 4, base=S.horizon + 0.1, amp=0.1, waves=2.5, lit=tone(S, (50, 40, 40), 0.4),
                shade=tone(S, (12, 11, 15), 0.4), albedo=0.55)
    tx = W * (0.3 + prng(seed + 3)() * 0.4)
    ty = ridge_y(mid, tx)
    x = tx - 60 * sc
    while x < tx + 60 * sc:                                     # in a hollow (the bound moves with tx, as in JS)
        if ridge_y(mid, x) > ty:
            ty, tx = ridge_y(mid, x), x
        x += 3
    tent(f, m, tx, ty + 3 * sc, sc * 1.5)
    near = dunes(f, m, W, H, seed + 5, base=1.02, amp=0.13, waves=1.6, lit=tone(S, (42, 34, 34), 0.2),
                 shade=tone(S, (8, 7, 10), 0.2), albedo=0.6)
    rnd = prng(seed + 6)                                        # shrubs and a few rocks on the near dune
    for _ in range(9):
        x = rnd() * W
        y = ridge_y(near, x) + (4 + rnd() * 30) * sc
        if rnd() < 0.6:
            for k, col in ((f, rgb(6, 6, 8)), (m, mat(0.3))):
                twigs = path()
                for j in range(9):
                    a, ln = -math.pi * (0.15 + 0.7 * j / 8), (6 + rnd() * 9) * sc
                    twigs.moveTo(x, y)
                    twigs.lineTo(x + math.cos(a) * ln, y + math.sin(a) * ln)
                stroke(k, twigs, col, 1.2 * sc)
        else:
            for k, col in ((f, rgb(6, 6, 8)), (m, mat(0.3))):
                rx, ry = (6 + rnd() * 8) * sc, (3 + rnd() * 4) * sc
                rock = upper_half(path(), x, y, rx, ry)
                rock.closeSubpath()
                fill(k, rock, col)


def snowy_village(S, c, f, m, seed) -> None:
    """Cottages in snow, a church, smoking chimneys, snow-laden conifers, lamp posts."""
    W, H = S.W, S.H
    hz, sc, snow_c = S.horizon * H, size_scale(S), tone(S, (92, 100, 128), 0.3)
    dark_sky(S, c, hz, (60, 62, 84), low=(22, 28, 50), glowH=0.22)
    starry(S, c, seed, hz, n=0.9, milky=0.9, angle=-0.6, cx=0.7)
    range_(c, m, W, H, seed + 1, dict(base=S.horizon - 0.03, amp=0.16, rough=2.6, sharp=0.55),
           tone(S, (74, 82, 110), 0.9), tone(S, (36, 42, 64), 0.9), 0.75, hz)
    tree_line(c, m, W, H, hz - H * 0.01, seed + 2, H * 0.035, tone(S, (16, 20, 30), 0.8))
    range_(c, m, W, H, seed + 3, dict(base=S.horizon + 0.005, amp=0.025, rough=1.5, sharp=0.1),
           tone(S, (64, 70, 96), 0.6), tone(S, (40, 46, 68), 0.6), 0.8)
    rnd = prng(seed + 4)
    slope = dict(base=0.9, amp=0.07, rough=1.2, sharp=0.1)    # village slope in front (hides the launch line)
    back = range_(f, m, W, H, seed + 5, {**slope, "base": S.horizon + 0.06, "amp": 0.04},
                  tone(S, (62, 68, 94), 0.4), tone(S, (44, 50, 72), 0.4), 0.8)
    cx = W * (0.45 + rnd() * 0.15)
    x = rnd() * 30 * sc
    while x < W:                                                # back row of cottages along the slope
        if abs(x - cx) >= 80 * sc:
            w = (26 + rnd() * 14) * sc
            cottage(S, f, m, x, ridge_y(back, x + w / 2) + 3 * sc, w, (12 + rnd() * 5) * sc, rnd, sc, snow=True,
                    spill=10 * sc, haze=0.4)
        x += (46 + rnd() * 40) * sc
    church(S, f, m, cx, ridge_y(back, cx) + 4 * sc, sc * 1.1, rnd, snow=True, haze=0.4)
    front = range_(f, m, W, H, seed + 6, slope, tone(S, (70, 76, 102), 0.2), tone(S, (30, 34, 52), 0.2), 0.85)
    for i in range(4):                                          # front row: bigger cottages
        x, w = W * (0.06 + i * 0.25 + rnd() * 0.08), (48 + rnd() * 20) * sc
        cottage(S, f, m, x, ridge_y(front, x + w / 2) + 4 * sc, w, (22 + rnd() * 8) * sc, rnd, sc, snow=True,
                spill=22 * sc, haze=0.1)
    for i in range(8):                                          # snow-laden conifers at the sides
        x, h = (rnd() * 0.12 if i % 2 else 0.88 + rnd() * 0.12) * W, H * (0.16 + rnd() * 0.16)
        snowy_conifer(f, m, x, H * 1.01, h, seed + 70 + i, tone(S, (6, 8, 12), 0.1), snow_c)
    for i in range(6):                                          # lamp posts along the lane
        x = W * (0.1 + i * 0.16 + rnd() * 0.04)
        y = ridge_y(front, x) + 26 * sc
        fill_rect(f, x - 0.8 * sc, y - 26 * sc, 1.6 * sc, 26 * sc, rgb(8, 8, 12))
        glow(f, x, y - 27 * sc, 20 * sc, (255, 190, 120), 0.5, 0.1)
        glow(f, x, y, 26 * sc, (255, 190, 120), 0.12, 0.3)


def castle(S, c, f, m, seed) -> None:
    """A floodlit castle on a hill above a small town, a road of lamps winding up to the gate."""
    W, H = S.W, S.H
    hz, sc, rnd = S.horizon * H, size_scale(S), prng(seed + 5)
    dark_sky(S, c, hz, (64, 52, 64), low=(20, 22, 40), glowH=0.26, sun_x=0.85)
    starry(S, c, seed, hz, n=0.9, milky=0.9, angle=-0.35, cx=0.78)
    range_(c, m, W, H, seed + 1, dict(base=S.horizon + 0.004, amp=0.1, rough=2.2, sharp=0.5),
           tone(S, (28, 32, 48), 0.9), tone(S, (16, 18, 28), 0.9), 0.25)
    range_(c, m, W, H, seed + 2, dict(base=S.horizon + 0.03, amp=0.05, rough=3.5, sharp=0.4),
           tone(S, (14, 16, 24), 0.8), tone(S, (8, 9, 14), 0.8), 0.3)
    cxf = 0.36 + rnd() * 0.12
    peak = min(0.3, 0.2 + 0.06 * W / H)
    hill = hill_line(W, H, seed + 3, base=1.0, amp=1.0 - (S.horizon - peak), cx=cxf, width=0.42)
    fill_ridge(f, W, H, hill, vgrad(H * (S.horizon - peak), H, [(0, rgb(*tone(S, (30, 26, 26), 0.3))),
                                                                (0.35, rgb(*tone(S, (14, 14, 18), 0.3))),
                                                                (1, rgb(5, 5, 7))]))
    fill_ridge(m, W, H, hill, mat(0.3))
    cx = W * cxf
    base = ridge_y(hill, cx) + 6 * sc
    p = f.p
    p.save()
    p.setClipPath(ridge_path(W, hill, H))
    glow(f, cx, base, 160 * sc, (255, 160, 90), 0.22, 0.2)      # floodlight spill on the summit
    rk = prng(seed + 8)                                         # rocky outcrops catching the light
    rock_col = tone(S, (34, 30, 30), 0.3)
    for _ in range(60):
        x = cx + (rk() - 0.5) * W * 0.5
        y = ridge_y(hill, x) + rk() * (H - ridge_y(hill, x)) * 0.6
        w = (6 + rk() * 18) * sc
        fill(f, poly([(x, y), (x + w, y + w * 0.25), (x + w * 0.3, y + w * 0.4)]), rgb(*rock_col, 0.25 + rk() * 0.25))
    p.restore()
    tree_col = rgb(*tone(S, (6, 6, 8), 0.2))
    for i in range(40):                                         # trees on the flanks
        x = cx + (-1 if rnd() < 0.5 else 1) * (0.08 + rnd() * 0.4) * W
        y, h = ridge_y(hill, x) + (4 + rnd() * 60) * sc, (16 + rnd() * 22) * sc
        tree = broadleaf if rnd() < 0.6 else conifer
        shape = tree(x, y, h, prng(seed + 100 + i))
        fill(f, shape, tree_col)
        fill(m, shape, mat(0.25))
    castle_(S, f, m, cx, base, sc * 1.05, rnd)
    _lights(S, f, 0, W, H * 0.9, H * 1.0, jround(W / (9 * sc)), sc, seed + 7, lambda x: ridge_y(hill, x))
    t = 0.0
    while t < 1:                                                # lamps on the road winding up to the gate
        x = cx + math.sin(t * 7) * 60 * sc * (1 - t) + 30 * sc * (1 - t)
        y = H * 0.98 - t * (H * 0.98 - base - 4 * sc)
        if y >= ridge_y(hill, x):
            glow(f, x, y, 6 * sc, (255, 180, 100), 0.7, 0.15)
        t += 0.06


def countryside(S, c, f, m, seed) -> None:
    """Farmland, a church spire, a farm, wind turbines on the far ridge, a fence and a big oak in front."""
    W, H = S.W, S.H
    hz, sc, rnd = S.horizon * H, size_scale(S), prng(seed + 9)
    dark_sky(S, c, hz, (50, 52, 72), low=(18, 22, 40), glowH=0.22, sun_x=0.3)
    starry(S, c, seed, hz, n=1.1, milky=1.1, angle=-0.75, cx=0.32)
    far = range_(c, m, W, H, seed + 1, dict(base=S.horizon - 0.02, amp=0.07, rough=1.6, sharp=0.2),
                 tone(S, (28, 32, 46), 0.9), tone(S, (18, 21, 32), 0.9), 0.25, hz + H * 0.02)
    x = W * (0.05 + rnd() * 0.1)
    while x < W:
        turbine(S, c, m, x, ridge_y(far, x) + 2 * sc, (52 + rnd() * 18) * sc, sc)
        x += W * (0.09 + rnd() * 0.08)
    _lights(S, c, 0, W, hz - H * 0.005, hz + H * 0.01, jround(W / (40 * sc)), sc * 0.7, seed + 2)
    mid = range_(c, m, W, H, seed + 3, dict(base=S.horizon + 0.02, amp=0.05, rough=1.4, sharp=0.15),
                 tone(S, (20, 24, 30), 0.6), tone(S, (12, 15, 18), 0.6), 0.3)
    fields(c, m, W, H, mid, seed + 4, depth=H * 0.09, rows=3, col=tone(S, (26, 30, 34), 0.6), sc=sc)
    cxp, farm = W * (0.45 + rnd() * 0.15), W * (0.15 + rnd() * 0.12)
    church(S, c, m, cxp, ridge_y(mid, cxp + 35 * sc) + 10 * sc, sc * 0.7, rnd, haze=0.6)
    for i in range(3):
        x = farm + i * 32 * sc
        cottage(S, c, m, x, ridge_y(mid, x + 12 * sc) + 14 * sc, (22 + rnd() * 10) * sc, (10 + rnd() * 4) * sc,
                rnd, sc * 0.8, haze=0.6)
    S.chimneys.clear()
    near = range_(f, m, W, H, seed + 5, dict(base=0.98, amp=0.1, rough=1.1, sharp=0.1),
                  tone(S, (14, 16, 18), 0.2), tone(S, (5, 6, 7), 0.2), 0.35)
    x = rnd() * 20 * sc
    while x < W:                                                # fence posts along the near meadow
        y = ridge_y(near, x) + 26 * sc
        fill_rect(f, x - 1.6 * sc, y - 24 * sc, 3.2 * sc, 24 * sc, rgb(5, 5, 7))
        fill_rect(m, x - 1.6 * sc, y - 24 * sc, 3.2 * sc, 24 * sc, mat(0.3))
        x += 34 * sc
    xs = np.arange(0, W + 1, 6, dtype=np.float64)
    for d in (17, 8):                                           # two wires
        ys = [ridge_y(near, x) + 26 * sc - d * sc + float(fbm1(seed, x * 0.02, 2)) * 2 * sc for x in xs]
        stroke(f, polyline(xs, ys), rgb(30, 32, 40, 0.6), 0.6 * sc)
    tree = oak(W * 0.94, H * 1.02, H * 0.5, prng(seed + 11))    # a big oak at the side
    fill(f, tree, rgb(4, 5, 6))
    fill(m, tree, mat(0.2))


LAND_SCENES = {"Desert": desert, "Snowy Village": snowy_village, "Castle": castle, "Countryside": countryside}
