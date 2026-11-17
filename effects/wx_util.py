"""Shared helpers of the realistic weather plug-ins (effects/wx_*.py): a numpy/QPainter port of web/static/fw_wx_util.js.

Units: positions in view px (env.W x env.H, the web's CSS px), time in s, wind in m/s (env.wind, gusty).  Depth:
something z metres from the camera moves PXM(env, z) = 1.5 * H / z px per metre (FOCAL = 1.5).
  clamp, smooth, rgba          numbers / QColor helpers (smooth_v: numpy smoothstep)
  budget(env, base, max)       particle budget scaled by the view area and env.quality (as the JS)
  lights(env, min_i, n)        burst lights [(x, y, r, I, col)] (env.lights are already view px)
  light_at, sky_tone           light falling on a point; per-scene fog / haze / cloud colours
  hash_v, noise1_v             value noise with a per-element seed (vectorised over many particles)
  fbm_p                        periodic fbm (tiles horizontally), vectorised; fog and cloud textures
  premul_image                 (h, w, 4) float RGBA 0..255 -> premultiplied QImage
  scene_geometry(env)          skyline tops, silhouette top edges (snow) and open-sky masks from the scenery's
                               material map and front layer, cached per scenery and size
  draw_scrolled                a horizontally periodic texture scrolled by a fractional offset
The geometry and the textures need QImage (no QApplication); update() of the plug-ins needs no Qt at all, except
lightning's skyline lookup (scene_geometry), which works headless.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter

from effects.scenery_noise import _imul, _u32, hash as nhash

M32 = 0xFFFFFFFF
_U = np.uint64


def jround(v: float) -> int:
    return int(math.floor(v + 0.5))


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def smooth(a, b, v):
    t = clamp((v - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def smooth_v(a, b, v):
    t = np.clip((v - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rgba(c, a: float) -> QColor:
    """CSS rgba(c|0, a) as a QColor."""
    f = lambda v: max(0, min(255, int(v)))   # noqa: E731
    return QColor(f(c[0]), f(c[1]), f(c[2]), max(0, min(255, jround(a * 255))))


def PXM(env, z: float) -> float:  # noqa: N802 (same name as the JS)
    return 1.5 * env.H / z


def budget(env, base: float, mx: float | None = None) -> int:
    mx = base * 2 if mx is None else mx
    area = env.W * env.H / (1280 * 800)
    q = env.quality if env.quality is not None else 1.0
    return max(4, min(mx, jround(base * clamp(area, 0.2, 2) * clamp(q, 0.2, 1))))


def lights(env, min_i: float = 0.0, n: int = 8) -> list:
    """The burst lights brighter than min_i, strongest first (env.lights are sorted already)."""
    return [L for L in (env.lights or []) if L[3] > min_i][:n]


def light_at(lts, x, y, rgb, spread=1.0) -> float:
    r = g = b = 0.0
    for Lx, Ly, Lr, LI, col in lts:
        s = Lr * spread
        dx, dy = (x - Lx) / s, (y - Ly) / s
        q = 1 + dx * dx + dy * dy
        f = LI / (q * q) / 255
        r += col[0] * f
        g += col[1] * f
        b += col[2] * f
    rgb[0], rgb[1], rgb[2] = r, g, b
    return r + g + b


def sky_tone(env) -> dict:
    n = getattr(env.scenery, "name", None)
    if n == "Cityscape":
        return dict(fog=(74, 64, 62), haze=(70, 58, 52), under=(96, 66, 48), top=(30, 30, 38))
    if n == "Beach":
        return dict(fog=(54, 58, 74), haze=(46, 50, 66), under=(56, 54, 72), top=(26, 28, 40))
    return dict(fog=(60, 66, 80), haze=(44, 50, 64), under=(52, 56, 74), top=(24, 27, 38))


# --- noise --------------------------------------------------------------------------------------------------
def hash_v(seeds, x, y=0):
    """fw_noise.js hash with an array of seeds (uint32 values) and array coordinates."""
    s = (np.asarray(seeds, dtype=np.int64) & M32).astype(_U)
    xi, yi = _u32(np.floor(x)), _u32(np.floor(y))
    h = s ^ _imul(xi, 374761393) ^ _imul(yi, 668265263)
    h = _imul(h ^ (h >> _U(13)), 1274126177)
    return (h ^ (h >> _U(16))).astype(np.float64) / 4294967296.0


def noise1_v(seeds, x):
    x = np.asarray(x, dtype=np.float64)
    i = np.floor(x)
    f = x - i
    a = hash_v(seeds, i)
    return a + (hash_v(seeds, i + 1) - a) * (f * f * (3 - 2 * f))


def _noise_p(seed, x, y, px, py):
    i, j = np.floor(x), np.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    i0 = np.mod(np.mod(i, px) + px, px)
    i1 = np.mod(i0 + 1, px)
    j0 = np.mod(np.mod(j, py) + py, py)
    j1 = np.mod(j0 + 1, py)
    a, b = nhash(seed, i0, j0), nhash(seed, i1, j0)
    c, d = nhash(seed, i0, j1), nhash(seed, i1, j1)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy


def fbm_p(seed, x, y, px, py, oct=5, gain=0.5):
    """Periodic fbm (period px, py lattice cells at the first octave; octaves double the frequency)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    s, a, n, f = 0.0, 1.0, 0.0, 1.0
    for o in range(oct):
        s = s + a * _noise_p(seed + o * 131, x * f, y * f, px * f, py * f)
        n += a
        a *= gain
        f *= 2
    return s / n


