"""Sky effects (user-toggled plug-ins, effects/fx_base.register_sky_fx): the moon, shooting stars and sky lanterns.
A QPainter/numpy port of web/static/fw_sky_fx.js (same seeds and random order).  The aurora is in sky_aurora.py.

All drawing is cut to the open sky (and to the water for reflections) with the scenery's material map
(effects/fx_masks.py).  update() only advances numbers (seeded, no Qt), so it is testable; state() returns them.
Moon: env.scenery.moon = {x, y, r (view px), time} is published each update, so a cloud plug-in that runs later in
the same step can light its cloud edges when moon["time"] == env.time.
"""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QRadialGradient

from effects.fx_base import register_sky_fx
from effects.fx_masks import FMT, exp_wait, horizon_px, is_dusk, masked, smooth, soft_sprite, water_px
from effects.scenery_noise import fbm2, hash, prng

M32 = 0xFFFFFFFF


def _col(rgb, a: float) -> QColor:
    return QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]), max(0, min(255, int(round(a * 255)))))


# ---- Moon --------------------------------------------------------------------------------------------------
def moon_disc(R: float, seed: int, phase: float, side: int, tilt: float):
    """The lit moon as an (n, n, 4) uint8 RGBA array (straight alpha): phase lit by a sun direction (normal . light),
    earthshine, limb darkening and maria from fbm2.  Returns (n, px)."""
    n = int(math.ceil(2 * R)) + 2
    lx0, lz = math.sin(phase) * side, math.cos(phase)
    lx, ly = lx0 * math.cos(tilt), lx0 * math.sin(tilt)
    idx = np.arange(n) + 0.5 - n / 2
    nx, ny = (idx / R)[None, :], (idx / R)[:, None]
    r2 = nx * nx + ny * ny
    a = np.clip((1 - np.sqrt(r2)) * R + 0.5, 0, 1)
    nz = np.sqrt(np.maximum(0, 1 - r2))
    lit = smooth(-0.05, 0.1, nx * lx + ny * ly + nz * lz)
    maria = fbm2(seed, nx * 1.8 + 3, ny * 1.8 + 1, 4)
    alb = 0.72 + 0.28 * smooth(0.38, 0.62, maria)
    limb = 0.8 + 0.2 * nz
    px = np.zeros((n, n, 4), np.uint8)
    on = a > 0
    for ch, (full, dark) in enumerate(((240, 38), (236, 44), (222, 60))):
        v = full * alb * limb * lit + dark * (1 - lit)
        px[..., ch] = np.where(on, np.clip(np.rint(v), 0, 255), 0)
    px[..., 3] = np.where(on, np.clip(np.rint(255 * a), 0, 255), 0)
    return n, px


def _rgba_image(px: np.ndarray) -> QImage:
    h, w = px.shape[:2]
    return QImage(np.ascontiguousarray(px).tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888).copy()


