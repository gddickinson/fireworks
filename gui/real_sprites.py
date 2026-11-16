"""Soft star sprites for the realistic renderer (gui/real_painter.py).

A sprite is a small ARGB32_Premultiplied image holding a radial gradient: a hot, nearly white core that fades into
the star's colour and then to transparent.  Sprites are drawn with CompositionMode_Plus, so overlapping stars add
up like light.  They are cached per quantised colour (16 levels per channel) and size (half-pixel steps); the cache
is cleared when it grows past MAX_SPRITES.  Brightness is not part of the key: the painter draws a sprite with
QPainter.setOpacity, so dim and fading stars reuse the same few images.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QRadialGradient

MAX_SPRITES = 3000
GLOW = 2.6            # sprite radius / star core radius


class SpriteCache:
    def __init__(self):
        self.cache: dict = {}

    def __len__(self):
        return len(self.cache)

    def get(self, r: float, g: float, b: float, core: float):
        """(image, half size) for a star of hue r, g, b (brightest channel ~255; the caller sets the painter's
        opacity for its brightness) and core radius in px."""
        key = (min(15, int(r) >> 4), min(15, int(g) >> 4), min(15, int(b) >> 4),
               min(24, max(1, int(core * 2 + 0.5))))
        return self.cache.get(key) or self.make(key)

    def make(self, key: tuple):
        """Build the sprite for key = (r, g, b in 0-15, core radius in half pixels 1-24) (hot loops look up
        `cache` themselves and call this on a miss)."""
        if len(self.cache) >= MAX_SPRITES:
            self.cache.clear()
        qr, qg, qb, qs = key
        hit = self.cache[key] = _make(qr * 17, qg * 17, qb * 17, qs * 0.5)
        return hit


def _make(r: int, g: int, b: int, core: float):
    rad = max(1.5, core * GLOW)
    size = int(rad * 2 + 2) | 1
    half = size / 2.0
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QRadialGradient(QPointF(half, half), rad)
    m = max(r, g, b, 1)
    hot = [min(255, int(c + (255 - c) * 0.55 * m / 255)) for c in (r, g, b)]   # white-hot centre
    grad.setColorAt(0.0, QColor(hot[0], hot[1], hot[2], 255))
    grad.setColorAt(min(0.9, 0.9 / GLOW), QColor(r, g, b, 230))
    grad.setColorAt(0.55, QColor(r, g, b, 60))
    grad.setColorAt(1.0, QColor(r, g, b, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawEllipse(QPointF(half, half), rad, rad)
    p.end()
    return img, half
