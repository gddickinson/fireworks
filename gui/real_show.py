"""State of the desktop app's realistic renderer (no Qt imports): the Sim, its Director and the burst lights.

`RealShow` owns a `models.pyro.Sim` (3-D shells in metres) and a `models.director.Director` (auto launch, finale,
messages).  `sync()` maps the classic controls the way the web version does (web/static/real_view.js):
star_scale = 0.5 + count/100, gravity_scale = gravity/0.1, height_scale = clamp((launch_speed/10)^2, 0.35, 1.3).
`step()` advances one frame (1/60 s) and turns the sim's burst/launch events into decaying lights
(the light model of web/static/fw_atmos.js) and sets the gusty wind (effects/fx_base.gusty_wind around WIND_BASE,
seeded by `seed`, as web/static/real_view.js: one wind for shells, smoke and weather).  Ground devices
(models/ground_effects.py): `set_ground` (Director.ground, niagara height from a bridge) and `fire_ground`.
The QPainter side lives in gui/real_painter.py.
"""
from __future__ import annotations

import math
import random

from effects.fx_base import gusty_wind
from models.director import Director
from models.pyro import DT, FOCAL, Sim
from models.shell_types import TYPES

HORIZON = 0.9          # classic scenery: fraction of the view height above the launch line (realistic
                       # scenery: effects/scenery.SCENERY_HORIZON)
BEACH_HORIZON = 0.7    # classic scenery: BeachBackground's waterline: shells rise from the water and are mirrored in it
QUALITY = 0.5
BUDGET = 4000
WIND_BASE = 1.5        # m/s, +x (models.pyro.Sim.wind's default)


class Light:
    __slots__ = ("x", "y", "z", "col", "s", "t", "launch")

    def __init__(self, x, y, z, col, s, launch=False):
        self.x, self.y, self.z, self.col, self.s, self.t, self.launch = x, y, z, col, s, 0.0, launch

    def intensity(self) -> float:
        """A sharp flash plus the ~1 s glow of the burning stars (launch: a short orange glow)."""
        if self.launch:
            return self.s * math.exp(-self.t / 0.6)
        return self.s * (2.4 * math.exp(-self.t / 0.09) + 0.45 * math.exp(-self.t / 1.1))


class RealShow:
    def __init__(self, aspect: float = 16 / 9, horizon: float = HORIZON, rand=None, seed=None):
        self.rand = rand or random.Random()
        self.seed = random.Random().getrandbits(32) if seed is None else int(seed)
        self.sim = Sim(self.rand, aspect=aspect, horizon=horizon, quality=QUALITY, budget=BUDGET)
        self.director = Director(self.rand)
        self.lights: list = []

    # --- settings -------------------------------------------------------------------------------------------
    def sync(self, particle_count: int, gravity: float, launch_speed: float, color, pattern, pattern_scale: float,
             auto: bool) -> None:
        """color: (r, g, b) or None for random pyrotechnic colours; pattern: object with get_points() or None."""
        m, d = self.sim, self.director
        m.star_scale = 0.5 + particle_count / 100.0
        m.gravity_scale = gravity / 0.1
        m.height_scale = min(1.3, max(0.35, (launch_speed / 10.0) ** 2))
        d.color = None if color is None else tuple(int(c) for c in color)
        d.pattern = pattern
        d.pattern_scale = pattern_scale
        d.auto = auto

    def set_shell_type(self, name: str) -> None:
        """'mixed' or one of models.shell_types.TYPES (labels are mapped by the caller)."""
        self.director.shell_type = name if name in TYPES else "mixed"

    def set_lift_time(self, seconds) -> None:
        """Sim.lift_time: seconds from launch to burst at most (None: real time, about 4.5 s for a high shell)."""
        self.sim.lift_time = None if seconds is None else float(seconds)

    def set_ground(self, on: bool, niagara_height=None) -> None:
        """Ground devices in auto launching and the finale; niagara_height: a bridge's deck height (m) or None."""
        self.director.ground = bool(on)
        self.director.niagara_height = niagara_height

    def fire_ground(self, kind: str, niagara_height=None):
        """Light one ground device now (as the web's Fire button: a niagara centred, at the bridge's height)."""
        opts = {"height": float(niagara_height)} if kind == "niagara" and niagara_height else None
        return self.sim.ground(kind, 0.0 if kind == "niagara" else None, None, opts)

    def set_view(self, aspect: float, horizon: float) -> None:
        self.sim.aspect = aspect
        self.sim.horizon = horizon

    # --- actions --------------------------------------------------------------------------------------------
    def launch(self, x_frac=None):
        """One shell of the current type/pattern; x_frac in -1..1 across the view (None: random)."""
        return self.sim.launch(self.director.recipe(), x_frac, None if x_frac is None else 450.0, None, 0.0)

    def start_finale(self) -> None:
        self.director.start_finale(self.sim)

    def queue_messages(self, messages: list, opener: str = "off", finale: bool = False) -> float:
        return self.director.queue_messages(self.sim, messages, opener, finale)

    def clear(self) -> None:
        self.sim.stars.clear()
        self.sim.emitters.clear()
        self.lights.clear()
        self.director.mode = "auto"
        self.director.cues = []

    # --- frame ----------------------------------------------------------------------------------------------
    def step(self) -> None:
        self.director.step(self.sim)
        self.sim.step()
        self.sim.wind = gusty_wind(WIND_BASE, self.sim.time, self.seed)
        for e in self.sim.events:
            if e[0] == "burst":
                _, x, y, z, col, strength = e
                self.lights.append(Light(x, y, z, col, strength))
            elif e[0] == "launch":
                self.lights.append(Light(e[1], 2.0, e[2], (255, 170, 90), 0.35, launch=True))
        for L in self.lights:
            L.t += DT
        self.lights = [L for L in self.lights if L.t < 4.0]

    def screen_lights(self, W: int, H: int, n: int = 6) -> list:
        """The n strongest lights as (x px, y px, radius px, intensity, (r, g, b))."""
        F, hz = FOCAL * H, self.sim.horizon * H
        out = []
        for L in self.lights:
            i = L.intensity()
            if i < 0.01:
                continue
            out.append((W / 2 + F * L.x / L.z, hz - F * L.y / L.z, F * 140.0 / L.z, i, L.col))
        out.sort(key=lambda t: -t[3])
        return out[:n]
