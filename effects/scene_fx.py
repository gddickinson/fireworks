"""Animated objects of the realistic scenes (always on, effects/fx_base.register_scene_fx): a QPainter port of
web/static/fw_scene_fx.js (same seeds and random order).

Bobbing boats and a sweeping lighthouse beam in the Harbour, chimney smoke drifting with the wind in the Snowy
Village, blinking aviation lights on towers and bridge pylons, searchlights over the Waterfront, turning wind
turbines in the Countryside.  Positions come from the scenery painter (S.boats / S.lighthouse / S.chimneys /
S.beacons / S.turbines, scenery px; drawn in view px = scenery px * env.k).  update() is pure seeded arithmetic
(state() for tests); sprites are made lazily when drawing.  The boat sprite painter `paint_boat` follows
fw_scenery_houses.js boat().
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

from effects.fx_base import combine, register_scene_fx
from effects.fx_masks import FMT, horizon_px, is_dusk, masked, soft_sprite
from effects.scenery_noise import hash, prng

M32 = 0xFFFFFFFF
DEG = 180 / math.pi


def _rgb(c, a: float = 1.0) -> QColor:
    f = lambda v: max(0, min(255, int(v)))   # noqa: E731
    return QColor(f(c[0]), f(c[1]), f(c[2]), max(0, min(255, int(round(a * 255)))))


def _glow(p, x, y, r, col, a=0.6, core=0.12):
    g = QRadialGradient(QPointF(x, y), r)
    g.setColorAt(0, _rgb(col, a))
    g.setColorAt(core, _rgb(col, a * 0.45))
    g.setColorAt(1, _rgb(col, 0))
    p.fillRect(QRectF(x - r, y - r, 2 * r, 2 * r), g)


def paint_boat(p: QPainter, x, y, ln, sc, rnd, sail=True, colour=(12, 13, 18), lights=True):
    """Boat (side view, facing right) on the waterline y: hull, gunwale, cabin, mast and stays (sailing), riding
    lights.  Returns the masthead light's offset (dx, dy)."""
    h = ln * 0.16
    p.setPen(Qt.PenStyle.NoPen)
    hull = QPainterPath()
    hull.moveTo(x - ln / 2, y - h)
    hull.lineTo(x + ln / 2 + ln * 0.06, y - h * 1.15)
    hull.quadTo(x + ln * 0.42, y + h * 0.2, x + ln * 0.25, y + h * 0.25)
    hull.lineTo(x - ln * 0.42, y + h * 0.2)
    hull.closeSubpath()
    p.fillPath(hull, _rgb(colour))
    p.fillRect(QRectF(x - ln / 2, y - h * 1.05, ln * 1.04, h * 0.18), _rgb([min(255, v * 1.8 + 20) for v in colour]))
    p.fillRect(QRectF(x - ln * 0.2, y - h * 1.9, ln * 0.32, h * 0.95), _rgb([v * 1.4 for v in colour]))
    top = (0.0, -h * 1.9)
    if sail:
        mh = ln * (0.9 + rnd() * 0.4)
        mast = _rgb([v * 1.8 for v in colour])
        p.fillRect(QRectF(x - 0.5 * sc, y - h - mh, 1 * sc, mh), mast)
        p.setPen(QPen(mast, 0.5 * sc))
        p.drawLine(QPointF(x, y - h - mh), QPointF(x + ln * 0.5, y - h))
        p.drawLine(QPointF(x, y - h - mh), QPointF(x - ln * 0.48, y - h))
        p.setPen(Qt.PenStyle.NoPen)
        top = (0.0, -h - mh)
    if lights:
        p.setBrush(QColor(255, 245, 220))
        p.drawEllipse(QPointF(x + top[0], y + top[1]), 1.1 * sc, 1.1 * sc)
        _glow(p, x + top[0], y + top[1], 6 * sc, (255, 240, 210), 0.35)
        cab = _rgb((255, 200, 130), 0.85)
        p.fillRect(QRectF(x - ln * 0.15, y - h * 1.6, ln * 0.06, h * 0.4), cab)
        p.fillRect(QRectF(x, y - h * 1.6, ln * 0.06, h * 0.4), cab)
    return top


