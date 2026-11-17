"""Painting primitives of the realistic scenery: a QPainter/numpy port of web/static/fw_scenery_parts.js.

Night-sky gradient with airglow and light pollution, star field with a magnitude distribution, Milky Way (computed
at low resolution with numpy, scaled up smoothly), fractal ridgelines with haze and snow, trees and palms, and
rippled water reflections.  Painters draw colour into a `Layer` (`c`) and, where it matters for lighting, material
into the material layer (`m`): red = albedo lit by bursts, green = water, blue = open sky.  The random draws
(effects/scenery_noise.prng) happen in the same order as in the JavaScript, so the scenes match the web ones.
Desktop-only differences: self-overlapping shapes use the non-zero fill rule like canvas 2D, and the water's
vertical smear is a true average of the mirrored rows.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

from effects.scenery_noise import fbm1, fbm2, ridged1

TAU = 6.2832


def jround(v: float) -> int:
    """JavaScript Math.round (halves round up)."""
    return int(math.floor(v + 0.5))


def rgb(r, g, b, a: float = 1.0) -> QColor:
    """CSS rgba(r|0, g|0, b|0, a)."""
    c = lambda v: max(0, min(255, int(v)))   # noqa: E731
    return QColor(c(r), c(g), c(b), max(0, min(255, jround(a * 255))))


def mat(albedo: float, water: float = 0.0, sky: float = 0.0) -> QColor:
    return rgb(albedo * 255, water * 255, sky * 255)


# --- layers ---------------------------------------------------------------------------------------------------
class Layer:
    """A QImage with a lazily opened antialiased QPainter (`p`); `array()` ends painting and returns a writable
    (H, W, 4) uint8 view of the pixels (B, G, R, A byte order)."""

    def __init__(self, W: int, H: int, fmt=QImage.Format.Format_ARGB32_Premultiplied, fill=0):
        self.W, self.H = W, H
        self.img = QImage(W, H, fmt)
        self.img.fill(fill)
        self._p = None

    @property
    def p(self) -> QPainter:
        if self._p is None:
            self._p = QPainter(self.img)
            self._p.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._p.setPen(Qt.PenStyle.NoPen)
        return self._p

    def end(self) -> QImage:
        if self._p is not None:
            self._p.end()
            self._p = None
        return self.img

    def array(self) -> np.ndarray:
        self.end()
        return image_array(self.img)


def image_array(img: QImage) -> np.ndarray:
    """Writable (H, W, 4) uint8 view of a 32-bit QImage (no painter may be active on it)."""
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    a = np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)
    return a[:, :img.width()]


def vgrad(y0: float, y1: float, stops) -> QLinearGradient:
    g = QLinearGradient(0, y0, 0, y1)
    for t, col in stops:
        g.setColorAt(t, col)
    return g


def fill_path(layer: Layer, path: QPainterPath, brush) -> None:
    p = layer.p
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(brush))
    p.drawPath(path)


# --- sky ------------------------------------------------------------------------------------------------------
def sky(c: Layer, W, H, top, mid, low, horizon, glow=None, glowH=0.25) -> None:
    p = c.p
    p.fillRect(QRectF(0, 0, W, H), QBrush(vgrad(0, horizon, [(0, rgb(*top)), (0.55, rgb(*mid)), (1, rgb(*low))])))
    if glow:                                                  # light pollution / last twilight above the horizon
        y0 = horizon - H * glowH
        g = vgrad(y0, horizon, [(0, rgb(*glow, 0)), (0.7, rgb(*glow, 0.35)), (1, rgb(*glow, 0.75))])
        p.fillRect(QRectF(0, y0, W, H * glowH), QBrush(g))
    y0, y1 = horizon - H * 0.16, horizon - H * 0.02            # faint green airglow band
    g = vgrad(y0, y1, [(0, rgb(40, 90, 60, 0)), (0.5, rgb(40, 90, 60, 0.07)), (1, rgb(40, 90, 60, 0))])
    p.fillRect(QRectF(0, y0, W, H * 0.14), QBrush(g))


STAR_COLS = ((170, 195, 255), (235, 238, 255), (255, 236, 205), (255, 200, 160))


def stars(c: Layer, W, H, rnd, n, horizon, dim=1.0, milky=None) -> None:
    """Counts grow steeply towards faint magnitudes; blue-white to orange; extinction near the horizon."""
    p = c.p
    s = max(1.0, H / 900)
    for _ in range(n):
        x = rnd() * W
        y = rnd() ** 1.25 * horizon
        m = rnd() ** 5.5                                        # most stars faint, a few bright
        if milky is not None and abs(milky(x, y)) < 0.12 * H:
            m = max(m, rnd() ** 3.5 * 0.6)
        ext = min(1.0, (horizon - y) / (horizon * 0.35))
        a = (0.12 + 0.88 * m) * ext * dim
        if a < 0.03:
            continue
        t = rnd()
        col = STAR_COLS[0 if t < 0.2 else 1 if t < 0.75 else 2 if t < 0.93 else 3]
        r = (0.35 + 0.95 * m) * s
        p.setBrush(rgb(*col, a))
        p.drawEllipse(QPointF(x, y), r, r)
        if m > 0.9:
            g = QRadialGradient(QPointF(x, y), r * 6)
            g.setColorAt(0, rgb(*col, 0.18 * a))
            g.setColorAt(1, rgb(*col, 0))
            p.fillRect(QRectF(x - r * 6, y - r * 6, r * 12, r * 12), QBrush(g))


def milky_way(c: Layer, W, H, seed, horizon, angle=-0.5, cx=0.6, strength=1.0):
    """Diffuse band with mottled star clouds and dark dust lanes, computed on a 256-wide grid and scaled up.
    Returns dist(x, y): signed distance (px) of a point from the band's centre line."""
    lw, lh = 256, max(32, jround(256 * horizon / W))
    ca, sa, x0, y0, width = math.cos(angle), math.sin(angle), cx * W, horizon * 0.45, H * 0.16

    def dist(x, y):
        return -(x - x0) * sa + (y - y0) * ca

    x = ((np.arange(lw) + 0.5) * W / lw)[None, :]
    y = ((np.arange(lh) + 0.5) * horizon / lh)[:, None]
    u = dist(x, y) / width
    along = ((x - x0) * ca + (y - y0) * sa) / width
    band = np.exp(-u * u * 1.6)
    cloud = fbm2(seed, along * 0.9, u * 1.4, 5)
    lane = (np.maximum(0, 1 - 2.2 * np.abs(u + 0.25 * (fbm2(seed + 9, along * 0.6, 0.3, 3) - 0.5)))
            * np.maximum(0, fbm2(seed + 5, along * 1.6, u * 2.5, 4) - 0.35) * 2.2)
    ext = np.minimum(1, (horizon - y) / (horizon * 0.4))
    v = np.maximum(0, band * (0.35 + 0.9 * cloud) - lane * band * 0.9) * ext * strength
    rgba = np.empty((lh, lw, 4), np.uint8)
    rgba[..., 0] = np.clip(np.rint(150 + 60 * cloud), 0, 255)
    rgba[..., 1] = np.clip(np.rint(150 + 40 * cloud), 0, 255)
    rgba[..., 2] = 190
    rgba[..., 3] = np.clip(np.rint(np.minimum(255, v * 70)), 0, 255)
    img = QImage(rgba.tobytes(), lw, lh, lw * 4, QImage.Format.Format_RGBA8888).copy()
    # two smooth steps (x4, then to size) so the bilinear upscaling shows no blocks
    img = img.scaled(lw * 4, lh * 4, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    p = c.p
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRectF(0, 0, W, horizon), img)
    p.restore()
    return dist


