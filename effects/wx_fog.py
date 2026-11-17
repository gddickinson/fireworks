"""Realistic fog and mist (weather plug-ins, effects/fx_base.py): a port of web/static/fw_wx_fog.js.

Layered volumetric fog from periodic fbm noise textures (numpy, built once per size at 1/4 view px), scrolled with
the gusty wind at their depths and blended in a low-resolution buffer that is scaled up smoothly.  Denser towards
the ground; bursts glow through it: their colour tints the fog around them (SourceAtop) plus a faint airlight halo,
while the fog's alpha dims the sparks behind it.  Mist is the light version: thinner, hugging the ground and water.

update() (as the JS): layer i (depth z_i m) scrolls off_i += wind * 1.5 H / z_i * dt / 4 (low-res px, wrapping
around the texture width); it bobs vertically by 1.5 sin(0.07 t + i) when drawn.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QRadialGradient

from effects.fx_base import register_weather
from effects.scenery_noise import prng
from effects.wx_util import PXM, clamp, draw_scrolled, fbm_p, lights, premul_image, rgba, sky_tone, smooth_v

DIV = 4                          # view px per fog pixel
# depth (m), noise scale (cells across the width), contrast window, alpha, band (centre, half-width, below fill)
FOG = [dict(z=900, cells=3, lo=0.3, hi=0.75, a=0.3, band=(0.35, 0.5, 0)),
       dict(z=260, cells=5, lo=0.35, hi=0.8, a=0.45, band=(0.0, 0.2, 1)),      # centred on the horizon
       dict(z=70, cells=4, lo=0.4, hi=0.85, a=0.5, band=(0.12, 0.25, 1))]
MIST = [dict(z=300, cells=6, lo=0.35, hi=0.85, a=0.4, band=(0.0, 0.1, 0.7)),
        dict(z=80, cells=5, lo=0.45, hi=0.9, a=0.42, band=(0.06, 0.12, 0.8))]
FMT = QImage.Format.Format_ARGB32_Premultiplied


def texture(L: dict, w: int, h: int, hz_frac: float) -> QImage:
    """White, alpha = density (noise through a contrast window, times the vertical band); periodic in x."""
    ctr, half, below = L["band"]
    cy = hz_frac - ctr
    cells_y = max(1, round(L["cells"] * h / w * 2))
    v = (np.arange(h) / h)[:, None]
    dv = (v - cy) / half
    band = np.exp(-dv * dv)
    band = np.where(v > cy, np.maximum(band, below * smooth_v(cy, cy + half, v)), band)
    x = (np.arange(w) / w * L["cells"])[None, :]
    n = fbm_p(L["seed"], x, v * cells_y * 0.5 + 0 * x, L["cells"], 1e6, 4)
    a = np.where(band < 0.01, 0.0, np.rint(255 * L["a"] * band * smooth_v(L["lo"], L["hi"], n)))
    arr = np.empty((h, w, 4))
    arr[..., :3] = 255
    arr[..., 3] = a
    return premul_image(arr)


class Fog:
    def __init__(self, env, mist: bool = False):
        self.mist = mist
        specs = MIST if mist else FOG
        seed = (env.seed ^ (0x3157 if mist else 0xF06)) & 0xFFFFFFFF
        R = prng(seed)
        self.layers = [dict(L, off=R() * 1000, seed=(seed + 977 * i) & 0xFFFFFFFF, tex=None)
                       for i, L in enumerate(specs)]
        self.W = self.H = 1
        self.t = 0.0
        self.vx = 0.0
        self.fc = None
        self.resize(env)

    def resize(self, env):
        self.W, self.H = env.W, env.H
        for L in self.layers:
            L["tex"] = None
        self.fc = None

    def update(self, dt, env):
        if env.W != self.W or env.H != self.H:
            self.resize(env)
        self.t += dt
        wind, calm = env.wind or 0.0, 0.5 if env.reduced else 1.0
        s = 0.0
        for L in self.layers:
            v = wind * PXM(env, L["z"]) / DIV * calm
            L["off"] += v * dt
            s += v
        self.vx = s / len(self.layers)

    def stats(self):
        return dict(count=len(self.layers), vx=self.vx)

    def state(self):
        return [L["off"] for L in self.layers]

    def draw_over(self, p, env):
        W, H, t, mist = self.W, self.H, self.t, self.mist
        w, h = math.ceil(W / DIV), math.ceil(H / DIV)
        hz = getattr(env.scenery, "horizon", None) or 0.85
        tone = sky_tone(env)
        if self.fc is None or (self.fc.width(), self.fc.height()) != (w, h):
            self.fc = QImage(w, h, FMT)
        fc = self.fc
        fc.fill(0)
        x = QPainter(fc)
        x.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        base = (0.0, 0.07, 0.22) if mist else (0.22, 0.32, 0.42)   # a smooth veil, thicker towards the ground
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(255, 255, 255, round(255 * base[0])))
        g.setColorAt(clamp(hz - 0.1, 0.05, 0.9), QColor(255, 255, 255, round(255 * base[1])))
        g.setColorAt(1, QColor(255, 255, 255, round(255 * base[2])))
        x.fillRect(QRectF(0, 0, w, h), QBrush(g))
        for i, L in enumerate(self.layers):
            if L["tex"] is None:
                L["tex"] = texture(L, w, h, hz)
            draw_scrolled(x, L["tex"], L["off"] % w, 1.5 * math.sin(0.07 * t + i), w)
        # colour: the sky glow's tone, lighter near the horizon
        x.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        col = tuple(v * 1.15 for v in tone["fog"]) if mist else tone["fog"]
        gc = QLinearGradient(0, 0, 0, h)
        gc.setColorAt(0, rgba(tuple(v * 0.75 for v in col), 1))
        gc.setColorAt(clamp(hz, 0.1, 0.95), rgba(tuple(v * 1.15 for v in col), 1))
        gc.setColorAt(1, rgba(tuple(v * 0.9 for v in col), 1))
        x.fillRect(QRectF(0, 0, w, h), QBrush(gc))
        lts = [L for L in lights(env) if L[3] > 0.03][:6]     # bursts glow through the fog
        modes = ((QPainter.CompositionMode.CompositionMode_SourceAtop, 0.9, 0.6),
                 (QPainter.CompositionMode.CompositionMode_SourceOver, 0.5, 0.14))
        for mode, k, amax in modes:
            x.setCompositionMode(mode)
            for lx, ly, lr, LI, lcol in lts:
                r, a = lr * k / DIV, min(amax, (0.15 if mist else 0.24) * LI)
                lx, ly = lx / DIV, ly / DIV
                gr = QRadialGradient(QPointF(lx, ly), r)
                hot = tuple(min(255, v * 0.85 + 60) for v in lcol)
                gr.setColorAt(0, rgba(hot, a))
                gr.setColorAt(0.3, rgba(lcol, a * 0.45))
                gr.setColorAt(1, rgba(lcol, 0))
                x.fillRect(QRectF(lx - r, ly - r, 2 * r, 2 * r), QBrush(gr))
        x.end()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF(0, 0, w * DIV, h * DIV), fc)


def make_fog(env, mist: bool = False) -> Fog:
    return Fog(env, mist)


register_weather("Fog", "Fog", lambda env: make_fog(env))
register_weather("Mist", "Mist", lambda env: make_fog(env, mist=True))
