"""Realistic firework physics (Qt-free): shells and stars moving in 3-D metres under gravity and quadratic air drag.

Units: metres, seconds, fixed time step DT = 1/60 s.  World axes: x to the right, y up (ground y = 0), z away from the
viewer (launch sites 300-600 m away).  Every object is a `Star` (the rising shell, the burning stars of a burst,
tail sparks, crackle pops, crossette fragments, sub-shells of a multi-break); `kind` and a few flags say what it
does.  Drag acts on the velocity relative to the wind: a = -k |v - w| (v - w), so a star with drag coefficient k has
terminal velocity sqrt(g / k).  Stars burst out at 30-70 m/s, slow within a second or two and then droop.

`Sim.step()` advances one frame and fills `Sim.events` (launches since the last step, bursts, crackles) for lights, smoke and sound.
The shell recipes live in models/shell_types.py and the launch schedule in models/director.py.  All randomness goes
through the injected ``rand`` (``random.Random`` in the desktop app, a seeded mulberry32 ``PyRand`` for the reference
runs), in the same order as the JavaScript copy web/static/fw_pyro.js, which is node-tested against these runs.
"""
from __future__ import annotations

import math

DT = 1.0 / 60.0
G = 9.81
FOCAL = 1.5           # camera focal length in units of the view height (shared with the renderers)
SHELL_DEPTH = (300.0, 600.0)
SHELL_DRAG = 0.006   # shells: terminal velocity ~40 m/s


class Star:
    __slots__ = ("kind", "x", "y", "z", "vx", "vy", "vz", "k", "age", "life", "color", "color2", "change",
                 "bright", "size", "trail", "trail_color", "trail_life", "acc", "glitter", "strobe", "phase",
                 "end", "recipe", "target", "glide", "hold", "nograv", "theta0", "rate")

    def __init__(self, kind, x, y, z, vx, vy, vz, k, life, color, bright=1.0, size=1.0):
        self.kind = kind
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = vx, vy, vz
        self.k = k
        self.age = 0.0
        self.life = life
        self.color = color
        self.color2 = None    # colour-changing star: color2 after `change` of the life
        self.change = 1.0
        self.bright = bright
        self.size = size
        self.trail = 0.0      # tail sparks per second
        self.trail_color = color
        self.trail_life = 0.6
        self.acc = 0.0        # fractional spark accumulator
        self.glitter = False
        self.strobe = 0.0     # strobe period in s (0: steady)
        self.phase = 0.0
        self.end = None       # None | "crackle" | "split" | "burst"
        self.recipe = None    # sub-shell recipe for end == "burst"
        self.target = None    # message star: (x, y) it glides to
        self.glide = 0.0      # message star: time the glide starts
        self.hold = 0.0       # message star: time it is released to gravity
        self.nograv = False
        self.theta0 = 0.0     # rising shell: exact drag trajectory parameter atan(v0 sqrt(k / g)) (0: integrate)
        self.rate = 1.0       # rising shell: playback rate of its climb (Lift time option)


