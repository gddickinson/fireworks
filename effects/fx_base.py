"""Plug-in layers of the desktop realistic renderer: a port of web/static/fw_fx.js (registries, layers, gusty wind).

Weather (effects/wx_*.py), sky effects (effects/sky_fx.py, sky_aurora.py) and animated scene objects
(effects/scene_fx.py) are plug-ins drawn by gui/real_painter.py in two places of a frame:
  sky  - after the scenery's back image and the burst light, behind the fireworks (moon, aurora, boats, clouds);
  over - after the scenery's front silhouettes, in front of everything but the vignette (rain, snow, fog).
Plug-in interface (all optional): resize(env) · update(dt, env) · draw_sky(p, env) · draw_over(p, env).
A plug-in paints straight onto the frame's QPainter `p` (source-over, view px) and uses its own buffers for any
other composition mode; the layers wrap every call in p.save()/p.restore().  update() is plain seeded arithmetic
(no Qt), so it can be tested without painting.  The env is an `FxEnv` (the web's env with cssW/cssH -> W/H).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

WEATHER: dict = {}      # name -> (label, make(env))
SKY_FX: dict = {}       # key -> (label, make(env))
SCENE_FX: dict = {}     # scenery name -> make(env)   (animated objects of a scene, always on)


def register_weather(name: str, label: str, make) -> None:
    WEATHER[name] = (label, make)


def register_sky_fx(key: str, label: str, make) -> None:
    SKY_FX[key] = (label, make)


def register_scene_fx(scene: str, make) -> None:
    SCENE_FX[scene] = make


@dataclass
class FxEnv:
    """What a plug-in sees each frame (web env): W, H - the view in px (the web's cssW, cssH); scenery - an
    effects.scenery.Scenery (its images and positions are in scenery px, `k` view px per scenery px) or None;
    lights - the strongest burst lights [(x, y, r, I, (r, g, b))] in view px (RealShow.screen_lights);
    time - sim time (s); wind - m/s (+x, gusty); seed - the show's seed; reduced - calmer motion; quality 0..1;
    intensity - the rain / snow amount (panel slider, 1 = normal)."""
    W: int
    H: int
    scenery: object = None
    lights: list = field(default_factory=list)
    time: float = 0.0
    wind: float = 1.5
    seed: int = 7
    reduced: bool = False
    quality: float = 1.0
    intensity: float = 1.0

    @property
    def k(self) -> float:
        S = self.scenery
        return self.W / max(1, S.W) if S is not None else 1.0


class FxLayers:
    """The active plug-ins (scene animations, sky effects, then the weather) and their two draw passes."""

    def __init__(self):
        self.plugins: list = []
        self.size = (0, 0)

    def set(self, plugins: list, env: FxEnv) -> None:
        self.plugins = [p for p in plugins if p is not None]
        self.resize(env, True)

    def resize(self, env: FxEnv, force: bool = False) -> None:
        if force or (env.W, env.H) != self.size:
            self.size = (env.W, env.H)
            for p in self.plugins:
                if hasattr(p, "resize"):
                    p.resize(env)

    def update(self, dt: float, env: FxEnv) -> None:
        for p in self.plugins:
            if hasattr(p, "update"):
                p.update(dt, env)

    def _draw(self, name: str, p, env: FxEnv) -> None:
        for plug in self.plugins:
            fn = getattr(plug, name, None)
            if fn is not None:
                p.save()
                fn(p, env)
                p.restore()

    def draw_sky(self, p, env: FxEnv) -> None:
        self._draw("draw_sky", p, env)

    def draw_over(self, p, env: FxEnv) -> None:
        self._draw("draw_over", p, env)


class Combined:
    """Several plug-ins run as one (Storm = clouds + lightning + rain; a scene with several animated objects).
    draw_sky / draw_over exist only when a part has them."""

    def __init__(self, parts):
        self.parts = [p for p in parts if p is not None]
        for name in ("draw_sky", "draw_over"):
            if any(hasattr(p, name) for p in self.parts):
                setattr(self, name, self._drawer(name))

    def _drawer(self, name):
        def draw(p, env):
            for part in self.parts:
                fn = getattr(part, name, None)
                if fn is not None:
                    p.save()
                    fn(p, env)
                    p.restore()
        return draw

    def resize(self, env):
        for p in self.parts:
            if hasattr(p, "resize"):
                p.resize(env)

    def update(self, dt, env):
        for p in self.parts:
            if hasattr(p, "update"):
                p.update(dt, env)

    def state(self):
        return [p.state() if hasattr(p, "state") else None for p in self.parts]


def combine(*parts) -> Combined:
    if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
        parts = parts[0]
    return Combined(parts)


def gusty_wind(base: float, t: float, seed: int = 0) -> float:
    """Gusty wind (m/s, +x) around `base`: two incommensurate swells and a gust term (fw_fx.js gustyWind)."""
    ph = (seed % 1000) * 0.01
    swell = 0.25 * math.sin(t * 0.21 + ph) + 0.15 * math.sin(t * 0.53 + 2 * ph)
    gust = max(0.0, math.sin(t * 0.11 + ph * 3)) ** 6 * 0.8
    return base * (1 + swell + gust)