class Moon:
    def __init__(self, env):
        rnd = prng((env.seed ^ 0x6D6F6F6E) & M32)
        self.fx, self.fy = 0.18 + rnd() * 0.64, 0.22 + rnd() * 0.25
        self.side = 1 if rnd() < 0.5 else -1
        self.tilt = (rnd() - 0.5) * 0.9
        self.phase = [0.75, 1.05, 2.05, 2.35][int(rnd() * 4)]     # gibbous or crescent (radians from full)
        self.t = 0.0
        self.img = None
        self._key = None

    def geo(self, env):
        R = max(7.0, 0.024 * min(env.H, env.W * 1.2))
        return self.fx * env.W, self.fy * horizon_px(env), R

    def resize(self, env):
        self.img = None

    def update(self, dt, env):
        self.t += dt
        if env.scenery is not None and env.W:
            x, y, R = self.geo(env)
            try:
                env.scenery.moon = {"x": x, "y": y, "r": R, "time": env.time}
            except AttributeError:
                pass

    def _render(self, env) -> QImage:
        W, H = max(1, int(env.W)), max(1, int(env.H))
        x, y, R = self.geo(env)
        dusk, lum = is_dusk(env), (1 + math.cos(self.phase)) / 2
        img = QImage(W, H, FMT)
        img.fill(0)
        g = QPainter(img)
        g.setRenderHint(QPainter.RenderHint.Antialiasing)

        def sky(l):
            big, kk = max(W, H) * 0.6, 0.4 + lum           # moonlit sky, then the halo
            for r, col, a, core in ((big, (150, 175, 230), (0.05 if dusk else 0.11) * kk, 0.02),
                                    (R * 8, (205, 218, 242), 0.28 * kk, 0.1)):
                gr = QRadialGradient(QPointF(x, y), r)
                gr.setColorAt(0, _col(col, a))
                gr.setColorAt(core, _col(col, a * 0.7))
                gr.setColorAt(0.4, _col(col, a * 0.18))
                gr.setColorAt(1, _col(col, 0))
                l.fillRect(QRectF(x - r, y - r, 2 * r, 2 * r), gr)
            n, px = moon_disc(R, env.seed & 0xFFFF, self.phase, self.side, self.tilt)
            l.drawImage(QPointF(x - n / 2, y - n / 2), _rgba_image(px))

        masked(g, env, "sky", sky)
        wl = water_px(env)
        if wl is not None:
            def column(l):                                  # the moon's broad reflected column
                gr = QLinearGradient(0, wl, 0, H)
                gr.setColorAt(0, QColor(200, 210, 235, 13))
                gr.setColorAt(1, QColor(200, 210, 235, 0))
                path = QPainterPath()
                path.moveTo(x - R * 0.8, wl)
                path.lineTo(x + R * 0.8, wl)
                path.lineTo(x + R * 3, H)
                path.lineTo(x - R * 3, H)
                path.closeSubpath()
                l.fillPath(path, gr)
            masked(g, env, "water", column, 0.4 + lum * 0.6)
        g.end()
        return img

    def draw_sky(self, p, env):
        key = (int(env.W), int(env.H), id(env.scenery))
        if self.img is None or self._key != key:
            self.img, self._key = self._render(env), key
        p.drawImage(0, 0, self.img)
        wl = water_px(env)
        if wl is None:
            return
        x, _, R = self.geo(env)
        H, seed, t = env.H, env.seed & 0xFFFF, self.t * (2 if env.reduced else 6)

        def glitter(l):                                    # dashes that switch on and off
            for i in range(110):
                u = hash(seed, i, 1)
                yy = wl + u ** 1.25 * (H - wl)
                d = (yy - wl) / max(1, H - wl)
                spread, ph = R * (0.5 + d * 4.5), hash(seed, i, 2)
                on = hash(seed + 7, i, math.floor(t + ph * 10))
                if on < 0.45:
                    continue
                xx = x + (hash(seed, i, 3) - 0.5) * 2 * spread
                w = 1 + d * 6 * on
                l.setOpacity(max(0.0, min(1.0, (on - 0.45) * 1.8) * (1 - abs(xx - x) / (spread + 1) * 0.8)))
                l.fillRect(QRectF(xx - w / 2, yy, w, 0.6 + d * 1.4), QColor(235, 238, 250))
        masked(p, env, "water", glitter)

    def state(self):
        return {"t": self.t, "fx": self.fx, "fy": self.fy, "phase": self.phase, "side": self.side, "tilt": self.tilt}


# ---- Shooting stars ----------------------------------------------------------------------------------------
class Meteors:
    """Rare, seeded arrivals (exponential waiting times); slower and rarer with reduced motion."""

    def __init__(self, env):
        self.rnd = prng((env.seed ^ 0x5EED5EED) & M32)
        self.mean = 20 if env.reduced else 7
        self.t = 0.0
        self.next = exp_wait(self.rnd(), self.mean * 0.4)
        self.list: list = []

    def _spawn(self, env):
        rnd, W, hz = self.rnd, env.W, horizon_px(env)
        d = 1 if rnd() < 0.5 else -1
        a = 0.25 + rnd() * 0.7
        sp = (0.3 + 0.45 * rnd()) * max(W, env.H) * (0.4 if env.reduced else 1)
        m = {"x": rnd() * W, "y": rnd() * hz * 0.5, "vx": math.cos(a) * sp * d, "vy": math.sin(a) * sp, "age": 0.0}
        m["life"] = (0.35 + rnd() * 0.55) * (2 if env.reduced else 1)
        m["len"] = sp * (0.1 + rnd() * 0.08)
        m["b"] = 0.5 + 0.5 * rnd()
        m["green"] = rnd() < 0.3
        self.list.append(m)
        if len(self.list) > 6:
            self.list.pop(0)

    def update(self, dt, env):
        self.t += dt
        while self.t >= self.next:
            self._spawn(env)
            self.next += exp_wait(self.rnd(), self.mean)
        for m in self.list:
            m["age"] += dt
        self.list = [m for m in self.list if m["age"] < m["life"]]

    def draw_sky(self, p, env):
        if not self.list:
            return
        kk = 0.4 if is_dusk(env) else 1.0

        def draw(l):
            for m in self.list:
                pr = m["age"] / m["life"]
                a = math.sin(math.pi * pr) * m["b"] * kk
                hx, hy = m["x"] + m["vx"] * m["age"], m["y"] + m["vy"] * m["age"]
                v = math.hypot(m["vx"], m["vy"])
                tx, ty = hx - m["vx"] / v * m["len"], hy - m["vy"] / v * m["len"]
                # one continuous, tapering streak: bright head, fading tail (a thin wedge, no dots)
                col = (215, 250, 235) if m["green"] else (238, 243, 255)
                g = QLinearGradient(tx, ty, hx, hy)
                g.setColorAt(0, _col(col, 0))
                g.setColorAt(0.7, _col(col, a * 0.45))
                g.setColorAt(1, _col(col, a))
                nx, ny, w = -m["vy"] / v, m["vx"] / v, 0.9          # half-width at the head (px)
                wedge = QPainterPath(QPointF(tx, ty))
                wedge.lineTo(hx + nx * w, hy + ny * w)
                wedge.lineTo(hx - nx * w, hy - ny * w)
                wedge.closeSubpath()
                l.setPen(Qt.PenStyle.NoPen)
                l.fillPath(wedge, g)
                l.setOpacity(max(0.0, min(1.0, a * 0.8)))
                l.drawImage(QRectF(hx - 2.5, hy - 2.5, 5, 5), soft_sprite((240, 245, 255)))
                l.setOpacity(1.0)
        masked(p, env, "sky", draw)

    def state(self):
        return {"t": self.t, "next": self.next, "list": [dict(m) for m in self.list]}