# ---- Boats -------------------------------------------------------------------------------------------------
class Boats:
    """Pre-rendered sprites that bob and roll on the swell, with a wobbling reflection and light streaks."""

    def __init__(self, env):
        self.list = []
        for x, y, ln, seed in getattr(env.scenery, "boats", None) or []:
            r = prng(seed)
            self.list.append({"x": x, "y": y, "len": ln, "seed": seed, "ph": r() * 6.28, "w": 0.9 + r() * 0.6,
                              "roll": 0.025 + r() * 0.03, "sail": r() < 0.5, "bob": 0.0, "ang": 0.0, "top": (0, 0)})
        self.t = 0.0
        self.sprites = None
        self._k = None

    def resize(self, env):
        self.sprites = None

    def update(self, dt, env):
        self.t += dt
        amp = (0.5 if env.reduced else 1.0) * (1 + abs(env.wind or 0) * 0.1)
        for B in self.list:
            B["bob"] = math.sin(self.t * B["w"] + B["ph"]) * 1.6 * amp            # view px
            B["ang"] = math.sin(self.t * B["w"] * 0.8 + B["ph"] * 1.7) * B["roll"] * amp

    def _make(self, env):
        self._k = k = env.k
        sc, col = env.H / 800, (30, 34, 50) if is_dusk(env) else (20, 22, 30)
        self.sprites = []
        for B in self.list:
            L = B["len"] * k
            img = QImage(max(1, math.ceil(L * 1.5)), max(1, math.ceil(L * 1.9)), FMT)
            img.fill(0)
            q = QPainter(img)
            q.setRenderHint(QPainter.RenderHint.Antialiasing)
            B["top"] = paint_boat(q, img.width() / 2, img.height() * 0.85, L, sc, prng(B["seed"] + 1),
                                  sail=B["sail"], colour=col)
            q.end()
            self.sprites.append(img)

    def draw_sky(self, p, env):
        if not self.list:
            return
        if self.sprites is None or self._k != env.k:
            self._make(env)
        k = self._k
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        for B, sp in zip(self.list, self.sprites):
            x, y = B["x"] * k, B["y"] * k + B["bob"]
            ox, oy = sp.width() / 2, sp.height() * 0.85
            p.save()
            p.translate(x, y)
            p.rotate(B["ang"] * DEG)
            p.scale(1, -0.8)
            p.setOpacity(0.28)
            p.drawImage(QPointF(-ox, -oy), sp)
            p.restore()
            lx = x + B["top"][0] - B["top"][1] * math.sin(B["ang"]) * 0.8          # masthead light streaks
            ln = B["len"] * k * 1.2
            for j in range(7):
                d = (j + 1) / 8
                jit = (hash(B["seed"], j, math.floor(self.t * 5)) - 0.5) * 4 * (1 + d * 3)
                p.setOpacity(0.35 * (1 - d))
                p.fillRect(QRectF(lx + jit - (1 + 4 * d), y + 3 + d * ln, 2 + 8 * d, 1), QColor(255, 240, 210))
            p.setOpacity(1.0)
            p.save()
            p.translate(x, y)
            p.rotate(B["ang"] * DEG)
            p.drawImage(QPointF(-ox, -oy), sp)
            p.restore()

    def state(self):
        return {"t": self.t, "boats": [(B["bob"], B["ang"]) for B in self.list]}


# ---- Lighthouse --------------------------------------------------------------------------------------------
class Lighthouse:
    """A beam sweeping round; a flash when it points at the viewer."""

    def __init__(self, env):
        self.t = 0.0
        self.a = 0.0

    def update(self, dt, env):
        self.t += dt
        self.a = (self.a + dt * (0.35 if env.reduced else 0.9)) % 6.2832

    def draw_sky(self, p, env):
        L = getattr(env.scenery, "lighthouse", None)
        if not L:
            return
        k = env.k
        x, y, s = L[0] * k, L[1] * k, env.H / 800
        ca, toward = math.cos(self.a), max(0.0, math.sin(self.a))
        ln = env.W * 0.45 * abs(ca) + 20 * s
        ex, w = x + math.copysign(1, ca) * ln, 6 * s + ln * 0.06
        g = QLinearGradient(x, y, ex, y)
        g.setColorAt(0, _rgb((255, 245, 220), 0.22 + 0.2 * toward))
        g.setColorAt(1, _rgb((255, 245, 220), 0))
        path = QPainterPath()
        path.moveTo(x, y - 1.5 * s)
        path.lineTo(ex, y - w - 4 * s)
        path.lineTo(ex, y + w - 4 * s)
        path.lineTo(x, y + 1.5 * s)
        path.closeSubpath()
        p.fillPath(path, g)
        f = toward ** 12
        r = (8 + 40 * f) * s
        p.setOpacity(0.5 + 0.5 * f)
        p.drawImage(QRectF(x - r, y - r, 2 * r, 2 * r), soft_sprite((255, 245, 220), 0.1))
        p.setOpacity(1.0)

    def state(self):
        return {"t": self.t, "a": self.a}


