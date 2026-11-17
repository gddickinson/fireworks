"""Realistic rain (weather plug-in, effects/fx_base.py): a port of web/static/fw_wx_rain.js.

Motion-blurred streaks in three depth layers, slanted by the gusty wind, glinting in the colour of nearby bursts;
ripple rings on water or crown splashes on the ground; a wet sheen with light reflections near the bottom; a thin
haze that lowers the contrast and scatters the burst light.

update() (plain seeded arithmetic, as the JS): layer z (m): px per metre m = 1.5 H / z; drop velocity (px/s) =
(wind, 9 m/s * s) * m, so the slant dx/dy = wind / 9 at every depth; streak length = speed * 0.022 s (shutter).
Drops below the bottom respawn above the top at a seeded x; x wraps around the width.  Splashes spawn at a fixed
rate (rings on water between the waterline and the bottom, crowns in the bottom band otherwise); a ring grows with
its age while its alpha fades.  Drops are numpy arrays per layer; respawns draw the prng in the JS order.
Drawing: one QPainterPath per depth layer (and per glint ring), splashes one by one.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QLinearGradient, QPainterPath, QPen, QRadialGradient

from effects.fx_base import register_weather
from effects.scenery_noise import prng
from effects.wx_util import PXM, budget, clamp, lights, rgba, sky_tone

LAYERS = [                                                    # near = longer, faster, brighter, thicker
    dict(z=4.5, n=90, width=1.5, alpha=0.34, col=(200, 208, 224)),
    dict(z=12, n=300, width=0.95, alpha=0.22, col=(176, 186, 206)),
    dict(z=32, n=700, width=0.6, alpha=0.13, col=(150, 160, 182)),
]
SHUTTER, FALL = 0.022, 9.0                                    # s, m/s


class _Layer:
    def __init__(self, spec):
        self.__dict__.update(spec)
        self.x = np.zeros(0)
        self.y = np.zeros(0)
        self.s = np.zeros(0)


class Rain:
    def __init__(self, env, heavy: float = 1.0, shared: dict | None = None):
        self.heavy = heavy
        self.shared = shared if shared is not None else {}
        self.R = prng((env.seed ^ 0x52A1) & 0xFFFFFFFF)
        self.layers = [_Layer(L) for L in LAYERS]
        self.splashes: list = []                              # [x, y, age, life, s, ring, a]
        self.W = self.H = 1
        self.wl = None
        self.spawn_acc = 0.0
        self.vx_mean = 0.0
        self.resize(env)

    def _fill(self, env):
        R = self.R
        for L in self.layers:
            n = budget(env, L.n * self.heavy, L.n * self.heavy * 2)
            if len(L.x) > n:
                L.x, L.y, L.s = L.x[:n], L.y[:n], L.s[:n]
            if len(L.x) < n:
                add = [(R() * self.W, R() * self.H, 0.8 + R() * 0.4) for _ in range(n - len(L.x))]
                a = np.array(add, dtype=np.float64).reshape(-1, 3)
                L.x, L.y, L.s = np.concatenate([L.x, a[:, 0]]), np.concatenate([L.y, a[:, 1]]), \
                    np.concatenate([L.s, a[:, 2]])

    def resize(self, env):
        self.W, self.H = env.W, env.H
        S = env.scenery
        self.wl = S.water * env.k if S is not None and getattr(S, "water", None) is not None else None
        for L in self.layers:
            L.x, L.y, L.s = np.zeros(0), np.zeros(0), np.zeros(0)
        self._fill(env)

    def update(self, dt, env):
        if env.W != self.W or env.H != self.H or not len(self.layers[0].x):
            self.resize(env)
        self._fill(env)
        R, W, H = self.R, self.W, self.H
        wind, calm = env.wind or 0.0, 0.6 if env.reduced else 1.0
        sx, n = 0.0, 0
        for L in self.layers:
            m = PXM(env, L.z) * calm
            vx, vy = wind * m, FALL * L.s * m
            L.x = L.x + vx * dt
            L.y = L.y + vy * dt
            sx += vx * len(L.x)
            n += len(L.x)
            for i in np.nonzero(L.y > H + vy * SHUTTER)[0].tolist():
                L.x[i] = R() * W
                L.y[i] = -R() * H * 0.1
                L.s[i] = 0.8 + R() * 0.4
            L.x = np.where(L.x < -20, L.x + W + 40, np.where(L.x > W + 20, L.x - W - 40, L.x))
        self.vx_mean = sx / n if n else 0.0
        wl = self.wl
        rate = budget(env, (140 if wl is not None else 90) * self.heavy, 400) * calm
        self.spawn_acc += rate * dt
        max_s = budget(env, 160 * self.heavy, 400)
        sp = self.splashes
        while self.spawn_acc >= 1:
            self.spawn_acc -= 1
            if len(sp) >= max_s:
                continue
            if wl is not None:
                u = R()
                y = wl + 2 + (H - wl - 2) * (u * u * 0.4 + u * 0.6)    # fewer near the far waterline
                sp.append([R() * W, y, 0.0, 0.45 + R() * 0.35, 0.15 + 0.85 * (y - wl) / max(1, H - wl), True, 0.0])
            else:
                y = H * (0.9 + R() * 0.1)
                sp.append([R() * W, y, 0.0, 0.1 + R() * 0.08, 0.5 + (y / H - 0.9) * 5, False, R() * 6.283])
        for s in sp:
            s[2] += dt
        self.splashes = [s for s in sp if s[2] < s[3]]

    def stats(self):
        return dict(count=sum(len(L.x) for L in self.layers), splashes=len(self.splashes), vx=self.vx_mean)

    def state(self):
        return [(L.x.copy(), L.y.copy(), L.s.copy()) for L in self.layers]

    # --- drawing ---------------------------------------------------------------------------------------------
    def draw_over(self, p, env):
        W, H, heavy, wl = self.W, self.H, self.heavy, self.wl
        lts = [L for L in lights(env) if L[3] > 0.05][:5]
        tone = sky_tone(env)
        flash = clamp(self.shared.get("flash", 0) or 0, 0, 1.5)
        wind, sc = env.wind or 0.0, H / 800
        hz = (getattr(env.scenery, "horizon", None) or 0.85) * H
        veil = 0.05 + 0.04 * heavy
        p.setPen(Qt.PenStyle.NoPen)
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0, rgba(tone["haze"], veil * 0.6))
        g.setColorAt(clamp(hz / H, 0.1, 0.95), rgba(tone["haze"], veil * 1.6))
        g.setColorAt(1, rgba(tone["haze"], veil))
        p.fillRect(QRectF(0, 0, W, H), QBrush(g))
        for x, y, r, I, col in lts:                           # light scattered by the rain
            r, a = r * 1.1, min(0.22, 0.06 * I * heavy)
            gr = QRadialGradient(QPointF(x, y), r)
            gr.setColorAt(0, rgba(col, a))
            gr.setColorAt(1, rgba(col, 0))
            p.fillRect(QRectF(x - r, y - r, 2 * r, 2 * r), QBrush(gr))
        cap = Qt.PenCapStyle.RoundCap
        for L in reversed(self.layers):                       # streaks, far to near
            m = PXM(env, L.z)
            ex, ey = -wind * m * SHUTTER, -FALL * m * SHUTTER
            width = L.width * max(0.7, sc)
            col = tuple(min(255, v + 30 * flash) for v in L.col)
            p.setPen(QPen(rgba(col, min(0.9, L.alpha * (1 + 0.8 * flash))), width, Qt.PenStyle.SolidLine, cap))
            p.drawPath(_streaks(L.x, L.y, L.x + ex * L.s, L.y + ey * L.s))
            for lx, ly, lr, LI, lcol in lts:                  # glints: drops near a burst catch its colour
                r2 = (lr * 0.9) ** 2
                inner, a = r2 * 0.2, min(0.85, L.alpha * 2.2 * LI)
                if a < 0.03:
                    continue
                q = (L.x - lx) ** 2 + (L.y - ly) ** 2
                gcol = tuple(min(255, v * 0.7 + 90) for v in lcol)
                for lo, hi, f in ((0, inner, 1.0), (inner, r2, 0.35)):
                    sel = (q >= lo) & (q < hi)
                    if not sel.any():
                        continue
                    xs, ys, ss = L.x[sel], L.y[sel], L.s[sel]
                    p.setPen(QPen(rgba(gcol, a * f), width, Qt.PenStyle.SolidLine, cap))
                    p.drawPath(_streaks(xs, ys, xs + ex * ss, ys + ey * ss))
        p.setPen(Qt.PenStyle.NoPen)
        if wl is None:                                        # wet sheen and stretched reflections on wet ground
            top = H * 0.86
            gs = QLinearGradient(0, top, 0, H)
            gs.setColorAt(0, rgba(tone["haze"], 0))
            gs.setColorAt(1, rgba(tuple(v * 1.6 for v in tone["haze"]), 0.16))
            p.fillRect(QRectF(0, top, W, H - top), QBrush(gs))
            for x, y, r, I, col in lts:
                a, rx = min(0.3, 0.1 * I), max(10.0, r * 0.18)
                p.save()
                p.translate(x, H)
                p.scale(1, (H - top) / rx)
                gr = QRadialGradient(QPointF(0, 0), rx)
                gr.setColorAt(0, rgba(col, a))
                gr.setColorAt(1, rgba(col, 0))
                p.fillRect(QRectF(-rx, -rx, 2 * rx, rx), QBrush(gr))
                p.restore()
        self._draw_splashes(p, lts, sc)

    def _draw_splashes(self, p, lts, sc):
        p.setBrush(Qt.BrushStyle.NoBrush)
        lw = max(0.6, 0.8 * sc)
        for x, y, age, life, s, ring, _a in self.splashes:
            t = age / life
            fade = (1 - t) * (1 - t)
            col = [190.0, 198.0, 215.0]
            if lts:                                           # the nearest strong light tints the splash
                best, lit = 0.0, None
                for lx, ly, lr, LI, lcol in lts:
                    d = math.hypot(x - lx, y - ly) / lr
                    w = LI / (1 + d * d * 4)
                    if w > best:
                        best, lit = w, lcol
                if best > 0.08:
                    k = min(0.8, best)
                    col = [v + (lit[i] - v) * k for i, v in enumerate(col)]
            if ring:
                rx = (2 + 13 * t) * s * sc * 1.4
                ry = rx * (0.12 + 0.22 * s)
                p.setPen(QPen(rgba(col, 0.5 * fade * (0.5 + s)), lw))
                p.drawEllipse(QPointF(x, y), rx, ry)
            else:
                h = (2 + 5 * math.sin(t * math.pi)) * s * sc
                w = (1.5 + 4 * t) * s * sc
                p.setPen(QPen(rgba(col, 0.45 * fade), lw))
                path = QPainterPath()
                path.moveTo(x - w, y - h)
                path.lineTo(x - w * 0.3, y)
                path.moveTo(x + w, y - h)
                path.lineTo(x + w * 0.3, y)
                path.moveTo(x, y - h * 1.3)
                path.lineTo(x, y - h * 0.4)
                p.drawPath(path)


def _streaks(x0, y0, x1, y1) -> QPainterPath:
    path = QPainterPath()
    mv, ln = path.moveTo, path.lineTo
    for a, b, c, d in zip(x0.tolist(), y0.tolist(), x1.tolist(), y1.tolist()):
        mv(a, b)
        ln(c, d)
    return path


def make_rain(env, heavy: float = 1.0, shared: dict | None = None) -> Rain:
    return Rain(env, heavy, shared)


register_weather("Rain", "Rain", lambda env: make_rain(env))
