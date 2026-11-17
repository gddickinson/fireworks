"""Natural props of the realistic scenery: a QPainter/numpy port of web/static/fw_scenery_props.js.

Tree lines and surf (moved unchanged from effects/scenery.py), snow-laden conifers, flat-topped mesas, wind-shaped
dunes, a single smooth hill, rolling fields with hedgerows, and rippled reflections of single lights on water.
Colour goes to `c`, material (albedo) to `m`.  Ridges are (ys numpy array, step) tuples like
effects/scenery_parts.ridge_line; `ridge_y(r, x)` samples one.  Same prng draws as the web.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QPainterPath, QPen

from effects.scenery_draw import circle, fill, path, poly, polyline, stroke
from effects.scenery_noise import fbm1, hash, prng
from effects.scenery_parts import conifer, fill_path, jround, mat, ridge_path, rgb, vgrad


def size_scale(S) -> float:
    """Structure size: fits portrait views too."""
    return min(S.H / 800, S.W / 900)


def ridge_y(r, x) -> float:
    ys, step = r
    return float(ys[max(0, min(len(ys) - 1, jround(x / step)))])


def fill_ridge(c, W, H, r, brush, bottom=None) -> None:
    fill_path(c, ridge_path(W, r, H if bottom is None else bottom), brush)


def tree_line(c, m, W, H, y, seed, h, col) -> None:
    rnd, n = prng(seed), jround(W / (h * 0.22))
    c.p.fillRect(QRectF(0, y - h * 0.15, W, h * 0.2), rgb(*col))
    m.p.fillRect(QRectF(0, y - h * 0.15, W, h * 0.2), mat(0.2))
    cp, mp, cc, mc = c.p, m.p, rgb(*col), mat(0.2)
    cp.setPen(Qt.PenStyle.NoPen)
    mp.setPen(Qt.PenStyle.NoPen)
    for i in range(n):
        x = (i + rnd()) * W / n
        th = h * (0.5 + rnd() * 0.7) * (0.7 + 0.6 * float(fbm1(seed, x / W * 3, 3)))
        pth = conifer(x, y + 1, th, prng(seed * 1000 + i))
        cp.setBrush(cc)
        cp.drawPath(pth)
        mp.setBrush(mc)
        mp.drawPath(pth)


def surf(c, W, H, wl, seed) -> None:
    """Faint foam lines catching the sky light."""
    sc, p = H / 800, c.p
    for i in range(6):
        y, a = wl + (H - wl) * (0.25 + i * 0.13), 0.05 + i * 0.015
        pth = QPainterPath()
        for k, x in enumerate(range(0, W + 1, 8)):
            yy = y + math.sin(x / (60 * sc) + i * 1.7) * 3 * sc + (hash(seed, x, i) - 0.5) * 2 * sc
            pth.lineTo(x, yy) if k else pth.moveTo(x, yy)
        p.setPen(QPen(rgb(160, 175, 210, a), (1 + i * 0.5) * sc))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(pth)
    p.setPen(Qt.PenStyle.NoPen)


def snowy_conifer(c, m, x, y, h, seed, dark, snow_col) -> None:
    """Conifer with snow lying on the upper side of each tier."""
    shape = conifer(x, y, h, prng(seed))
    fill(c, shape, rgb(*dark))
    fill(m, shape, mat(0.3))
    rnd = prng(seed + 1)
    tiers, w = 6 + int(rnd() * 3), h * 0.32
    snow = path()
    for i in range(1, tiers + 1):
        t = i / tiers
        ty, tw, th = y - h + h * 0.92 * t, w * t * (0.7 + rnd() * 0.25), h * 0.035 * (0.6 + rnd() * 0.6)
        lift = ty - h * 0.11 * (1 - t * 0.5)
        snow.moveTo(x - tw * 0.85, ty - h * 0.01)
        snow.quadTo(x, lift, x + tw * 0.75, ty - h * 0.02)
        snow.quadTo(x, lift + th, x - tw * 0.85, ty - h * 0.01)
        snow.closeSubpath()
    fill(c, snow, rgb(*snow_col, 0.85))


def mesa_line(W, H, seed, base, amp, rough=2.5, step=2):
    """Flat-topped mesas and buttes: fbm through a steep step, so tops are flat and the walls are cliffs."""
    x = np.arange(0, W + step + 1, step, dtype=np.float64)
    u = x / W * rough
    f = fbm1(seed, u, 5)
    t = np.clip((f - 0.48) * 7, 0, 1)
    mesa = t * t * (3 - 2 * t)
    tier = np.clip((fbm1(seed + 3, u * 0.7, 3) - 0.5) * 6, 0, 1) * 0.35
    detail = (fbm1(seed + 9, u * 25, 3) - 0.5) * 0.06
    return H * (base - amp * (mesa * (0.65 + tier) + 0.05 * f + detail * (0.3 + mesa))), step


def dunes(c, m, W, H, seed, base, amp, lit, shade, waves=3.0, albedo=0.45, bottom=None):
    """One layer of dunes: sharp crests, smooth lit windward slopes, a shadowed slip face behind each crest."""
    bottom = H if bottom is None else bottom
    step = 3
    x = np.arange(0, W + step + 1, step, dtype=np.float64)
    u = x / W * waves + fbm1(seed, x / W * 2, 3) * 0.8
    ph = u - np.floor(u)
    shape = np.where(ph < 0.68, 0.5 - 0.5 * np.cos(np.pi * ph / 0.68), ((1 - ph) / 0.32) ** 1.3)
    height = 0.55 + 0.45 * fbm1(seed + 4, np.floor(u) * 0.37 + 0.2, 2)
    ys = H * (base - amp * (shape * height * 0.85 + 0.15 * fbm1(seed + 7, x / W * 5, 3)))
    crest, prev = [], 0.0
    for i, p_ in enumerate(ph.tolist()):
        if p_ < prev - 0.5 or (i == 0 and p_ > 0.68):           # phase wrapped: the trough
            crest.append(i)
        prev = p_
    r = (ys, step)
    top = float(ys.min())
    depth = bottom - top
    mix = tuple(lit[i] + (shade[i] - lit[i]) * 0.7 for i in range(3))
    fill_ridge(c, W, H, r, vgrad(top, bottom, [(0, rgb(*lit)), (1, rgb(*mix))]), bottom)
    fill_ridge(m, W, H, r, mat(albedo), bottom)
    yl = ys.tolist()
    for t in crest:                                             # slip face from the crest before the trough
        k = t
        while k > 0 and yl[k - 1] < yl[k]:
            k -= 1
        if t - k < 2:
            continue
        xc, xt, yc = k * step, t * step, yl[k]
        drop = min(depth * 0.9, (yl[t] - yc) * 2.5 + depth * 0.25)
        pth = path()
        pth.moveTo(xc, yc)
        for i in range(k, t + 1):
            pth.lineTo(i * step, yl[i])
        pth.quadTo(xt + (xt - xc) * 0.2, yc + drop, xc - (xt - xc) * 0.15, yc + drop * 1.1)
        pth.quadTo(xc - (xt - xc) * 0.05, yc + drop * 0.3, xc, yc)
        fill(c, pth, rgb(*shade, 0.85))
    p = c.p
    p.save()                                                    # the layer darkens downwards
    p.setClipPath(ridge_path(W, r, bottom))
    p.fillRect(QRectF(0, top, W, depth), QBrush(vgrad(top, bottom, [(0, rgb(0, 0, 0, 0)), (1, rgb(0, 0, 0, 0.45))])))
    p.restore()
    edge = polyline(x, ys)                                      # crest edge
    stroke(c, edge, rgb(*(min(255, v * 1.5) for v in lit), 0.5), max(1, H / 900))
    return r


def oak(x, y, h, rnd) -> QPainterPath:
    """Spreading broadleaf tree: a trunk splitting into branches recursively, leaf clumps at the twig ends."""
    out = path()

    def branch(x0, y0, a, ln, w, d):
        x1, y1 = x0 + math.cos(a) * ln, y0 + math.sin(a) * ln
        out.addPath(poly([(x0 - w / 2, y0), (x1 - w * 0.3, y1), (x1 + w * 0.3, y1), (x0 + w / 2, y0)]))
        if d == 0:
            for _ in range(16):
                cx = x1 + (rnd() - 0.5) * h * 0.13
                cy = y1 + (rnd() - 0.65) * h * 0.09
                circle(out, cx, cy, h * (0.008 + rnd() * 0.014))
            return
        n = 3 if d > 2 else 2 + (1 if rnd() < 0.5 else 0)
        for i in range(n):
            ang = a + (i - (n - 1) / 2) * (0.42 + rnd() * 0.25) + (rnd() - 0.5) * 0.3
            branch(x1, y1, ang, ln * (0.66 + rnd() * 0.14), w * 0.6, d - 1)

    branch(x, y, -math.pi / 2 + (rnd() - 0.5) * 0.15, h * 0.33, h * 0.07, 4)
    return out


def hill_line(W, H, seed, base, amp, cx, width, step=2):
    """A single rounded hill (castle mound) centred at cx (fraction of W), with a flattened summit."""
    x = np.arange(0, W + step + 1, step, dtype=np.float64)
    u = (x / W - cx) / width
    bump = np.exp(-u * u * 2.2) * (1 - 0.18 * np.exp(-u * u * 30))
    flat = np.exp(-(u * 2.2) ** 8)
    v = (np.maximum(bump, flat * 0.93) + (fbm1(seed, x / W * 9, 5) - 0.5) * 0.08 * (1 - flat)
         + (fbm1(seed + 2, x / W * 2, 3) - 0.5) * 0.1)
    return H * (base - amp * v), step


def fields(c, m, W, H, r, seed, depth, col, sc, rows=4) -> None:
    """Rolling farmland below a painted ridge: field strips between contour hedgerows, cross hedges, trees."""
    rnd = prng(seed)

    def off(k):
        return depth * (k / rows) ** 1.4

    for k in range(rows):
        x0 = 0.0
        while x0 < W:
            x1 = min(W + 4, x0 + W * (0.06 + rnd() * 0.12) * (1 + k * 0.4))
            tint = 0.75 + rnd() * 0.5
            pts, x = [], x0
            while x <= x1:
                pts.append((x, ridge_y(r, x) + off(k) + 2 * sc))
                x += 4
            x = x1
            while x >= x0:
                pts.append((x, ridge_y(r, x) + off(k + 1)))
                x -= 4
            fill(c, poly(pts), rgb(*(v * tint for v in col)))
            hedge = poly([(x1, ridge_y(r, x1) + off(k)),
                          (x1 + (rnd() - 0.5) * 20 * sc, ridge_y(r, x1) + off(k + 1))], close=False)
            stroke(c, hedge, rgb(*(v * 0.45 for v in col)), (0.8 + k * 0.5) * sc)
            x0 = x1
        xs = np.arange(0, W + 1, 4)
        stroke(c, polyline(xs, [ridge_y(r, x) + off(k + 1) for x in xs]), rgb(*(v * 0.4 for v in col)),
               (1 + k * 0.6) * sc)
        trees = path()
        x = rnd() * 40 * sc
        while x < W:                                            # trees along the hedge
            y, rr = ridge_y(r, x) + off(k + 1), (1.2 + rnd() * rnd() * 4) * sc * (1 + k * 0.45)
            circle(trees, x, y - rr * 0.8, rr)
            circle(trees, x + rr * 0.7, y - rr * 0.5, rr * 0.8)
            x += (8 + rnd() * rnd() * 90) * sc * (1 + k * 0.5)
        fill(c, trees, rgb(*(v * 0.35 for v in col)))
    xs = np.arange(0, W + 1, 4)
    fill(m, poly([(0, H)] + [(float(x), ridge_y(r, x)) for x in xs] + [(W, H)]), mat(0.3))


def light_reflection(c, x, y0, ln, col, sc, seed, a=0.5) -> None:
    """Rippled reflection of a point light on water from y0: short horizontal dashes, wider and fainter further."""
    rnd, p = prng(seed), c.p
    d = 1.5 * sc
    while d < ln:
        t = d / ln
        w, al = (1.5 + 9 * t + rnd() * 4) * sc, a * (1 - t) * (0.4 + rnd() * 0.6)
        if al >= 0.02:
            xx = x - w / 2 + (rnd() - 0.5) * 3 * sc * (1 + 3 * t)
            p.fillRect(QRectF(xx, y0 + d, w, (0.7 + rnd() * 0.8) * sc), rgb(*col, al))
        d += (1.6 + rnd() * 1.6) * sc