# ---- Chimney smoke -----------------------------------------------------------------------------------------
class Smoke:
    """Puffs rising, slowing, spreading and drifting downwind, fading out."""
    EVERY, LIFE = 0.32, 6.0

    def __init__(self, env):
        self.rnd = prng((env.seed ^ 0x5307E) & M32)
        self.chimneys = list(getattr(env.scenery, "chimneys", None) or [])
        self.t, self.next, self.list = 0.0, 0.0, []

    def update(self, dt, env):
        self.t += dt
        k, s = env.k, env.H / 800
        wind, rnd = (env.wind or 0) * 5 * s, self.rnd
        while self.t >= self.next:
            self.next += self.EVERY
            for x, y, w in self.chimneys:
                self.list.append({"x": x * k + (rnd() - 0.5) * w * k * 0.4, "y": y * k, "r": max(1.0, w * k * 0.45),
                                  "age": 0.0, "vy": -(10 + rnd() * 6) * s, "ph": rnd() * 6.28})
        for q in self.list:
            q["age"] += dt
            f = min(1.0, q["age"] / 3)
            q["y"] += q["vy"] * (1 - 0.6 * f) * dt
            q["x"] += (wind * f + math.sin(q["age"] * 0.8 + q["ph"]) * 2 * s) * dt
            q["r"] += (2.2 + 1.5 * f) * s * dt
        self.list = [q for q in self.list if q["age"] < self.LIFE]

    def draw_sky(self, p, env):
        sp = soft_sprite((150, 158, 182) if is_dusk(env) else (118, 124, 142), 0.25)
        for q in self.list:
            a = q["age"] / self.LIFE
            p.setOpacity(max(0.0, 0.22 * min(1.0, q["age"] * 2) * (1 - a) * (1 - a)))
            r = q["r"]
            p.drawImage(QRectF(q["x"] - r * 1.6, q["y"] - r * 1.6, r * 3.2, r * 3.2), sp)
        p.setOpacity(1.0)

    def state(self):
        return {"t": self.t, "n": len(self.list), "list": [(q["x"], q["y"], q["r"]) for q in self.list]}


# ---- Aviation warning lights -------------------------------------------------------------------------------
class Beacons:
    """Red flashes, nearly in step across a skyline (towers are often synchronised)."""

    def __init__(self, env):
        self.beacons = list(getattr(env.scenery, "beacons", None) or [])
        self.ph = [hash(env.seed & 0xFFFF, i) * 0.25 for i in range(len(self.beacons))]
        self.t = 0.0

    def on(self, i) -> bool:
        return ((self.t + self.ph[i]) % 1.6) < 0.35

    def update(self, dt, env=None):
        self.t += dt

    def draw_sky(self, p, env):
        k, sp = env.k, soft_sprite((255, 50, 35), 0.05)
        for i, (x, y, r) in enumerate(self.beacons):
            if not self.on(i):
                continue
            R = max(3.0, r * k * 4.5)
            p.setOpacity(0.7)
            p.drawImage(QRectF(x * k - R, y * k - R, 2 * R, 2 * R), sp)
            p.setOpacity(1.0)
            p.fillRect(QRectF(x * k - 0.8, y * k - 0.8, 1.6, 1.6), QColor(255, 90, 70))

    def state(self):
        return {"t": self.t, "on": [self.on(i) for i in range(len(self.beacons))]}


