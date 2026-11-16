"""Seeded value noise for the realistic scenery: a numpy port of web/static/fw_noise.js (no Qt).

The functions reproduce the JavaScript numbers (Math.imul and `>>> 0` are emulated with uint64 arithmetic masked
to 32 bits), so the desktop scenery (effects/scenery.py) is generated from the same noise and the same prng draws
as the web scenery.  Every noise function accepts scalars or numpy arrays for its coordinates (vectorised); the
seeds are plain ints.

  hash(seed, x, y=0)          integer hash of a lattice point -> [0, 1)
  noise1 / noise2             smoothly interpolated value noise
  fbm1 / fbm2                 fractal sums of octaves
  ridged1                     ridged multifractal (sharp crests), 0..1
  prng(seed)                  mulberry32 generator: call it for the next uniform number in [0, 1)
"""
from __future__ import annotations

import numpy as np

M32 = 0xFFFFFFFF
_U = np.uint64


def _u32(v):
    """Integer value(s) as uint64 holding the low 32 bits (JS `x | 0` / `>>> 0` of an integer)."""
    return (np.asarray(v, dtype=np.int64) & M32).astype(_U)


def _imul(a, b: int):
    """Math.imul(a, b) as an unsigned 32-bit value (a: uint64 array < 2^32, b: python int)."""
    return (a * _U(b & M32)) & _U(M32)


def hash(seed: int, x, y=0):  # noqa: A001 (same name as the JS function)
    xi, yi = _u32(np.floor(x)), _u32(np.floor(y))
    h = _U(seed & M32) ^ _imul(xi, 374761393) ^ _imul(yi, 668265263)
    h = _imul(h ^ (h >> _U(13)), 1274126177)
    out = (h ^ (h >> _U(16))).astype(np.float64) / 4294967296.0
    return out if out.ndim else float(out)


def _fade(t):
    return t * t * (3 - 2 * t)


def noise1(seed: int, x):
    x = np.asarray(x, dtype=np.float64)
    i = np.floor(x)
    f = x - i
    a = hash(seed, i)
    return a + (hash(seed, i + 1) - a) * _fade(f)


def noise2(seed: int, x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    i, j = np.floor(x), np.floor(y)
    fx, fy = _fade(x - i), _fade(y - j)
    a, b = hash(seed, i, j), hash(seed, i + 1, j)
    c, d = hash(seed, i, j + 1), hash(seed, i + 1, j + 1)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy


def fbm1(seed: int, x, oct: int = 5, gain: float = 0.5):
    x = np.asarray(x, dtype=np.float64)
    s, a, f, n = 0.0, 1.0, 1.0, 0.0
    for o in range(oct):
        s = s + a * noise1(seed + o * 101, x * f)
        n += a
        a *= gain
        f *= 2.03
    return s / n


def fbm2(seed: int, x, y, oct: int = 5, gain: float = 0.5):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    s, a, f, n = 0.0, 1.0, 1.0, 0.0
    for o in range(oct):
        s = s + a * noise2(seed + o * 131, x * f, y * f)
        n += a
        a *= gain
        f *= 2.01
    return s / n


def ridged1(seed: int, x, oct: int = 6):
    x = np.asarray(x, dtype=np.float64)
    s, a, f, w, n = 0.0, 0.5, 1.0, 1.0, 0.0
    for o in range(oct):
        v = 1 - np.abs(noise1(seed + o * 71, x * f) * 2 - 1)
        v = v * (v * w)
        w = np.minimum(1, v * 2)
        s = s + v * a
        n += a
        a *= 0.5
        f *= 2.1
    return s / n


class prng:  # noqa: N801 (mirrors the JS factory `prng(seed)`)
    """mulberry32, as fw_noise.js: `rnd = prng(7); rnd()` gives the same sequence as in the browser."""
    __slots__ = ("a",)

    def __init__(self, seed: int):
        self.a = int(seed) & M32

    def __call__(self) -> float:
        a = self.a = (self.a + 0x6D2B79F5) & M32
        t = ((a ^ (a >> 15)) * (1 | a)) & M32
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & M32)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296.0
