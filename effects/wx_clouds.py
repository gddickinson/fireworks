"""Realistic low cloud deck (weather plug-in, effects/fx_base.py; also part of Storm and Lightning): a port of
web/static/fw_wx_clouds.js.

Two periodic fbm cloud textures (a high deck and lower, faster scud) shaded once per size with numpy at 1/4 view
px - dark cores, thin edges lit by the sky glow, undersides lit by the town - scrolled with the wind aloft.  Every
frame the bursts light the clouds from below/inside in their colour (SourceAtop: only where there is cloud), the
Moon sky effect (env.scenery.moon = {x, y, r, time}, view px, when on) silvers the cloud near it, a lightning flash
(shared["flash"]) lights the deck, and the open-sky mask of the scenery (wx_util.scene_geometry) hides the clouds
behind the skyline, ridges and trees.  The deck is drawn in the sky pass (behind the fireworks); a thin copy in the
over pass veils bursts inside the deck.

update() (as the JS): wind aloft = 2 x env.wind; layer i (depth z_i m) scrolls off_i += 2 wind 1.5 H / z_i dt / 4
(low-res px, wrapping around the texture width).
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QBrush, QImage, QPainter, QRadialGradient

from effects.fx_base import register_weather
from effects.scenery_noise import prng
from effects.wx_util import (PXM, clamp, draw_scrolled, fbm_p, lights, premul_image, rgba, scene_geometry,
                             sky_tone, smooth_v)

DIV = 4                          # view px per cloud pixel
FMT = QImage.Format.Format_ARGB32_Premultiplied
ATOP = QPainter.CompositionMode.CompositionMode_SourceAtop


def texture(L: dict, w: int, h: int, H: float, o: dict, tone: dict) -> QImage:
    """A shaded cloud texture (w x h low-res px, periodic in x): rgb = shading, alpha = density."""
    base_y, thr = L["base"] * H / DIV, 1 - L["cover"]
    cells = L["cells"]
    cells_y = max(2, round(cells * h / w * 2.2))
    core = np.array(tone["top"], float) * (1 - 0.55 * o["dark"])
    edge = np.array((74, 80, 100), float) * (1 - 0.45 * o["dark"])
    under = np.array(tone["under"], float) * (1 - 0.3 * o["dark"])
    u = (np.arange(w) / w)[None, :]
    j = np.arange(h)[:, None].astype(float)
    ragged = base_y * (0.82 + 0.3 * fbm_p(L["seed"] + 77, u * cells * 2, 0.5 + 0 * u, cells * 2, 1e6, 3))
    pp = j / ragged                                           # 0 at the top, 1 at the (ragged) base
    n = fbm_p(L["seed"], u * cells + 0 * j, j / h * cells_y + 0 * u, cells, 1e6, 5)
    shape = n + 0.18 * (1 - pp) - 0.6 * np.maximum(0, pp - 0.75) * 4
    a = smooth_v(thr - 0.12, thr + 0.22, shape) * L["a"]
    thick = smooth_v(thr, thr + 0.45, shape)[..., None]       # thick cores are dark; thin edges catch the light
    lit = (smooth_v(0.55, 1.0, pp) * 0.8)[..., None]          # underside lit by the ground and the town
    v = edge + (core - edge) * thick
    arr = np.empty((h, w, 4))
    arr[..., :3] = np.rint(v + (under - v) * lit * (0.4 + 0.6 * thick))
    arr[..., 3] = np.rint(255 * np.clip(a, 0, 1))
    return premul_image(arr)


class Clouds:
    """opts: cover (0..1), base (deck bottom, fraction of H), dark (0..1), over (alpha of the copy in front)."""

    def __init__(self, env, cover=0.6, base=0.34, dark=0.3, over=0.32, shared: dict | None = None):
        self.o = dict(cover=cover, base=base, dark=dark, over=over)
        self.shared = shared if shared is not None else {}
        seed = (env.seed ^ 0xC10D) & 0xFFFFFFFF
        R = prng(seed)
        self.layers = [dict(z=2600, cells=4, cover=cover, base=base, a=1.0, off=R() * 1000, seed=seed, tex=None),
                       dict(z=1100, cells=8, cover=cover * 0.55, base=base * 1.08, a=0.7, off=R() * 1000,
                            seed=seed + 5003, tex=None)]
        self.W = self.H = 1
        self.vx = 0.0
        self.wc = None
        self.resize(env)

    def resize(self, env):
        self.W, self.H = env.W, env.H
        for L in self.layers:
            L["tex"] = None
        self.wc = None

    def update(self, dt, env):
        if env.W != self.W or env.H != self.H:
            self.resize(env)
        wind = 2 * (env.wind or 0.0) * (0.5 if env.reduced else 1.0)
        s = 0.0
        for L in self.layers:
            v = wind * PXM(env, L["z"]) / DIV
            L["off"] += v * dt
            s += v
        self.vx = s / len(self.layers)

    def stats(self):
        return dict(count=len(self.layers), vx=self.vx)

    def state(self):
        return [L["off"] for L in self.layers]

    def _render(self, env) -> QImage:
        """The cloud deck of this frame (low-res): scrolled textures, burst light, moon, lightning, sky mask."""
        o, W, H = self.o, self.W, self.H
        w, h = math.ceil(W / DIV), max(1, math.ceil(H * min(0.75, o["base"] * 1.5) / DIV))
        tone = sky_tone(env)
        if self.wc is None or (self.wc.width(), self.wc.height()) != (w, h):
            self.wc = QImage(w, h, FMT)
        self.wc.fill(0)
        x = QPainter(self.wc)
        for L in self.layers:
            if L["tex"] is None:
                L["tex"] = texture(L, w, h, H, o, tone)
            draw_scrolled(x, L["tex"], L["off"] % w, 0, w)
        x.setCompositionMode(ATOP)                            # burst light from below / inside
        for lx, ly, lr, LI, col in lights(env)[:6]:
            if LI < 0.03:
                continue
            r, lx, ly, a = lr / DIV, lx / DIV, ly / DIV, min(0.6, 0.2 * LI)
            gr = QRadialGradient(QPointF(lx, ly), r)
            gr.setColorAt(0, rgba(tuple(min(255, v * 0.6 + 90) for v in col), a))
            gr.setColorAt(0.35, rgba(col, a * 0.35))
            gr.setColorAt(1, rgba(col, 0))
            x.fillRect(QRectF(lx - r, ly - r, 2 * r, 2 * r), QBrush(gr))
        M = getattr(env.scenery, "moon", None)                # the Moon sky effect (when on): moonlit rims
        if M and M.get("time") == env.time:
            r, mx, my = max(8, M["r"] * 7) / DIV, M["x"] / DIV, M["y"] / DIV
            gr = QRadialGradient(QPointF(mx, my), r)
            gr.setColorAt(0, rgba((225, 230, 245), 0.75))
            gr.setColorAt(0.25, rgba((170, 182, 210), 0.4))
            gr.setColorAt(1, rgba((120, 130, 160), 0))
            x.fillRect(QRectF(mx - r, my - r, 2 * r, 2 * r), QBrush(gr))
        f = clamp(self.shared.get("flash", 0) or 0, 0, 1.5)
        if f > 0.01:                                          # lightning lights the deck from inside
            fx = (self.shared.get("flashX", W / 2)) / DIV
            fy = (self.shared.get("flashY", H * 0.2)) / DIV
            gr = QRadialGradient(QPointF(fx, fy), w * 0.7)
            gr.setColorAt(0, rgba((215, 220, 255), min(0.85, 0.65 * f)))
            gr.setColorAt(1, rgba((150, 160, 215), min(0.5, 0.3 * f)))
            x.fillRect(QRectF(0, 0, w, h), QBrush(gr))
        mask = scene_geometry(env).mask(DIV)                  # hide the deck behind the scenery
        if mask is not None:
            x.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            x.drawImage(0, 0, mask)
        x.end()
        return self.wc

    def draw_sky(self, p, env):
        wc = self._render(env)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF(0, 0, wc.width() * DIV, wc.height() * DIV), wc)

    def draw_over(self, p, env):
        if self.wc is None or self.o["over"] <= 0:
            return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setOpacity(self.o["over"])
        p.drawImage(QRectF(0, 0, self.wc.width() * DIV, self.wc.height() * DIV), self.wc)
        p.setOpacity(1)


def make_clouds(env, shared: dict | None = None, **opts) -> Clouds:
    return Clouds(env, shared=shared, **opts)


register_weather("Clouds", "Clouds", lambda env: make_clouds(env))
