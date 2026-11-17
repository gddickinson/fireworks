"""Realistic lightning (weather plug-in part, effects/fx_base.py) and the two weathers that use it: a port of
web/static/fw_wx_lightning.js.
  Storm ("Thunderstorm") - dark low cloud deck + heavy rain + frequent strikes
  Lightning              - light broken cloud + rare strikes
A strike is a cloud-to-ground bolt (a jagged channel from the cloud base to the skyline/ground with branches) or a
flash inside the cloud.  Its brightness is a few return strokes, each a sharp spike decaying in ~50 ms, so the bolt
flickers.  The flash lights the cloud deck (shared["flash"] -> effects/wx_clouds.py), brightens the rain and the
open sky behind the silhouettes (sky pass, masked by the scenery).  With env.reduced there are no strikes at all.

update() (as the JS): t += dt; when t >= next: a new strike (seeded), next = t + uniform(lo, hi);
brightness b(t) = sum over strokes k of amp_k exp(-(t - t_k) / 0.05) for t >= t_k; shared flash = max over live
strikes; a strike ends 0.4 s after its last stroke.  Bolt path: n steps from the cloud base towards the top of the
scenery at x1, each step down (y1 - y0) / n * (0.6..1.4) and sideways towards the target plus a seeded jitter;
branches leave with probability 0.14 per step and walk 5..16 shorter steps at 0.35..1.1 rad off the vertical;
every segment then gets a midpoint shifted sideways by (-0.25..0.25) x its length.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QImage, QPainter, QPainterPath, QPen, QRadialGradient

from effects.fx_base import combine, register_weather
from effects.scenery_noise import prng
from effects.wx_clouds import make_clouds
from effects.wx_rain import make_rain
from effects.wx_util import clamp, jround, rgba, scene_geometry

FMT = QImage.Format.Format_ARGB32_Premultiplied


class Lightning:
    """interval [lo, hi] s, ground (probability of a bolt vs a cloud flash), deck (cloud base, fraction of H)."""

    def __init__(self, env, interval=(6, 16), ground=0.6, deck=0.3, shared: dict | None = None):
        self.o = dict(interval=tuple(interval), ground=ground, deck=deck)
        self.shared = shared if shared is not None else {}
        self.R = prng((env.seed ^ 0x1B0175) & 0xFFFFFFFF)
        self.strikes: list = []
        self.W, self.H = env.W, env.H
        self.t = 0.0
        self.next = 2 + self.R() * self.o["interval"][0]
        self.shared["flash"] = 0.0
        self.fc = None

    # --- geometry (seeded) -----------------------------------------------------------------------------------
    def _walk(self, x, y, ty, tx, n, step, spread, out):
        R, pts, i = self.R, [(x, y)], 0
        while i < n and y < ty:
            dy = step * (0.6 + R() * 0.8)
            pull = 0 if tx is None else (tx - x) / max(1, n - i)
            x += pull + (R() - 0.5) * 2 * spread * dy
            y += dy
            pts.append((x, y))
            if out is not None and R() < 0.14 and i < n - 3:  # a branch, sometimes with a sub-branch
                side = -1 if R() < 0.5 else 1
                ang = 0.35 + R() * 0.75
                m = 5 + int(R() * 12)
                br = self._branch(x, y, side, ang, m, step * 0.7)
                out.append(br)
                if R() < 0.3 and len(br) > 4:
                    bx, by = br[2]
                    s2 = side * (1 if R() < 0.5 else -1)
                    out.append(self._branch(bx, by, s2, ang, 4 + int(R() * 6), step * 0.5))
            i += 1
        return self._refine(pts)

    def _refine(self, pts):
        R, out = self.R, [pts[0]]
        for i in range(1, len(pts)):
            (ax, ay), (bx, by) = pts[i - 1], pts[i]
            j = (R() - 0.5) * 0.5
            out.append(((ax + bx) / 2 - (by - ay) * j, (ay + by) / 2 + (bx - ax) * j))
            out.append(pts[i])
        return out

    def _branch(self, x, y, side, ang, n, step):
        R, pts = self.R, [(x, y)]
        for _ in range(n):
            a = ang + (R() - 0.5) * 0.9
            ln = step * (0.6 + R() * 0.8)
            x += side * math.sin(a) * ln
            y += math.cos(a) * ln
            pts.append((x, y))
        return self._refine(pts)

    def _strike(self, env):
        R, W, H, o = self.R, self.W, self.H, self.o
        x0 = W * (0.08 + R() * 0.84)
        y0 = H * o["deck"] * (0.55 + R() * 0.4)
        strokes, k, ts = [], 1 + int(R() * 3.2), self.t
        for i in range(k):
            strokes.append([ts, 1.0 if i == 0 else 0.45 + R() * 0.55])
            ts += 0.04 + R() * 0.12
        s = dict(t0=self.t, strokes=strokes, end=ts + 0.4, x=x0, y=y0, bolt=None, branches=[], b=0.0)
        if R() < o["ground"]:
            x1 = clamp(x0 + (R() - 0.5) * W * 0.25, 2, W - 2)
            tops = scene_geometry(env).tops
            idx = jround(x1 * (len(tops) - 1) / max(1, W))
            y1 = min(H, float(tops[idx]) if 0 <= idx < len(tops) else H) + 1
            n = 26 + int(R() * 18)
            s["bolt"] = self._walk(x0, y0, y1, x1, n, (y1 - y0) / n, 0.55, s["branches"])
        else:
            for st in strokes:                                # a flash inside the cloud: dimmer, no channel
                st[1] *= 0.55
        self.strikes.append(s)

    def _bright(self, s) -> float:
        t = self.t
        return sum(a * math.exp(-(t - tk) / 0.05) for tk, a in s["strokes"] if t >= tk)

    # --- plug-in ---------------------------------------------------------------------------------------------
    def resize(self, env):
        self.W, self.H = env.W, env.H
        self.strikes.clear()
        self.fc = None

    def update(self, dt, env):
        if env.W != self.W or env.H != self.H:
            self.resize(env)
        self.t += dt
        sh = self.shared
        if env.reduced:
            self.strikes.clear()
            sh["flash"] = 0.0
            return
        if self.t >= self.next:
            self._strike(env)
            lo, hi = self.o["interval"]
            self.next = self.t + lo + self.R() * (hi - lo)
        f = 0.0
        for s in self.strikes:
            b = s["b"] = self._bright(s)
            if b > f:
                f = b
                sh["flashX"], sh["flashY"] = s["x"], s["y"]
        self.strikes = [s for s in self.strikes if self.t <= s["end"]]
        sh["flash"] = f

    def stats(self):
        return dict(count=len(self.strikes), flash=self.shared.get("flash", 0.0),
                    bolts=sum(1 for s in self.strikes if s["bolt"]))

    def state(self):
        return dict(t=self.t, next=self.next, strikes=[(s["t0"], s["x"], s["y"], s["bolt"]) for s in self.strikes])

    def draw_sky(self, p, env):
        if not self.strikes:
            return
        W, H, sh = self.W, self.H, self.shared
        sc, f = H / 800, clamp(sh.get("flash", 0.0), 0, 1.5)
        if f > 0.02:                                          # the open sky lights up behind the silhouettes
            w, h = math.ceil(W / 4), math.ceil(H / 4)
            if self.fc is None or (self.fc.width(), self.fc.height()) != (w, h):
                self.fc = QImage(w, h, FMT)
            self.fc.fill(0)
            x = QPainter(self.fc)
            fx, fy = sh.get("flashX", W / 2) / 4, sh.get("flashY", H * 0.2) / 4
            g = QRadialGradient(QPointF(fx, fy), w * 0.9)
            g.setColorAt(0, rgba((190, 198, 240), min(0.5, 0.38 * f)))
            g.setColorAt(1, rgba((120, 130, 180), min(0.2, 0.12 * f)))
            x.fillRect(QRectF(0, 0, w, h), QBrush(g))
            mask = scene_geometry(env).mask(4)
            if mask is not None:
                x.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                x.drawImage(0, 0, mask)
            x.end()
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(QRectF(0, 0, w * 4, h * 4), self.fc)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for s in self.strikes:                                # glow, bluish body, white-hot core; thinner branches
            if not s["bolt"]:
                continue
            b = clamp(s["b"] * 1.4, 0, 1)
            after = clamp(1 - (self.t - s["t0"]) / (s["end"] - s["t0"]), 0, 1) * 0.25
            v = max(b, after)
            if v < 0.02:
                continue
            bolt = _poly(s["bolt"])
            branches = QPainterPath()
            for br in s["branches"]:
                branches.addPath(_poly(br))
            for width, col, a in ((12, (140, 130, 255), 0.1), (4.5, (180, 190, 255), 0.35), (1.6, (255, 255, 255), 1)):
                p.setPen(_pen(rgba(col, a * v), width * sc))
                p.drawPath(bolt)
                p.setPen(_pen(rgba(col, a * v * 0.7), width * sc * 0.5))
                p.drawPath(branches)

    def draw_over(self, p, env):                              # the whole scene catches a little of the flash
        f = clamp(self.shared.get("flash", 0.0) or 0.0, 0, 1.5)
        if f > 0.02:
            p.fillRect(QRectF(0, 0, self.W, self.H), rgba((170, 180, 230), 0.05 * f))


def _pen(col, width) -> QPen:
    return QPen(col, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def _poly(pts) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(*pts[0])
    for x, y in pts[1:]:
        path.lineTo(x, y)
    return path


def make_lightning(env, shared: dict | None = None, **opts) -> Lightning:
    return Lightning(env, shared=shared, **opts)


def make_storm(env):
    shared = {"flash": 0.0}
    return combine([make_clouds(env, shared, cover=0.92, base=0.36, dark=0.85, over=0.4),
                    make_lightning(env, shared, interval=(3, 9), ground=0.65, deck=0.36),
                    make_rain(env, heavy=1.8, shared=shared)])


def make_lightning_weather(env):
    shared = {"flash": 0.0}
    return combine([make_clouds(env, shared, cover=0.42, base=0.3, dark=0.5, over=0.25),
                    make_lightning(env, shared, interval=(5, 13), ground=0.75, deck=0.3)])


register_weather("Storm", "Thunderstorm", make_storm)
register_weather("Lightning", "Lightning", make_lightning_weather)