# --- images -------------------------------------------------------------------------------------------------
def premul_image(rgba_f: np.ndarray) -> QImage:
    """(h, w, 4) RGBA (0..255, straight alpha) -> ARGB32_Premultiplied QImage."""
    h, w = rgba_f.shape[:2]
    a = np.clip(rgba_f[..., 3], 0, 255)
    out = np.empty((h, w, 4), np.uint8)
    k = a / 255.0
    out[..., 0] = np.clip(np.rint(rgba_f[..., 2] * k), 0, 255)     # B G R A byte order
    out[..., 1] = np.clip(np.rint(rgba_f[..., 1] * k), 0, 255)
    out[..., 2] = np.clip(np.rint(rgba_f[..., 0] * k), 0, 255)
    out[..., 3] = np.rint(a)
    return QImage(out.tobytes(), w, h, w * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()


def _array(img: QImage, fmt) -> np.ndarray:
    img = img.convertToFormat(fmt)
    ptr = img.constBits()
    ptr.setsize(img.sizeInBytes())
    a = np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)[:, :img.width()]
    return a.copy()


def draw_scrolled(p: QPainter, tex: QImage, off: float, dy: float, w: float) -> None:
    """Draw tex repeated along x, shifted by `off` px (fractional, any sign) and `dy` down, covering 0..w."""
    tw = tex.width()
    x = off % tw - tw
    while x < w:
        p.drawImage(QPointF(x, dy), tex)
        x += tw


# --- scene geometry ------------------------------------------------------------------------------------------
_GEO: dict = {}


class _Geometry:
    def __init__(self, W, H, tops, edges, sky):
        self.W, self.H, self.tops, self.edges, self._sky = W, H, tops, edges, sky
        self._masks = {}

    def mask(self, s: int = 4):
        """QImage of ceil(W/s) x ceil(H/s) whose alpha is the open sky not hidden by the front (None: no scenery)."""
        if self._sky is None:
            return None
        if s not in self._masks:
            W, H = self.W, self.H
            w, h = -(-W // s), -(-H // s)
            v = np.full((h * s, w * s), np.nan)
            v[:H, :W] = self._sky
            sub = v[::2, ::2]                                 # the JS samples every 2nd px of each s x s cell
            g = max(1, s // 2)
            blk = sub.reshape(h, g, w, g)
            a = np.nanmean(blk, axis=(1, 3))
            a = np.nan_to_num(a)
            arr = np.zeros((h, w, 4), np.float64)
            arr[..., :3] = 255
            arr[..., 3] = np.rint(255 * a)
            self._masks[s] = premul_image(arr)
        return self._masks[s]


def scene_geometry(env) -> _Geometry:
    """tops[x] (first solid y per view column), edges [(x, y, slope, over_water)] and mask(s), as fw_wx_util.js."""
    S, W, H = env.scenery, max(1, jround(env.W)), max(1, jround(env.H))
    if S is None or getattr(S, "mat", None) is None:
        return _Geometry(W, H, np.full(W, float(H)), [], None)
    key = (id(S), W, H)
    hit = _GEO.get(key)
    if hit is not None and hit[0] is S:
        return hit[1]
    smooth_t = Qt.TransformationMode.SmoothTransformation
    ign = Qt.AspectRatioMode.IgnoreAspectRatio
    m = _array(S.mat.scaled(W, H, ign, smooth_t), QImage.Format.Format_RGB32).astype(np.int32)   # B G R A
    f = _array(S.front.scaled(W, H, ign, smooth_t), QImage.Format.Format_ARGB32)[..., 3].astype(np.int32)
    mr, mg, mb = m[..., 2], m[..., 1], m[..., 0]
    solid = (f > 128) | ((mr > 12) & (mg < 128) & (mb < 128))
    water = (f <= 128) & (mg >= 128)
    rising = np.zeros_like(solid)
    rising[1:] = solid[1:] & ~solid[:-1]
    tops = np.full(W, float(H))
    first = np.where(rising.any(axis=0), rising.argmax(axis=0), H)
    wat = ~solid & water
    firstw = np.where(wat.any(axis=0), wat.argmax(axis=0), H)
    tops = np.minimum(first, firstw).astype(np.float64)
    cols = [[] for _ in range(W)]
    ys, xs = np.nonzero(rising.T)                             # column-major: per column in y order
    for cx, y in zip(ys.tolist(), xs.tolist()):
        lst = cols[cx]
        if len(lst) < 8:
            lst.append(-y if water[y - 1, cx] else y)
    edges = []
    for cx in range(W):
        for v in cols[cx]:
            y = abs(v)
            d = 99
            for nb in (cols[cx - 1] if cx > 0 else None, cols[cx + 1] if cx + 1 < W else None):
                if nb:
                    for u in nb:
                        d = min(d, abs(abs(u) - y))
            edges.append((cx, y, d, v < 0))
    sky = (mb / 255.0) * (1 - f / 255.0)
    geo = _Geometry(W, H, tops, edges, sky)
    if len(_GEO) > 8:
        _GEO.clear()
    _GEO[key] = (S, geo)
    return geo