# ---- Sky lanterns ------------------------------------------------------------------------------------------
class Lanterns:
    """Warm paper lanterns rising from behind the horizon, drifting with the wind, flickering; reflected on water.
    Farther lanterns are smaller and slower."""
    N = 18

    def __init__(self, env):
        self.rnd = prng((env.seed ^ 0x1A77E125) & M32)
        self.t = 0.0
        self.list: list = []
        for _ in range(self.N):
            L = {}
            self._born(L, env, True)
            self.list.append(L)

    def _born(self, L, env, first):
        rnd, hz = self.rnd, horizon_px(env)
        L["z"] = rnd()
        L["x"] = rnd() * env.W
        L["y"] = hz - rnd() * hz * 0.85 if first else hz + 4
        L["vy"] = (10 + rnd() * 10) * (1 - 0.5 * L["z"]) * env.H / 800
        L["ph"] = rnd() * 6.28
        L["sway"] = 0.5 + rnd()

    def update(self, dt, env):
        self.t += dt
        kk = 0.6 if env.reduced else 1.0
        wind = (env.wind or 0) * env.H / 800 * 4
        for L in self.list:
            L["y"] -= L["vy"] * dt * kk
            L["x"] += (wind * (1 - 0.5 * L["z"]) + math.sin(self.t * 0.4 * L["sway"] + L["ph"]) * 3) * dt * kk
            if L["y"] < -20 or L["x"] < -60 or L["x"] > env.W + 60:
                self._born(L, env, False)

    def draw_sky(self, p, env):
        s0, hz, wl, dusk = env.H / 800, horizon_px(env), water_px(env), is_dusk(env)
        glow, t = soft_sprite((255, 140, 50), 0.06), self.t

        def draw(l, flip):
            for L in self.list:
                y = wl + (wl - L["y"]) * 0.85 if flip else L["y"]
                if flip and (y > env.H or L["y"] > wl):
                    continue
                sz = (1.6 + 2.2 * (1 - L["z"])) * s0 * (0.6 + 0.4 * min(1, max(0, L["y"] / hz)))
                fl = 0.8 + 0.2 * math.sin(t * 9 + L["ph"] * 5) * math.sin(t * 5.3 + L["ph"])
                l.setOpacity((0.4 if dusk else 0.55) * fl * (0.4 if flip else 1))
                l.drawImage(QRectF(L["x"] - sz * 3.5, y - sz * 3.5, sz * 7, sz * 7), glow)
                l.setOpacity(fl * (0.5 if flip else 1))
                l.fillRect(QRectF(L["x"] - sz * 0.5, y - sz * 0.7, sz, sz * 1.3), QColor(255, 205, 130))
            l.setOpacity(1.0)
        masked(p, env, "sky", lambda l: draw(l, False))
        if wl is not None:
            masked(p, env, "water", lambda l: draw(l, True))

    def state(self):
        return {"t": self.t, "list": [dict(L) for L in self.list]}


SKY_MAKERS = {"moon": Moon, "meteors": Meteors, "lanterns": Lanterns}
register_sky_fx("moon", "Moon", Moon)
register_sky_fx("meteors", "Shooting stars", Meteors)
register_sky_fx("lanterns", "Sky lanterns", Lanterns)
