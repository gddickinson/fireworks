"""Skies of the realistic scenery, aware of the time of day (S.time): a QPainter port of web/static/fw_scenery_sky.js.

  night (default) - near-black zenith, airglow, light-pollution `glow` over the horizon, stars and Milky Way
                    (exactly what effects/scenery.py drew before; the original five scenes are unchanged);
  dusk            - the blue hour: deep blue zenith, paler blue lower down, a warm afterglow band over the horizon
                    (strongest on the sunset side `sun_x`), the light-pollution glow on top, only the brightest stars,
                    no Milky Way; terrain colours lifted a little by the sky light (`tone`).
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter

from effects.scenery_noise import prng
from effects.scenery_parts import jround, milky_way, rgb, sky, stars, vgrad


def is_dusk(S) -> bool:
    return getattr(S, "time", "night") == "dusk"


def dark_sky(S, c, horizon, glow, low=None, glowH=None, sun_x=None) -> None:
    """Sky gradient from the top of the frame to `horizon` (px); glow: light-pollution colour or None."""
    W, H = S.W, S.H
    if not is_dusk(S):
        sky(c, W, H, (1, 2, 8), (4, 8, 22), low or (12, 20, 40), horizon, glow, glowH or 0.3)
        return
    p = c.p
    p.fillRect(QRectF(0, 0, W, H), QBrush(vgrad(0, horizon, [(0, rgb(6, 13, 40)), (0.45, rgb(16, 32, 78)),
                                                              (0.8, rgb(44, 62, 118)), (1, rgb(92, 96, 140))])))
    sx = W * (0.22 if sun_x is None else sun_x)                 # afterglow: warm, wide, low, on the sunset side
    band = H * 0.2
    for col, a, h, wr in (((255, 150, 90), 0.55, band, 1.1), ((250, 120, 80), 0.5, band * 0.45, 0.6)):
        hh = max(1, math.ceil(h))
        off = QImage(W, hh, QImage.Format.Format_ARGB32_Premultiplied)
        off.fill(0)
        o = QPainter(off)
        o.fillRect(QRectF(0, 0, W, h), QBrush(vgrad(0, h, [(0, rgb(*col, 0)), (0.65, rgb(*col, a * 0.45)),
                                                            (1, rgb(*col, a))])))
        hg = QLinearGradient(0, 0, W, 0)                        # fades away from the sunset side
        for i in range(9):
            x = i / 8
            d = (x * W - sx) / (W * wr)
            hg.setColorAt(x, rgb(0, 0, 0, max(0.25, math.exp(-d * d))))
        o.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        o.fillRect(QRectF(0, 0, W, hh), QBrush(hg))
        o.end()
        p.drawImage(QRectF(0, horizon - h, W, hh), off)
    if glow:                                                    # town light still adds its colour near the horizon
        y0 = horizon - H * 0.12
        p.fillRect(QRectF(0, y0, W, H * 0.12), QBrush(vgrad(y0, horizon, [(0, rgb(*glow, 0)), (1, rgb(*glow, 0.25))])))


def starry(S, c, seed, horizon, n=1.0, milky=1.0, angle=-0.55, cx=0.62) -> None:
    W, H, rnd = S.W, S.H, prng(seed)
    if is_dusk(S):                                              # a few of the brightest stars and planets only
        stars(c, W, H, rnd, jround(W * H / 260 * n * 0.1), horizon * 0.75, dim=0.75)
        return
    dist = milky_way(c, W, H, seed, horizon, angle, cx, milky) if milky > 0 else None
    stars(c, W, H, rnd, jround(W * H / 260 * n), horizon, milky=dist)


def tone(S, col, haze=0.5) -> tuple:
    """Terrain/building colour at the time of day: at dusk the sky light lifts and blues the shadows.
    haze 0 (foreground) .. 1 (far away)."""
    if not is_dusk(S):
        return tuple(col)
    k = 1.35 + haze * 0.9
    add = [v * (0.4 + haze) for v in (6, 10, 26)]
    return tuple(min(255.0, v * k + add[i]) for i, v in enumerate(col))


def qc(col, a: float = 1.0) -> QColor:
    """rgb() of a colour tuple."""
    return rgb(*col, a)
