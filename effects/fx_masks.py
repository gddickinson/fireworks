"""Helpers of the sky-effect and scene plug-ins (effects/sky_fx.py, sky_aurora.py, scene_fx.py): a port of
web/static/fw_fx_masks.js.

Masks of the open sky and of the water from the scenery's material map (blue = sky, green = water), scaled to the
view (env.W x env.H) and cached per scenery and size, so a moon or an aurora disappears behind hills and buildings
and is reflected only on water; `masked()` draws through a mask via a shared scratch image; soft round sprites;
small numeric helpers.  Nothing here runs in update(), so the plug-ins' state stays testable without painting.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QRadialGradient

FMT = QImage.Format.Format_ARGB32_Premultiplied
_cache: dict = {}        # id(scenery) -> (scenery, key, {"sky": QImage, "water": QImage})
_scratch = {"img": None}
_sprites: dict = {}


def _image_array(img: QImage) -> np.ndarray:
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    a = np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)
    return a[:, :img.width()]


def masks(env) -> dict | None:
    """{"sky": QImage, "water": QImage} at env.W x env.H (premultiplied white, alpha = sky / water), or None."""
    S = env.scenery
    if S is None or getattr(S, "mat", None) is None:
        return None
    W, H = max(1, int(env.W)), max(1, int(env.H))
    key = (W, H)
    e = _cache.get(id(S))
    if e is not None and e[0] is S and e[1] == key:
        return e[2]
    small = S.mat.scaled(W, H, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGB32)
    px = _image_array(small)                              # B, G, R, A bytes
    out = {}
    for name, ch in (("sky", 0), ("water", 1)):           # blue (byte 0) = sky, green (byte 1) = water
        a = px[..., ch]
        rgba = np.ascontiguousarray(np.repeat(a[..., None], 4, axis=2))   # premultiplied white
        out[name] = QImage(rgba.tobytes(), W, H, W * 4, FMT).copy()
    if len(_cache) > 8:
        _cache.clear()
    _cache[id(S)] = (S, key, out)
    return out


def _scratch_image(W: int, H: int) -> QImage:
    img = _scratch["img"]
    if img is None or img.width() != W or img.height() != H:
        img = _scratch["img"] = QImage(W, H, FMT)
    img.fill(0)
    return img


def masked(p: QPainter, env, which: str, fn, alpha: float = 1.0) -> None:
    """fn(painter) paints into a scratch layer, which is cut to the sky (or water) and drawn onto p with `alpha`.
    Without a scenery (no masks) fn paints straight onto p."""
    M = masks(env)
    if M is None:
        p.save()
        p.setOpacity(alpha)
        fn(p)
        p.restore()
        return
    W, H = max(1, int(env.W)), max(1, int(env.H))
    L = _scratch_image(W, H)
    lp = QPainter(L)
    lp.setRenderHint(QPainter.RenderHint.Antialiasing)
    lp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    lp.setPen(Qt.PenStyle.NoPen)
    fn(lp)
    lp.setOpacity(1.0)
    lp.resetTransform()
    lp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    lp.drawImage(0, 0, M[which])
    lp.end()
    p.save()
    p.setOpacity(alpha)
    p.drawImage(0, 0, L)
    p.restore()


def soft_sprite(col, core: float = 0.15) -> QImage:
    """Soft radial sprite (128 x 128, cached per colour): draw it into a 2r x 2r rect centred on the point."""
    key = (tuple(int(v) for v in col), core)
    img = _sprites.get(key)
    if img is None:
        img = QImage(128, 128, FMT)
        img.fill(0)
        g = QRadialGradient(QPointF(64, 64), 64)
        r, gg, b = key[0]
        g.setColorAt(0, QColor(r, gg, b, 255))
        g.setColorAt(core, QColor(r, gg, b, 128))
        g.setColorAt(1, QColor(r, gg, b, 0))
        q = QPainter(img)
        q.fillRect(0, 0, 128, 128, g)
        q.end()
        _sprites[key] = img
    return img


def draw_sprite(p: QPainter, img: QImage, x: float, y: float, w: float, h: float) -> None:
    p.drawImage(QRectF(x, y, w, h), img)


def k(env) -> float:
    """View px per scenery px."""
    return env.k


def water_px(env):
    """The waterline in view px, or None."""
    S = env.scenery
    return S.water * env.k if S is not None and getattr(S, "water", None) else None


def horizon_px(env) -> float:
    S = env.scenery
    hz = getattr(S, "horizon", None) if S is not None else None
    return (hz if hz is not None else 0.9) * env.H


def is_dusk(env) -> bool:
    return getattr(env.scenery, "time", "night") == "dusk"


def exp_wait(u: float, mean: float) -> float:
    """Exponential waiting time from a seeded uniform u in [0, 1)."""
    return -math.log(1 - u) * mean


def smooth(a: float, b: float, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