def sphere_dirs(n: int, rot: float):
    """n directions spread evenly over the unit sphere (Fibonacci lattice) turned by rot about the vertical."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    out = []
    for i in range(n):
        y = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1.0 - y * y))
        a = i * golden + rot
        out.append((r * math.cos(a), y, r * math.sin(a)))
    return out


class Sim:
    """The sky: all stars, the wind, the camera's view cone (to place shells) and per-frame events."""

    def __init__(self, rand, aspect: float = 16 / 9, horizon: float = 0.86, quality: float = 1.0,
                 budget: int = 1_000_000):
        self.rand = rand
        self.aspect = aspect          # view width / height
        self.horizon = horizon        # fraction of the view height above the horizon line
        self.quality = quality        # scales star counts and spark rates (performance)
        self.budget = budget          # no new tail sparks while more stars than this are alive
        self.stars: list = []
        self.events: list = []
        self.time = 0.0
        self.frame = 0
        self.wind = 1.5               # m/s, +x
        self.gravity_scale = 1.0
        self.height_scale = 1.0
        self.star_scale = 1.0
        self.lift_time = 3.0          # s from launch to burst at most: longer climbs are played faster (None: real time)
        self._new: list = []
        self._pending: list = []      # events raised between frames (launches), reported by the next step

    # --- view geometry (pinhole camera at the origin looking along +z, horizon line at `horizon`) --------------
    def x_max(self, z: float) -> float:
        return z * self.aspect / (2.0 * FOCAL)

    def y_top(self, z: float) -> float:
        return z * self.horizon / FOCAL

    def count(self, n: float) -> int:
        return max(4, int(n * self.star_scale * self.quality))

    # --- launching --------------------------------------------------------------------------------------------
    def launch(self, recipe: dict, x: float | None = None, z: float | None = None, height: float | None = None,
               tilt: float = 0.0):
        """Fire a shell with `recipe` (see shell_types) from (x, 0, z) to burst at `height` (fractions of the view)."""
        R = self.rand
        if z is None:
            z = R.uniform(*SHELL_DEPTH)
        if x is None:
            x = R.uniform(-0.85, 0.85) * self.x_max(z)
        else:
            x = x * self.x_max(z)
        if height is None:
            height = R.uniform(0.4, 0.75)
        h = height * self.y_top(z) * self.height_scale
        g = G * self.gravity_scale
        k = SHELL_DRAG
        # speed that reaches height h against gravity and drag: h = ln(1 + k v^2 / g) / (2 k)
        vy = math.sqrt(g / k * (math.exp(2.0 * k * h) - 1.0)) if g > 0 else 60.0
        vx = R.uniform(-1.5, 1.5) + tilt * vy
        s = Star("shell", x, 0.0, z, vx, vy, 0.0, k, 30.0 if g > 0 else h / vy, (255, 160, 70), 1.0, 1.4)
        if g > 0:
            s.theta0 = math.atan(vy * math.sqrt(k / g))
            climb = s.theta0 / math.sqrt(g * k)       # physical time to the top (about 4-5 s for 150 m)
            if self.lift_time is not None and self.lift_time < climb:
                s.rate = climb / self.lift_time      # Lift time: the same trajectory, played faster
        s.trail = (110.0 if recipe["type"] == "palm" else 55.0) * self.quality
        s.trail_color = (255, 150, 52)
        s.trail_life = 0.55
        s.end = "burst"
        s.recipe = recipe
        self.stars.append(s)
        self._pending.append(("launch", x, z, recipe["type"]))
        return s

    # --- the frame step ---------------------------------------------------------------------------------------
    def step(self) -> None:
        from models.shell_types import burst  # late import: shell_types imports this module
        self.events, self._pending = self._pending, []
        R = self.rand
        g = G * self.gravity_scale
        wind = self.wind
        alive = []
        born: list = []
        crowded = len(self.stars) > self.budget
        for s in self.stars:
            if s.age < 0.0:                       # delayed (crackle pop not yet lit)
                s.age += DT
                alive.append(s)
                continue
            if s.theta0 > 0.0:                    # rising shell: exact solution of the climb against drag
                th = max(0.0, s.theta0 - math.sqrt(g * s.k) * (s.age + DT) * s.rate)
                s.vy = math.sqrt(g / s.k) * math.tan(th)
                s.x += s.vx * DT * s.rate
                s.y = math.log(math.cos(th) / math.cos(s.theta0)) / s.k
            elif s.target is not None and s.glide <= s.age < s.hold:
                w = 5.5                           # critically damped glide to the letter position
                s.vx += (w * w * (s.target[0] - s.x) - 2.0 * w * s.vx) * DT
                s.vy += (w * w * (s.target[1] - s.y) - 2.0 * w * s.vy) * DT
                s.vz += (-2.0 * w * s.vz) * DT
                s.x += s.vx * DT
                s.y += s.vy * DT
                s.z += s.vz * DT
            else:
                rx = s.vx - wind
                sp = math.sqrt(rx * rx + s.vy * s.vy + s.vz * s.vz)
                d = s.k * sp * DT
                s.vx -= d * rx
                s.vy -= d * s.vy
                s.vz -= d * s.vz
                if not (s.nograv and s.age < s.glide):
                    s.vy -= g * DT
                s.x += s.vx * DT
                s.y += s.vy * DT
                s.z += s.vz * DT
            s.age += DT
            if s.trail > 0.0 and not crowded:
                s.acc += s.trail * DT
                while s.acc >= 1.0:
                    s.acc -= 1.0
                    born.append(self._spark(s))
            if s.kind == "shell" and s.vy <= 0.0:
                s.age = s.life
            if s.age >= s.life:
                if s.end == "burst":
                    burst(self, s)
                elif s.end == "split":
                    self._split(s, born)
                elif s.end == "crackle":
                    p = Star("pop", s.x, s.y, s.z, s.vx * 0.3, s.vy * 0.3, s.vz * 0.3, 0.5, 0.07, s.color, 1.0, 1.6)
                    p.age = -R.uniform(0.0, 0.6)
                    born.append(p)
                    self.events.append(("crackle", s.x, s.y, s.z))
                continue
            alive.append(s)
        self.stars = alive + born + self._new
        self._new = []
        self.time += DT
        self.frame += 1

    def add(self, star: Star) -> Star:
        """Stars created by a burst during step() join after the frame (shell_types calls this)."""
        self._new.append(star)
        return star

    def _spark(self, s: Star) -> Star:
        R = self.rand
        f, j = (0.15, 6.0) if s.kind != "shell" else (0.0, 3.0)   # a shell's tail stays behind it
        sp = Star("spark", s.x, s.y, s.z, s.vx * f + R.uniform(-j, j), s.vy * f + R.uniform(-j, j),
                  s.vz * f, 1.2, s.trail_life * R.uniform(0.5, 1.0), s.trail_color, 0.8 if s.glitter else 0.55,
                  0.7)
        sp.glitter = s.glitter
        sp.phase = s.age * 13.0
        return sp

    def _split(self, s: Star, born: list) -> None:
        a0 = self.rand.uniform(0.0, 2.0 * math.pi)
        for i in range(4):
            a = a0 + i * math.pi / 2.0
            c = Star("star", s.x, s.y, s.z, s.vx + 16.0 * math.cos(a), s.vy + 16.0 * math.sin(a), s.vz, s.k,
                     s.life * 0.55, s.color, s.bright, s.size * 0.8)
            c.trail, c.trail_color, c.trail_life = s.trail, s.trail_color, s.trail_life * 0.7
            c.phase = a
            born.append(c)
        self.events.append(("crackle", s.x, s.y, s.z))