# --- terrain --------------------------------------------------------------------------------------------------
def ridge_line(W, H, seed, base, amp, rough=3.0, sharp=0.6, step=2, taper=None):
    """y (px) of a ridge per x column (every `step` px, x = 0 .. W + step): (ys, step)."""
    x = np.arange(0, W + step + 1, step, dtype=np.float64)
    u = x / W * rough
    r, f = ridged1(seed, u + 3.1, 7), fbm1(seed + 7, u * 1.7, 6)
    detail = fbm1(seed + 11, u * 14, 4) - 0.5                  # rocky, jagged small scale
    v = sharp * r + (1 - sharp) * f + detail * 0.08
    if taper is not None:
        v = v * taper(x / W)
    return H * (base - amp * v), step


def ridge_path(W, ridge, bottom) -> QPainterPath:
    ys, step = ridge
    path = QPainterPath()
    path.moveTo(0, bottom)
    for i, y in enumerate(ys.tolist()):
        path.lineTo(i * step, y)
    path.lineTo(W, bottom)
    path.closeSubpath()
    return path


def range_(c: Layer, m: Layer, W, H, seed, opts: dict, col_top, col_bot, albedo, bottom=None):
    """A ridge range filled with a vertical gradient on c (hazier crest) and its material on m."""
    bottom = H if bottom is None else bottom
    r = ridge_line(W, H, seed, **opts)
    path = ridge_path(W, r, bottom)
    fill_path(c, path, vgrad(float(r[0].min()), bottom, [(0, rgb(*col_top)), (1, rgb(*col_bot))]))
    fill_path(m, path, mat(albedo))
    return r


