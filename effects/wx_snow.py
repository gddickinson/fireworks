"""Realistic snow (weather plug-in, effects/fx_base.py): a port of web/static/fw_wx_snow.js.

Many small bright flakes at depths from 3 to 63 m in three layers (far: faint specks; middle: small dots; near: slightly
larger with a soft bokeh edge), tumbling in turbulence and drifting with the gusty wind; coloured by nearby bursts; and a thin layer of snow slowly building up
on the top edges of the silhouettes (effects/wx_util.scene_geometry), cached as an image per depth step.

update() (as the JS): each flake: depth z, px per metre m = 1.5 H / z, fall speed vf (0.6..1.4 m/s), phase ph;
turbulence u, w = noise1(seed + id, 0.5 t + ph) - 0.5, noise1(seed + 7 id, 0.4 t + ph) - 0.5;
x += (wind + 1.6 u) m dt; y += (vf + 0.5 w) m dt; below the bottom: respawn at the top (seeded); x wraps.
Accumulated depth (px at 800 px height): acc = 0.4 + 3 (1 - exp(-t / 90)).  Flakes are numpy arrays (noise with a
per-flake seed: wx_util.noise1_v); respawns draw the prng in flake order like the JS.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QImage, QPainter, QPainterPath, QRadialGradient

from effects.fx_base import register_weather
from effects.scenery_noise import hash as nhash, noise1, prng
from effects.wx_util import budget, clamp, lights, noise1_v, rgba, scene_geometry, sky_tone

BASE, FOCUS = 4200, 5            # flakes at 1280 x 800; nearer than FOCUS m: soft bokeh
FIELDS = ("x", "y", "z", "vf", "ph", "sz", "id")
_SPRITE = None


def sprite() -> QImage:
    """Soft white disc, 32 px."""
    global _SPRITE
    if _SPRITE is None:
        img = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        g = QRadialGradient(QPointF(16, 16), 16)
        for t, col, a in ((0, (255, 255, 255), 1), (0.45, (250, 252, 255), 0.85), (0.75, (245, 248, 255), 0.25),
                          (1, (245, 248, 255), 0)):
            g.setColorAt(t, rgba(col, a))
        p.fillRect(0, 0, 32, 32, QBrush(g))
        p.end()
        _SPRITE = img
    return _SPRITE


class Snow:
    def __init__(self, env, density: float = 1.0):
        self.seed = (env.seed ^ 0x5E0F) & 0xFFFFFFFF
        self.R = prng(self.seed)
        self.dens = density
        self.f = {k: np.zeros(0) for k in FIELDS}
        self.W = self.H = 1
        self.t = 0.0
        self.acc = 0.0
        self.vx_mean = 0.0
        self.acc_img = None
        self.acc_depth = None
        self.resize(env)

    def _new(self, top: bool) -> tuple:
        R = self.R
        u = R()
        z = 3 + 60 * u ** 1.15                                # most flakes far, a few close to the lens
        x = R() * self.W
        y = -10 - R() * 20 if top else R() * self.H
        return x, y, z, 0.6 + R() * 0.8, R() * 100, 0.6 + R() * 0.8, float(int(R() * 1e6))

    def _fill(self, env):
        amount = getattr(env, "intensity", 1.0)               # panel slider (Rain / snow amount)
        n = budget(env, BASE * self.dens * amount, BASE * self.dens * 2.5)
        cur = len(self.f["x"])
        if cur > n:
            self.f = {k: v[:n] for k, v in self.f.items()}
        elif cur < n:
            a = np.array([self._new(False) for _ in range(n - cur)], dtype=np.float64).reshape(-1, 7)
            self.f = {k: np.concatenate([self.f[k], a[:, i]]) for i, k in enumerate(FIELDS)}

    def resize(self, env):
        self.W, self.H = env.W, env.H
        self.f = {k: np.zeros(0) for k in FIELDS}
        self._fill(env)
        self.acc_img = None

    def update(self, dt, env):
        if env.W != self.W or env.H != self.H or not len(self.f["x"]):
            self.resize(env)
        self._fill(env)
        self.t += dt
        f, t, W, H = self.f, self.t, self.W, self.H
        wind, calm = env.wind or 0.0, 0.5 if env.reduced else 1.0
        m = 1.5 * env.H / f["z"]
        ids = f["id"].astype(np.int64)
        u = noise1_v(self.seed + ids, t * 0.5 + f["ph"]) - 0.5
        w = noise1_v(self.seed + 7 * ids, t * 0.4 + f["ph"]) - 0.5
        vx = (wind + 1.6 * u * calm) * m
        f["x"] = f["x"] + vx * dt
        f["y"] = f["y"] + (f["vf"] + 0.5 * w * calm) * m * dt * calm
        for i in np.nonzero(f["y"] > H + 20)[0].tolist():
            for k, v in zip(FIELDS, self._new(True)):
                f[k][i] = v
        x = f["x"]
        f["x"] = np.where(x < -20, x + W + 40, np.where(x > W + 20, x - W - 40, x))
        self.vx_mean = float(vx.mean()) if len(vx) else 0.0
        self.acc = 0.4 + 3 * (1 - math.exp(-t / 90))

    def stats(self):
        return dict(count=len(self.f["x"]), vx=self.vx_mean, acc=self.acc)

    def state(self):
        return {k: v.copy() for k, v in self.f.items()}

    # --- drawing ---------------------------------------------------------------------------------------------
    def _accumulation(self, env) -> QImage | None:
        """Thin white lines on the silhouettes' top edges (flat ones get more), redrawn per 1/8 px of depth."""
        want = round(self.acc * 8) / 8
        if self.acc_img is not None and self.acc_depth == want:
            return self.acc_img
        geo = scene_geometry(env)
        W, H = max(1, int(self.W)), max(1, int(self.H))
        img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        if geo.edges:
            e = np.array([(x, y, s, 1.0 if ow else 0.0) for x, y, s, ow in geo.edges], dtype=np.float64)
            ex, ey, slope, ow = e[:, 0], e[:, 1], e[:, 2], e[:, 3] > 0
            flat = np.where(ow, np.clip(1 - slope / 1.2, 0, 1), np.clip(1 - (slope - 1) / 4, 0, 1))
            seed = env.seed & 0xFFFFFFFF
            vary = 0.55 + 0.9 * (0.6 * noise1(seed, ex / 9) + 0.4 * nhash(seed, ex, ey))
            th = want * (H / 800) * vary * flat
            sel = (flat > 0) & (th >= 0.25)
            p = QPainter(img)
            for x, y, h in zip(ex[sel].tolist(), ey[sel].tolist(), th[sel].tolist()):
                p.fillRect(QRectF(x, y - h * 0.7, 1, h), rgba((232, 238, 250), clamp(0.3 + h * 0.25, 0, 0.85)))
            p.end()
        self.acc_img, self.acc_depth = img, want
        return img

    def draw_over(self, p, env):
        W, H, t, f = self.W, self.H, self.t, self.f
        lts = [L for L in lights(env) if L[3] > 0.05][:5]
        tone = sky_tone(env)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillRect(QRectF(0, 0, W, H), rgba(tuple(v * 1.2 for v in tone["haze"]), 0.05))   # a faint veil
        for x, y, r, I, col in lts:                           # burst light scattered by the falling snow
            r, a = r * 1.2, min(0.08, 0.024 * I * getattr(env, "intensity", 1.0))   # gentle (web scatter 0.02)
            g = QRadialGradient(QPointF(x, y), r)
            g.setColorAt(0, rgba(col, a))
            g.setColorAt(1, rgba(col, 0))
            p.fillRect(QRectF(x - r, y - r, 2 * r, 2 * r), QBrush(g))
        if env.scenery is not None:
            p.drawImage(0, 0, self._accumulation(env))
        # three layers: far specks and middle dots in two paths, near flakes as small soft sprites (bokeh)
        r = 0.006 * (1.5 * env.H / f["z"]) * f["sz"]          # a ~1 cm flake (radius in px)
        near = f["z"] < FOCUS * 2
        far, mid = ~near & (r < 0.7), ~near & (r >= 0.7)
        specks = QPainterPath()
        for x, y in zip(f["x"][far].tolist(), f["y"][far].tolist()):
            specks.addRect(x - 0.5, y - 0.5, 1, 1)
        p.fillPath(specks, rgba((240, 244, 255), 0.45))
        dots = QPainterPath()
        s = np.clip(r[mid], 0.7, 1.6)
        for x, y, ss in zip(f["x"][mid].tolist(), f["y"][mid].tolist(), s.tolist()):
            dots.addEllipse(QPointF(x, y), ss, ss)
        p.fillPath(dots, rgba((248, 250, 255), 0.8))
        spr = sprite()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        for i in np.nonzero(near)[0].tolist():
            z, ri = f["z"][i], r[i]
            soft = (FOCUS - z) / FOCUS if z < FOCUS else 0.0
            d = min(7.0, max(2.4, ri * 2.6 * (1 + 0.6 * soft)))
            tumble = 0.8 + 0.2 * math.sin(t * (2 + f["sz"][i] * 3) + f["ph"][i])   # a turning flake glints
            p.setOpacity(clamp(0.95 * tumble * (1 - 0.35 * soft), 0.3, 1))
            p.drawImage(QRectF(f["x"][i] - d / 2, f["y"][i] - d / 2, d, d), spr)
        p.setOpacity(1)
        for lx, ly, lr, LI, col in lts:                       # flakes inside a light's radius take its colour
            r2, a = (lr * 0.8) ** 2, min(0.9, 0.45 * LI)
            if a < 0.04:
                continue
            sel = (f["x"] - lx) ** 2 + (f["y"] - ly) ** 2 <= r2
            if not sel.any():
                continue
            sz = np.clip(0.006 * (1.5 * env.H / f["z"][sel]) * f["sz"][sel] * 1.3, 0.7, 2.5)
            dots = QPainterPath()
            for x, y, ss in zip(f["x"][sel].tolist(), f["y"][sel].tolist(), sz.tolist()):
                dots.addEllipse(QPointF(x, y), ss, ss)
            p.fillPath(dots, rgba(tuple(min(255, v * 0.7 + 90) for v in col), a))   # coloured by the burst


def make_snow(env, density: float = 1.0) -> Snow:
    return Snow(env, density)


register_weather("Snow", "Snow", lambda env: make_snow(env))