# ---- Searchlights ------------------------------------------------------------------------------------------
class Searchlights:
    """Two beams sweeping slowly above the skyline (cut to the open sky)."""

    def __init__(self, env):
        rnd = prng((env.seed ^ 0x5EA7C4) & M32)
        self.beams = []
        for i in range(2):
            b = {"x": 0.25 + i * 0.45 + rnd() * 0.1}
            b["ph"] = rnd() * 6.28
            b["w"] = 0.13 + rnd() * 0.08
            b["a"] = 0.0
            self.beams.append(b)
        self.t = 0.0

    def update(self, dt, env):
        self.t += dt * (0.4 if env.reduced else 1.0)
        for B in self.beams:
            B["a"] = math.sin(self.t * B["w"] + B["ph"]) * 0.38

    def draw_sky(self, p, env):
        hz = horizon_px(env)
        L, kk = hz * 1.1, 0.5 if is_dusk(env) else 1.0

        def draw(l):
            for B in self.beams:
                x, a = B["x"] * env.W, B["a"]
                ex, ey, w = x + math.sin(a) * L, hz - math.cos(a) * L, L * 0.022
                g = QLinearGradient(x, hz, ex, ey)
                g.setColorAt(0, _rgb((210, 225, 255), 0.09 * kk))
                g.setColorAt(0.5, _rgb((210, 225, 255), 0.04 * kk))
                g.setColorAt(1, _rgb((210, 225, 255), 0))
                path = QPainterPath()
                path.moveTo(x - 2, hz)
                path.lineTo(ex - w * math.cos(a), ey - w * math.sin(a))
                path.lineTo(ex + w * math.cos(a), ey + w * math.sin(a))
                path.lineTo(x + 2, hz)
                path.closeSubpath()
                l.fillPath(path, g)
        masked(p, env, "sky", draw)

    def state(self):
        return {"t": self.t, "a": [B["a"] for B in self.beams]}


# ---- Wind turbines -----------------------------------------------------------------------------------------
class Turbines:
    """Three blades turning (faster with the wind), synchronised red lights on the nacelles."""

    def __init__(self, env):
        self.turbines = list(getattr(env.scenery, "turbines", None) or [])
        self.t = 0.0
        self.rot = [hash(env.seed & 0xFFFF, i, 9) * 6.28 for i in range(len(self.turbines))]

    def update(self, dt, env):
        self.t += dt
        w = (0.6 + 0.12 * abs(env.wind or 0)) * (0.5 if env.reduced else 1.0)
        self.rot = [(a + dt * w * (0.85 + 0.3 * hash(7, i))) % 6.2832 for i, a in enumerate(self.rot)]

    def draw_sky(self, p, env):
        k, blink = env.k, (self.t % 2) < 0.6
        sp = soft_sprite((255, 50, 35), 0.12)
        col = QColor(70, 78, 104) if is_dusk(env) else QColor(46, 50, 66)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, (x, y, ln) in enumerate(self.turbines):
            X, Y, L = x * k, y * k, ln * k
            path = QPainterPath()
            for b in range(3):
                a = self.rot[i] + b * 2.0944
                ca, sa, wd = math.cos(a), math.sin(a), max(0.8, L * 0.04)
                path.moveTo(X - sa * wd, Y + ca * wd)
                path.lineTo(X + ca * L, Y + sa * L)
                path.lineTo(X + sa * wd * 0.6, Y - ca * wd * 0.6)
                path.closeSubpath()
            p.fillPath(path, col)
            if blink:
                R = max(3.0, L * 0.14)
                p.setOpacity(0.9)
                p.drawImage(QRectF(X - R, Y - R - 1, 2 * R, 2 * R), sp)
                p.setOpacity(1.0)

    def state(self):
        return {"t": self.t, "rot": list(self.rot)}


SCENE_MAKERS = {
    "Harbour": lambda env: combine(Boats(env), Lighthouse(env)),
    "Snowy Village": Smoke,
    "River Bridge": Beacons,
    "Waterfront": lambda env: combine(Searchlights(env), Beacons(env)),
    "Cityscape": Beacons,
    "Countryside": Turbines,
}
for _name, _make in SCENE_MAKERS.items():
    register_scene_fx(_name, _make)