def snow(c: Layer, m: Layer, ridge, line, depth, seed) -> None:
    """Snow caps (as fw_scenery_parts.js since 7ff6914): one polygon per stretch of crest above `line` (px) with a
    noise-shaped lower edge, shaded by slope through a smooth horizontal gradient and faded downwards."""
    ys, step = ridge
    n = len(ys)
    xs = np.arange(n) * step
    lower = ys + np.maximum(0, np.minimum(depth, (line - ys) * 0.9) * (0.35 + 0.95 * fbm1(seed, xs * 0.018, 5)))
    csum = np.concatenate([[0.0], np.cumsum(ys)])

    def smooth_y(i):                                          # mean of ys[i-6 .. i+6] that exist
        lo, hi = max(0, i - 6), min(n, i + 7)
        return (csum[hi] - csum[lo]) / (hi - lo) if hi > lo else ys[min(max(i, 0), n - 1)]

    def draw(idx):
        if len(idx) < 3:
            return
        x0, x1 = idx[0] * step, idx[-1] * step
        top, bot = float(ys[idx].min()), float(lower[idx].max())
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.moveTo(xs[idx[0]], ys[idx[0]])
        for i in idx[1:]:
            path.lineTo(xs[i], ys[i])
        for i in idx[::-1]:
            path.lineTo(xs[i], lower[i])
        path.closeSubpath()
        hg = QLinearGradient(x0, 0, x1 + 0.01, 0)
        for i in idx[::3]:                                    # slope -> brightness, smooth along x
            slope = (smooth_y(i + 3) - smooth_y(i - 3)) / (6 * step)
            br = min(1.0, max(0.0, 0.5 + slope * 1.6))
            hg.setColorAt((i * step - x0) / max(1, x1 - x0),
                          rgb(105 + 80 * br, 115 + 78 * br, 148 + 70 * br, 0.5 + 0.25 * br))
        ox, oy = int(math.floor(x0)) - 1, int(math.floor(top)) - 1
        off = QImage(int(x1 - ox) + 3, int(bot - oy) + 3, QImage.Format.Format_ARGB32_Premultiplied)
        off.fill(0)
        o = QPainter(off)
        o.setRenderHint(QPainter.RenderHint.Antialiasing)
        o.translate(-ox, -oy)
        o.setPen(Qt.PenStyle.NoPen)
        o.setBrush(QBrush(hg))
        o.drawPath(path)
        o.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        o.fillRect(QRectF(ox, oy, off.width(), off.height()),
                   QBrush(vgrad(top, bot + 1, [(0, QColor(0, 0, 0, 255)), (1, QColor(0, 0, 0, 31))])))
        o.end()
        c.p.drawImage(ox, oy, off)
        fill_path(m, path, mat(0.85))

    run = []
    for i, above in enumerate((ys < line).tolist()):
        if above:
            run.append(i)
        else:
            draw(run)
            run = []
    draw(run)


# --- trees ----------------------------------------------------------------------------------------------------
def conifer(x, y, h, rnd) -> QPainterPath:
    """Layered jagged tiers at base (x, y), height h."""
    w, tiers = h * (0.28 + rnd() * 0.12), 6 + int(rnd() * 4)
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    path.moveTo(x, y - h)
    for i in range(1, tiers + 1):
        t = i / tiers
        ty, tw = y - h + h * 0.92 * t, w * t * (0.75 + rnd() * 0.35)
        path.lineTo(x + tw, ty)
        path.lineTo(x + tw * 0.45, ty - h * 0.02)
    path.lineTo(x + w * 0.08, y)
    path.lineTo(x - w * 0.08, y)
    for i in range(tiers, 0, -1):
        t = i / tiers
        ty, tw = y - h + h * 0.92 * t, w * t * (0.75 + rnd() * 0.35)
        path.lineTo(x - tw * 0.45, ty - h * 0.02)
        path.lineTo(x - tw, ty)
    path.closeSubpath()
    return path


def broadleaf(x, y, h, rnd) -> QPainterPath:
    """Trunk and a crown of many small clumps inside an irregular ellipse."""
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    path.moveTo(x - h * 0.035, y)
    path.lineTo(x - h * 0.015, y - h * 0.5)
    path.lineTo(x + h * 0.015, y - h * 0.5)
    path.lineTo(x + h * 0.035, y)
    path.closeSubpath()
    n, rx, ry = 40 + int(rnd() * 20), h * (0.26 + rnd() * 0.1), h * 0.24
    for _ in range(n):
        a, d = rnd() * TAU, math.sqrt(rnd())
        cx, cy, rr = x + math.cos(a) * rx * d, y - h * 0.68 + math.sin(a) * ry * d, h * (0.03 + rnd() * 0.06)
        path.addEllipse(QPointF(cx, cy), rr, rr)
    return path


