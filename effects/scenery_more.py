"""Waterside scenes of the realistic scenery: a QPainter port of web/static/fw_scenery_more.js.

A fishing harbour (hillside town, lighthouse, jetty, boats), a cable-stayed bridge over a city river (sets S.bridge,
the deck height in metres, for the niagara ground device), and a big-city waterfront on New Year's Eve (towers with
floodlit crowns, a ferris wheel, a crowd).  Shells launch from barges on the waterline.  Painter signature:
(S, c, f, m, seed) with c/f/m the back/front/material layers (see effects/scenery.py).  Same prng draws as the web.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QBrush, QPainter

from effects.scenery_city import cable_bridge, crown_tower, ferris_wheel, glow, skyline, street_lights
from effects.scenery_draw import ellipse, fill, fill_rect, path, poly
from effects.scenery_houses import boat, crowd, jetty, town_row
from effects.scenery_noise import prng
from effects.scenery_parts import jround, mat, range_, rgb, vgrad, water
from effects.scenery_props import light_reflection, ridge_y, size_scale
from effects.scenery_sky import dark_sky, starry, tone


def _hill_town(S, c, m, r, x0, x1, wl, sc, seed) -> None:
    """Hillside town: little houses with a lit window or two, denser towards the shore, and a winding lit road."""
    rnd = prng(seed)
    i, n = 0, (x1 - x0) / (3.2 * sc)
    house = rgb(*tone(S, (20, 20, 28), 0.6))
    while i < n:
        i += 1
        x = x0 + rnd() * (x1 - x0)
        top = ridge_y(r, x) + 8 * sc
        if top > wl - 10 * sc:
            continue
        y = wl - rnd() ** 1.8 * (wl - top)
        w, h = (5 + rnd() * 7) * sc, (4 + rnd() * 4) * sc
        fill_rect(c, x, y - h, w, h, house)
        fill(c, poly([(x - sc, y - h), (x + w / 2, y - h - w * 0.35), (x + w + sc, y - h)]), house)
        if rnd() < 0.55:
            fill_rect(c, x + w * 0.3, y - h * 0.6, 1.6 * sc, 2 * sc, rgb(255, 190, 110, 0.55 + rnd() * 0.4))
    px, t = x0 + (x1 - x0) * 0.2, 0.0                           # road lamps zig-zagging up the hill
    while t < 1:
        x = px + math.sin(t * 9 + seed) * (x1 - x0) * 0.12
        y = wl - t * (wl - ridge_y(r, x) - 14 * sc)
        if y < ridge_y(r, x) + 6 * sc:
            break
        glow(c, x, y, 5 * sc, (255, 175, 90), 0.7, 0.15)
        px += (x1 - x0) * 0.004
        t += 0.035


def harbour(S, c, f, m, seed) -> None:
    """A fishing harbour: hillside town, boats, a lit jetty, a lighthouse on the headland."""
    W, H = S.W, S.H
    wl, sc, rnd = S.horizon * H, size_scale(S), prng(seed + 9)
    dark_sky(S, c, wl, (90, 70, 64), low=(22, 24, 40), glowH=0.26, sun_x=0.8)
    starry(S, c, seed, wl, n=0.7, milky=0.55, angle=-0.4, cx=0.7)

    def taper(u):
        return np.where(u < 0.62, 1.0, np.maximum(0.08, 1 - (u - 0.62) / 0.25))
    hill = dict(base=S.horizon, amp=0.3, rough=1.4, sharp=0.3, taper=taper)
    range_(c, m, W, H, seed + 1, {**hill, "base": S.horizon - 0.04, "amp": 0.2, "rough": 2.2},
           tone(S, (30, 34, 52), 0.9), tone(S, (18, 20, 32), 0.9), 0.2, wl)
    r = range_(c, m, W, H, seed + 2, hill, tone(S, (18, 21, 32), 0.7), tone(S, (10, 11, 18), 0.7), 0.25, wl)
    _hill_town(S, c, m, r, 0, W * 0.72, wl - 14 * sc, sc, seed + 3)
    town_row(S, c, m, -5 * sc, W * 0.62, wl, sc, rnd)
    street_lights(c, W * 0.62, H, wl - 1 * sc, seed + 4, sc)
    lx, ly = W * 0.9, wl - 6 * sc                               # headland with a lighthouse on the right
    head = path()
    head.moveTo(W * 0.8, wl)
    head.quadTo(W * 0.86, ly - 4 * sc, lx, ly)
    head.lineTo(W + 2, ly + 2 * sc)
    head.lineTo(W + 2, wl)
    head.closeSubpath()
    fill(c, head, rgb(*tone(S, (12, 13, 20), 0.6)))
    fill_rect(m, W * 0.8, ly - 4 * sc, W * 0.2, wl - ly + 4 * sc, mat(0.25))
    fill(c, poly([(lx - 5 * sc, ly), (lx - 3 * sc, ly - 44 * sc), (lx + 3 * sc, ly - 44 * sc), (lx + 5 * sc, ly)]),
         rgb(*tone(S, (70, 70, 80), 0.5)))
    fill_rect(c, lx - 4.2 * sc, ly - 30 * sc, 8.4 * sc, 5 * sc, rgb(160, 30, 30, 0.8))
    fill_rect(c, lx - 3 * sc, ly - 50 * sc, 6 * sc, 6 * sc, rgb(255, 245, 210))
    fill(c, poly([(lx - 4 * sc, ly - 50 * sc), (lx, ly - 55 * sc), (lx + 4 * sc, ly - 50 * sc)]), rgb(30, 30, 36))
    glow(c, lx, ly - 47 * sc, 30 * sc, (255, 240, 200), 0.4, 0.1)
    S.lighthouse = (lx, ly - 47 * sc)
    water(c, m, W, H, wl, seed + 5, tint=(8, 12, 24), reflect=0.68)
    S.water = wl
    jy = wl + (H - wl) * 0.42
    lamps = jetty(S, c, m, -2, W * 0.4, jy, sc * 1.5, rnd)
    for i, (x, _) in enumerate(lamps):
        light_reflection(c, x, jy + 5 * sc, (H - jy) * 0.7, (255, 180, 100), sc, seed + 60 + i, 0.55)
    for i in range(7):                                          # moored boats off the town quay
        x, y = W * (0.06 + i * 0.085 + rnd() * 0.03), wl + (H - wl) * (0.1 + rnd() * 0.12)
        ln = (34 + rnd() * 26) * sc
        sail = rnd() < 0.6
        colour = tone(S, (44, 46, 56) if rnd() < 0.6 else (16, 18, 26), 0.4)
        top = boat(c, x, y, ln, sc, rnd, sail=sail, colour=colour)
        light_reflection(c, x, y + 2 * sc, (H - y) * 0.45, (255, 240, 210), sc, seed + 80 + i, 0.4)
        fill_rect(m, x - ln / 2, y + top[1], ln, -top[1], mat(0.3))
    for i in range(3):
        S.boats.append((W * (0.5 + i * 0.16 + rnd() * 0.05), wl + (H - wl) * (0.3 + i * 0.16 + rnd() * 0.05),
                        (60 + i * 22) * sc, seed + 90 + i))
    qy = H * 0.94                                               # the quay in front: stone edge, bollards
    quay = path()
    quay.addRect(QRectF(0, qy, W, H - qy))
    x = W * 0.07
    while x < W:
        quay.addRect(QRectF(x - 5 * sc, qy - 12 * sc, 10 * sc, 12 * sc))
        ellipse(quay, x, qy - 12 * sc, 7 * sc, 3 * sc)
        x += W * 0.21
    fill(f, quay, rgb(*tone(S, (8, 8, 11), 0.1)))
    fill(m, quay, mat(0.3))
    fill_rect(f, 0, qy, W, 1.5 * sc, rgb(80, 80, 96, 0.4))      # sky light on the quay edge
    x = 0.0
    while x < W:                                                # joints between the coping stones
        fill_rect(f, x, qy, 1 * sc, H - qy, rgb(30, 30, 38, 0.5))
        x += 26 * sc


def river_bridge(S, c, f, m, seed) -> None:
    """A cable-stayed bridge over a city river; S.bridge = deck height (m) for the niagara curtain."""
    W, H = S.W, S.H
    wl, sc = S.horizon * H, size_scale(S)
    dark_sky(S, c, wl, (110, 78, 66), low=(26, 26, 42), glowH=0.34, sun_x=0.15)
    starry(S, c, seed, wl, n=0.35, milky=0)
    skyline(c, m, W, H, wl, seed + 1, far=True, S=S, sc=sc)
    skyline(c, m, W, H, wl, seed + 2, far=False, S=S, sc=sc, tall=0.45)
    street_lights(c, W, H, wl, seed + 3, sc)
    spec = dict(deck=wl - 0.07 * H, topY=wl - min(0.42 * H, 0.42 * W), pylons=(0.27, 0.75), sc=sc, seed=seed + 4,
                wl=wl)
    cable_bridge(S, c, m, **spec)
    S.bridge = (wl - spec["deck"]) / H * 150 / 1.5              # deck height (m) at ~150 m for the waterfall
    water(c, m, W, H, wl, seed + 5, tint=(10, 12, 24), reflect=0.72)
    S.water = wl
    n_beacons = len(S.beacons)
    cable_bridge(S, f, m, **spec)                               # again in front: shells rise behind the bridge
    del S.beacons[n_beacons:]
    for i, pf in enumerate(spec["pylons"]):
        light_reflection(c, pf * W, wl + 2 * sc, (H - wl) * 0.55, (200, 220, 255), sc, seed + 40 + i, 0.3)
    ey = H * 0.94                                               # embankment balustrade in front
    bal = path()
    bal.addRect(QRectF(0, ey, W, H - ey))
    bal.addRect(QRectF(0, ey - 22 * sc, W, 4 * sc))
    x = 0.0
    while x < W:
        ellipse(bal, x, ey - 9 * sc, 2.4 * sc, 9 * sc)
        x += 9 * sc
    fill(f, bal, rgb(*tone(S, (7, 7, 10), 0.1)))
    fill(m, bal, mat(0.3))
    for x in (W * 0.12, W * 0.88):                              # two old lamp posts on the embankment
        post = path()
        post.addRect(QRectF(x - 2 * sc, ey - 110 * sc, 4 * sc, 110 * sc))
        post.addRect(QRectF(x - 7 * sc, ey - 104 * sc, 14 * sc, 3 * sc))
        fill(f, post, rgb(8, 8, 11))
        fill(m, post, mat(0.3))
        fill(f, ellipse(path(), x, ey - 116 * sc, 5 * sc, 7 * sc), rgb(255, 214, 160))
        glow(f, x, ey - 116 * sc, 40 * sc, (255, 190, 120), 0.35, 0.12)


def waterfront(S, c, f, m, seed) -> None:
    """Big-city waterfront on New Year's Eve: floodlit crowns, a ferris wheel, a crowd in front."""
    W, H = S.W, S.H
    wl, sc, rnd = S.horizon * H, size_scale(S), prng(seed + 7)
    dark_sky(S, c, wl, (150, 96, 66), low=(40, 30, 46), glowH=0.48, sun_x=0.85)
    starry(S, c, seed, wl, n=0.15, milky=0)
    skyline(c, m, W, H, wl, seed + 1, far=True, S=S, sc=sc * 1.2)
    crowns = [(255, 220, 160), (140, 200, 255), (255, 120, 200), (255, 200, 90), (150, 255, 200), (255, 255, 240)]
    n = max(3, jround(W / (190 * sc)))
    for i in range(n):                                          # the tall towers with floodlit crowns
        x = W * (i + 0.2 + rnd() * 0.6) / n
        h = min(min(H, W * 1.1) * (0.26 + rnd() * 0.2), wl - H * 0.12)
        w = (34 + rnd() * 24) * sc
        crown_tower(S, c, m, x - w / 2, wl, w, h, rnd, sc, crowns[int(rnd() * len(crowns))])
    skyline(c, m, W, H, wl, seed + 2, far=False, S=S, sc=sc, tall=1.3)
    fx, fr = W * (0.78 + rnd() * 0.1), min(0.13 * H, 0.16 * W)
    ferris_wheel(c, m, fx, wl - fr * 1.12, fr, sc, rnd)
    street_lights(c, W, H, wl, seed + 3, sc)
    water(c, m, W, H, wl, seed + 4, tint=(12, 12, 26), reflect=0.78)
    S.water = wl
    for i, (x, y, _) in enumerate(S.beacons):
        light_reflection(c, x, wl + (wl - y) * 0.8, H * 0.06, (255, 60, 40), sc, seed + i, 0.25)
    top = H * 0.9
    crowd(f, m, W, H, seed + 5, sc * 1.7, top)
    p = f.p                                                     # the crowd's heads catch the city glow
    p.save()
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    p.fillRect(QRectF(0, top - 20 * sc, W, H), QBrush(vgrad(top - 10 * sc, H, [(0, rgb(120, 80, 60, 0.12)),
                                                                        (1, rgb(0, 0, 0, 0))])))
    p.restore()


WATER_SCENES = {"Harbour": harbour, "River Bridge": river_bridge, "Waterfront": waterfront}
