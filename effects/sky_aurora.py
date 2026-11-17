"""Aurora sky effect (register_sky_fx 'aurora'): a numpy/QPainter port of web/static/fw_sky_aurora.js.

Two or three curtains of vertical rays - bright green lower edge with a thin pink fringe, fading to violet-red
tops - that ripple along their length and drift.  Each frame the rays are summed additively into a quarter-size
premultiplied RGBA buffer with numpy (per curtain: an outer product of the column brightness and the ray profile,
the web's 1.6 px wide ray sprite as weights 1 and 0.6 on two columns), scaled up smoothly to the sky (which softens
it), cut to the open sky and mirrored onto water.  A faint green glow lifts the sky under the curtains.
Reduced motion: slower.  Dusk: much fainter.  update() is Qt-free; column() and state() are pure numbers.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter

from effects.fx_base import register_sky_fx
from effects.fx_masks import horizon_px, is_dusk, masked, water_px
from effects.scenery_noise import noise1, prng

M32 = 0xFFFFFFFF
# Ray profile stops (fraction from the top of the ray, rgb, alpha) as the web's ray sprite gradient.
STOPS = [(0.0, (150, 50, 170), 0.0), (0.3, (160, 60, 160), 0.12), (0.6, (60, 190, 130), 0.25),
         (0.88, (80, 250, 140), 0.7), (0.96, (170, 255, 190), 0.85), (0.985, (240, 110, 190), 0.35),
         (1.0, (255, 110, 190), 0.0)]


def _profile(n: int = 256) -> np.ndarray:
    """(n, 4) premultiplied RGBA (0..255) of the ray gradient sampled from top to bottom."""
    t = (np.arange(n) + 0.5) / n
    ts = [s[0] for s in STOPS]
    out = np.empty((n, 4))
    for ch in range(3):
        out[:, ch] = np.interp(t, ts, [s[1][ch] for s in STOPS])
    out[:, 3] = np.interp(t, ts, [s[2] for s in STOPS])
    out[:, :3] *= out[:, 3:4]
    out[:, 3] *= 255
    return out


PROFILE = _profile()


class Aurora:
    def __init__(self, env):
        rnd = prng((env.seed ^ 0xA0A0B0B) & M32)
        n = 2 + (1 if rnd() < 0.5 else 0)
        self.curtains = []
        for _ in range(n):
            C = {"base": 0.38 + rnd() * 0.32, "amp": 0.05 + rnd() * 0.08, "freq": 0.6 + rnd() * 1.2,
                 "speed": 0.05 + rnd() * 0.08, "ph": rnd() * 6.28, "h": 0.28 + rnd() * 0.3, "I": 0.55 + rnd() * 0.45,
                 "u0": rnd() * 0.3 - 0.1, "u1": 0.7 + rnd() * 0.4}
            C["seed"] = int(rnd() * 1e6)
            self.curtains.append(C)
        self.t = 0.0

    def column(self, C, u, t=None):
        """Geometry and brightness of curtain C at u in [0, 1] (scalar or array): dict(y, h, b) in fractions of
        the sky height."""
        t = self.t if t is None else t
        u = np.asarray(u, dtype=np.float64)
        win = np.maximum(0, np.minimum(np.minimum(1, (u - C["u0"]) * 6), (C["u1"] - u) * 6))
        y = (C["base"] + C["amp"] * np.sin(u * C["freq"] * 6.283 + t * C["speed"] * 6 + C["ph"])
             + 0.06 * (noise1(C["seed"], u * 3 + t * 0.04) - 0.5))
        b = (noise1(C["seed"] + 1, u * 110 - t * 0.6) ** 2 * 0.45 + 0.25 * noise1(C["seed"] + 4, u * 30 + t * 0.3)
             + 0.3 * noise1(C["seed"] + 3, u * 7 + t * 0.15))
        pulse = 0.75 + 0.25 * np.sin(t * 0.7 + C["ph"] + u * 3)
        h = C["h"] * (0.6 + 0.7 * noise1(C["seed"] + 2, u * 5 + t * 0.08))
        return {"y": y, "h": h, "b": b * win * pulse * C["I"]}

    def update(self, dt, env):
        self.t += dt * (0.3 if env.reduced else 1.0)

    def buffer(self, bw: int, bh: int, I: float) -> np.ndarray:
        """The rays of this frame: (bh, bw, 4) premultiplied RGBA floats (0..255), summed additively."""
        acc = np.zeros((bh, bw, 4))
        u = np.arange(bw) / bw
        rows = (np.arange(bh) + 0.5)[:, None]
        n = len(PROFILE)
        for C in self.curtains:
            col = self.column(C, u)
            a = np.minimum(1, col["b"] * I * 0.75) * (col["b"] >= 0.02)
            h, y = np.maximum(col["h"] * bh, 1e-6), col["y"] * bh
            f = (rows - (y - h)) / h                                 # (bh, bw): position along each ray
            inside = (f >= 0) & (f < 1)
            idx = np.clip((f * n).astype(np.int64), 0, n - 1)
            add = PROFILE[idx] * (inside * a)[..., None]
            acc += add
            acc[:, 1:] += add[:, :-1] * 0.6                         # the sprite is 1.6 columns wide
        return acc

    def draw_sky(self, p, env):
        W, hz = env.W, horizon_px(env)
        bw, bh = max(16, math.ceil(W / 4)), max(8, math.ceil(hz / 4))
        I = 0.35 if is_dusk(env) else 1.0
        acc = np.clip(self.buffer(bw, bh, I), 0, 255)
        px = np.empty((bh, bw, 4), np.uint8)                      # premultiplied BGRA bytes (ARGB32 little endian)
        a = acc[..., 3]
        px[..., 3] = a
        for dst, src in ((0, 2), (1, 1), (2, 0)):
            px[..., dst] = np.minimum(acc[..., src], a)
        buf = QImage(px.tobytes(), bw, bh, bw * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()

        def sky(l):
            g = QLinearGradient(0, hz * 0.3, 0, hz)              # diffuse glow under the curtains (sky only)
            g.setColorAt(0, QColor(40, 160, 100, 0))
            g.setColorAt(1, QColor(40, 160, 100, int(255 * 0.07 * I)))
            l.fillRect(QRectF(0, 0, W, hz), g)
            l.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            l.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            l.drawImage(QRectF(0, 0, W, hz), buf)
        masked(p, env, "sky", sky)
        wl = water_px(env)
        if wl is not None:
            def water(l):
                l.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                l.translate(0, wl)
                l.scale(1, -0.85)
                l.translate(0, -wl)
                l.drawImage(QRectF(0, wl - hz, W, hz), buf)
            masked(p, env, "water", water, 0.5)

    def state(self):
        return {"t": self.t, "curtains": [dict(C) for C in self.curtains]}


register_sky_fx("aurora", "Aurora", Aurora)