def palm(x, y, h, lean, rnd) -> list:
    """Curved tapering trunk and arching fronds with hanging leaflets, as drawing ops [(path, None | line width)]
    (None: fill) so the same shapes go on the colour and material layers."""
    tx, ty, bx, by = x + lean * h * 0.35, y - h, x + lean * h * 0.05, y - h * 0.6
    ops = []
    trunk = QPainterPath()
    w0, w1 = h * 0.03, h * 0.016
    trunk.moveTo(x - w0, y)
    trunk.quadTo(bx - w1, by, tx - w1, ty)
    trunk.lineTo(tx + w1, ty)
    trunk.quadTo(bx + w1, by, x + w0, y)
    trunk.closeSubpath()
    ops.append((trunk, None))
    fronds = 9 + int(rnd() * 4)
    for i in range(fronds):
        a = (i / fronds) * TAU + rnd() * 0.4
        dr, up = math.cos(a), math.sin(a) * 0.5 + 0.2
        ln = h * (0.34 + rnd() * 0.16)
        ex, ey = tx + dr * ln, ty + ln * (0.45 - up * 0.3) + ln * 0.2 * (1 - abs(dr))
        mx, my = tx + dr * ln * 0.55, ty - ln * (0.18 + up * 0.25)
        rib = QPainterPath()
        rib.moveTo(tx, ty)
        rib.quadTo(mx, my, ex, ey)
        ops.append((rib, h * 0.008))
        for k in range(2, 22):                                # leaflets along the rib
            t = k / 22
            px = (1 - t) * (1 - t) * tx + 2 * (1 - t) * t * mx + t * t * ex
            py = (1 - t) * (1 - t) * ty + 2 * (1 - t) * t * my + t * t * ey
            l = ln * (0.1 + 0.08 * rnd()) * math.sin(math.pi * min(1.0, t * 1.15))   # noqa: E741
            sx = dr * l * 0.55
            width = h * (0.004 + rnd() * 0.003)
            leaf = QPainterPath()
            leaf.moveTo(px, py)
            leaf.lineTo(px + sx + l * 0.25, py + l * 0.9)
            leaf.moveTo(px, py)
            leaf.lineTo(px + sx - l * 0.25, py + l * 0.85)
            ops.append((leaf, width))
    nuts = QPainterPath()
    for _ in range(4):
        nuts.addEllipse(QPointF(tx + (rnd() - 0.5) * h * 0.04, ty + h * 0.02), h * 0.012, h * 0.012)
    ops.append((nuts, None))
    return ops


def draw_ops(layer: Layer, ops: list, col: QColor) -> None:
    p = layer.p
    for path, width in ops:
        if width is None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
        else:
            p.setPen(QPen(col, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)


# --- water ----------------------------------------------------------------------------------------------------
def water(c: Layer, m: Layer, W, H, wl, seed, tint=(8, 14, 28), reflect=0.55) -> None:
    """Water below `wl` (px): base gradient, then a rippled, darkened, vertically smeared mirror image of the
    scene above it (numpy: each water row averages the mirrored source rows its smear covers)."""
    top = int(math.ceil(wl))
    src = c.array()[:top, :, :3].astype(np.float32)
    cum = np.concatenate([np.zeros((1, W, 3), np.float32), np.cumsum(src, axis=0, dtype=np.float32)])
    g = vgrad(wl, H, [(0, rgb(*(v * 1.6 for v in tint))), (1, rgb(*(v * 0.5 for v in tint)))])
    c.p.fillRect(QRectF(0, wl, W, H - wl), QBrush(g))
    dst = c.array()
    strip = max(1, jround(H / 700))
    xs = np.arange(W, dtype=np.float64)
    y = wl
    while y < H:
        d = y - wl
        sy = wl - d * 0.85 - 1                                  # mirrored row (slightly compressed)
        if sy < 0:
            break
        off = float((fbm2(seed, 0.3, d * 0.05, 3) - 0.5) * (1 + d * 0.03) + math.sin(d * 0.3) * (0.2 + d * 0.004))  # smooth
        smear = min(sy, 1 + d * 0.35)                           # vertical smear grows away from the shore line
        alpha = reflect * max(0.25, 1 - d / (H - wl) * 0.6)
        a = max(0, min(top - 1, int(sy - smear)))
        b = max(a + 1, min(top, int(math.ceil(sy + strip))))
        row = (cum[b] - cum[a]) / (b - a)                       # (W, 3)
        sx = np.clip(xs - off, 0, W - 1)
        i0 = sx.astype(np.int64)
        fr = (sx - i0)[:, None]
        i1 = np.minimum(i0 + 1, W - 1)
        row = row[i0] * (1 - fr) + row[i1] * fr
        y0, y1 = int(round(y)), min(H, int(round(y + strip)))
        if y1 > y0:
            blk = dst[y0:y1, :, :3]
            blk[:] = np.clip(blk * (1 - alpha) + row[None] * alpha + 0.5, 0, 255).astype(np.uint8)
        y += strip
    m.p.fillRect(QRectF(0, wl, W, H - wl), mat(0.12, 1))
