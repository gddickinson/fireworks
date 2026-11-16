"""QPainter renderer of the realistic mode (the look of web/static/fw_render_2d.js, without WebGL).

Layers, back to front, for one frame of a `gui.real_show.RealShow`:
  1. the scene: the existing background object (effects/backgrounds.py) or a plain colour;
  2. sky illumination: the strongest burst lights as additive radial gradients on a quarter-size image, scaled up;
  3. the firework trails: a persistent ARGB32_Premultiplied image, faded every frame (DestinationIn, alpha 0.78),
     on which every star is drawn additively (CompositionMode_Plus) as a soft sprite (gui/real_sprites.py);
     the image is added to the frame;
  4. bloom: the trail image shrunk to 1/8 and stretched back with smooth filtering, added again;
  5. water (Beach): a dimmed, vertically squashed mirror image of the trails below the waterline;
  6. weather (drawn normally on top) and a vignette.
Projection as models/pyro.py: screen x = W/2 + FOCAL*H*x/z, y = horizon*H - FOCAL*H*y/z.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QRadialGradient

from gui.real_sprites import SpriteCache
from models.pyro import FOCAL
from models.pyro_colors import star_rgb

PERSIST = 0.78        # trail alpha kept per frame
BLOOM = 0.9           # opacity of the added blurred copy
BLOOM_DIV = 8
LIGHT_DIV = 4
CROWD = 2500          # stars above which faint ones are skipped (keeps a finale near 60 fps)
REFLECT = 0.4         # opacity of the reflection on water
PLUS = QPainter.CompositionMode.CompositionMode_Plus
OVER = QPainter.CompositionMode.CompositionMode_SourceOver
FMT = QImage.Format.Format_ARGB32_Premultiplied
CLEAR_BITS = QColor(255, 255, 255, 3)   # premultiplied pixel 0x03030303 (the two low bits of every channel)


class RealPainter:
    def __init__(self):
        self.sprites = SpriteCache()
        self.W = self.H = 0
        self.trail = None
        self.vignette = None
        self.lights_img = None
        self.frame = 0
        self.drawn = 0          # stars drawn in the last frame (for profiling/tests)

    # --- buffers --------------------------------------------------------------------------------------------
    def resize(self, W: int, H: int) -> None:
        W, H = max(1, int(W)), max(1, int(H))
        if (W, H) == (self.W, self.H):
            return
        self.W, self.H = W, H
        self.trail = QImage(W, H, FMT)
        self.trail.fill(0)
        self.lights_img = QImage(max(1, W // LIGHT_DIV), max(1, H // LIGHT_DIV), FMT)
        self.vignette = _vignette(W, H)

    def clear(self) -> None:
        if self.trail is not None:
            self.trail.fill(0)

    # --- the frame ------------------------------------------------------------------------------------------
    def render(self, p: QPainter, W: int, H: int, show, background=None, weather=None, base_color=None,
               water_y=None) -> None:
        """Paint one frame of `show` (gui.real_show.RealShow) into p over the rect (0, 0, W, H)."""
        self.resize(W, H)
        W, H = self.W, self.H
        p.save()
        p.setCompositionMode(OVER)
        p.fillRect(0, 0, W, H, base_color if base_color is not None else QColor(0, 0, 0))
        if background is not None:
            background.draw(p)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._lights(p, show)
        self._trails(show)
        full = QRectF(0, 0, W, H)
        small = self.trail.scaled(max(1, W // BLOOM_DIV), max(1, H // BLOOM_DIV),
                                  Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        p.setCompositionMode(PLUS)
        p.drawImage(0, 0, self.trail)
        p.setOpacity(BLOOM)
        p.drawImage(full, small)
        if water_y is not None and water_y < H:
            p.save()
            p.setClipPath(beach_water_path(W, H, water_y))
            p.setOpacity(REFLECT)
            p.translate(0, water_y)
            p.scale(1.0, -0.85)
            p.translate(0, -water_y)
            p.drawImage(0, 0, self.trail)
            p.drawImage(full, small)
            p.restore()
        p.setOpacity(1.0)
        p.setCompositionMode(OVER)
        if weather is not None:
            weather.draw(p)
        p.drawImage(0, 0, self.vignette)
        p.restore()
        self.frame += 1

    def _lights(self, p: QPainter, show) -> None:
        lights = show.screen_lights(self.W, self.H)
        if not lights:
            return
        img = self.lights_img
        img.fill(0)
        k = img.width() / self.W
        lp = QPainter(img)
        lp.setCompositionMode(PLUS)
        lp.setPen(Qt.PenStyle.NoPen)
        for x, y, r, inten, col in lights:
            a = min(1.0, inten * 0.35)
            r, x, y = r * k * 3.0, x * k, y * k
            g = QRadialGradient(QPointF(x, y), r)
            g.setColorAt(0.0, QColor(int(col[0] * a * 0.55), int(col[1] * a * 0.55), int(col[2] * a * 0.55),
                                     int(255 * a * 0.55)))
            g.setColorAt(0.35, QColor(int(col[0] * a * 0.18), int(col[1] * a * 0.18), int(col[2] * a * 0.18),
                                      int(255 * a * 0.18)))
            g.setColorAt(1.0, QColor(0, 0, 0, 0))
            lp.setBrush(g)
            lp.drawRect(QRectF(x - r, y - r, 2 * r, 2 * r))
        lp.end()
        p.setCompositionMode(PLUS)
        p.drawImage(QRectF(0, 0, self.W, self.H), img)
        p.setCompositionMode(OVER)

    def _trails(self, show) -> None:
        tp = QPainter(self.trail)
        tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        tp.fillRect(0, 0, self.W, self.H, QColor(0, 0, 0, int(255 * PERSIST)))
        if self.frame % 4 == 0:
            # 8-bit rounding keeps values of 1-2 forever under DestinationIn: clear the two low bits now and then
            tp.setCompositionMode(QPainter.CompositionMode.RasterOp_NotSourceAndDestination)
            tp.fillRect(0, 0, self.W, self.H, CLEAR_BITS)
        tp.setCompositionMode(PLUS)
        self.drawn = self._stars(tp, show.sim)
        tp.end()

    def _stars(self, tp: QPainter, sim) -> int:
        """Draw the visible stars as sprites; the loop is inlined for speed (~4000 stars in a finale)."""
        W, H = self.W, self.H
        F, hz, W2 = FOCAL * H, sim.horizon * H, W / 2.0
        min_core = 1.1 * H / 900.0
        cache, make = self.sprites.cache, self.sprites.make
        exp, sqrt = math.exp, math.sqrt
        t = sim.time
        n = 0
        last_op = -1
        stars = sim.stars
        faint = 0.02 if len(stars) < CROWD else 0.07     # crowded sky (finale): skip the faintest sparks
        set_opacity, draw = tp.setOpacity, tp.drawImage
        for s in stars:
            if s.age < 0.0:
                continue
            r, g, b, i = star_rgb(s, t)
            if i <= 0.004:
                continue
            z = s.z
            x = W2 + F * s.x / z
            y = hz - F * s.y / z
            if x < -40 or x > W + 40 or y < -40 or y > H + 40:
                continue
            m = r if r > g else g
            if b > m:
                m = b
            if m < 1.0:
                continue
            L = m * i * 0.0036863 * exp((300.0 - z) / 2600.0)        # 0.94 / 255
            if s.kind == "spark":
                L *= 0.8
            core = F * 0.42 * s.size / z
            if core < min_core:
                core = min_core
            if L > 1.0:
                core *= sqrt(L) if L < 4.0 else 2.0
                L = 1.0
            elif L < faint:
                continue
            k = 15.99 / m
            qs = int(core * 2.0 + 0.5)
            key = (int(r * k), int(g * k), int(b * k), qs if qs < 24 else 24)
            img, half = cache.get(key) or make(key)
            op = int(L * 50.0 + 0.5)
            if op != last_op:
                set_opacity(op * 0.02)
                last_op = op
            draw(QPointF(x - half, y - half), img)
            n += 1
        tp.setOpacity(1.0)
        return n


def beach_water_path(W: int, H: int, water_y: float) -> QPainterPath:
    """The water of BeachBackground: below the waterline, minus its sand (same curve as BeachBackground.draw)."""
    water = QPainterPath()
    water.addRect(QRectF(0, water_y, W, H - water_y))
    sand = QPainterPath()
    sand.moveTo(0, H)
    sand.lineTo(0, H * 0.75)
    sand.quadTo(W / 2, H * 0.68, W, H * 0.75)
    sand.lineTo(W, H)
    sand.closeSubpath()
    return water.subtracted(sand)


def _vignette(W: int, H: int) -> QImage:
    img = QImage(W, H, FMT)
    img.fill(0)
    p = QPainter(img)
    g = QRadialGradient(QPointF(W / 2, H / 2), math.hypot(W, H) / 2)
    g.setColorAt(0.0, QColor(0, 0, 0, 0))
    g.setColorAt(min(W, H) * 0.3 / (math.hypot(W, H) / 2), QColor(0, 0, 0, 0))
    g.setColorAt(1.0, QColor(0, 0, 0, 105))
    p.fillRect(0, 0, W, H, g)
    p.end()
    return img
