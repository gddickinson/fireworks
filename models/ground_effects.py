"""Ground devices of the realistic engine (Qt-free): gerbs, roman candles, mines, cakes and niagara curtains.
JavaScript copy: web/static/fw_ground.js (same random order; checked by fw_pyro.test.mjs).

A device is an `Emitter` that `Sim.step()` advances before the stars move (`Sim.ground()` places one); it adds
ordinary `Star`s (models/pyro.py) through `sim.add`, so they join after the frame like burst stars.  Stars of ground
devices carry `ground = True` and die when they fall below the ground (y < 0).  Metres and seconds:
  gerb     a fountain: a nozzle 0.5 m up sprays ~240 sparks/s in a 9 degree cone at 17-22 m/s for 4-8 s; small
           sparks (k = 0.07, terminal ~12 m/s) rise ~8-10 m in ~1.2 s and droop; gold or silver, optional glitter;
  candle   a roman candle: n (8) single coloured stars every 0.45 s at 28-34 m/s (k = 0.035), each burning out near
           its ~20 m apex after 1.6-2.0 s, with a short gold tail; a 'launch' event (light, smoke, thump) per shot;
  mine     one upward burst from a mortar: ~60 stars and 6 gold comets in a 20 degree cone at 38-62 m/s, reaching
           ~30-35 m; a 'burst' event at 2 m;
  cake     a battery: n (16) small shells every 0.18 s in a fan sweeping +-26 degrees and back, each climbing ~55 m
           (integrated drag, k = 0.01) and bursting into a small peony/chrysanthemum/crackle;
  niagara  a line of nozzles at height y (a bridge, default 18 m) dropping gold sparks (24/s per nozzle, 2.5 m apart)
           that fall at their terminal ~5.7 m/s (k = 0.3) for 2.2-3.4 s: a curtain for 9-12 s.
Gerbs and niagaras raise a 'ground' event (x, y, z, colour, strength, duration) at ignition for a lasting light.
"""
from __future__ import annotations

import math

from models.pyro_colors import PALETTE, TAIL_GOLD, TAIL_SILVER, pick_color

DEVICES = ("gerb", "candle", "mine", "cake", "niagara")
LABELS = {"gerb": "Gerb (fountain)", "candle": "Roman candle", "mine": "Mine", "cake": "Cake (barrage)",
          "niagara": "Niagara falls"}
AUTO_DEVICES = ("gerb", "candle", "mine", "cake")     # niagara needs a bridge: finale only
GROUND_DEPTH = (110.0, 180.0)                          # m: the firing line is nearer than the shells' mortars
CAKE_STYLES = ("peony", "chrysanthemum", "crackle")


def _opt(opts: dict, key: str, fn):
    """opts[key] if given, else fn() (a random draw only when the option is missing)."""
    return opts[key] if key in opts else fn()


class Emitter:
    """One ground device. `life`: seconds it runs; shots (candle, cake) are fired at `t0 + i * every`."""

    def __init__(self, kind, x, y, z, life):
        self.kind = kind
        self.x, self.y, self.z = x, y, z
        self.age = 0.0
        self.life = life
        self.acc = 0.0          # fractional spark accumulator
        self.rate = 0.0         # sparks per second at full flow (gerb, niagara: all nozzles)
        self.speed = 0.0
        self.color = TAIL_GOLD
        self.glitter = False
        self.n = 0              # shots (candle, cake), nozzles (niagara)
        self.fired = 0
        self.every = 0.0
        self.width = 0.0        # niagara: length of the line in m
        self.style = "peony"    # cake: burst type
        self.tilt = 0.0


def make_device(sim, kind: str, x=None, z=None, opts=None) -> Emitter:
    """A ground device at x (fraction of the half-width at depth z) and depth z (m); random where not given.
    opts: gerb {duration, color: 'gold'|'silver', glitter}, candle {shots, tilt}, mine {}, cake {shots, style},
    niagara {height (m), width (fraction of the half-width), duration}."""
    if kind not in DEVICES:
        raise ValueError(f"unknown ground device {kind!r}")
    R = sim.rand
    opts = opts or {}
    if z is None:
        z = R.uniform(*GROUND_DEPTH)
    xm = R.uniform(-0.7, 0.7) * sim.x_max(z) if x is None else x * sim.x_max(z)
    q = sim.quality
    if kind == "gerb":
        e = Emitter(kind, xm, 0.5, z, _opt(opts, "duration", lambda: R.uniform(4.0, 8.0)))
        silver = _opt(opts, "color", lambda: "silver" if R.random() < 0.4 else "gold") == "silver"
        e.color = TAIL_SILVER if silver else TAIL_GOLD
        e.glitter = bool(_opt(opts, "glitter", lambda: R.random() < 0.35))
        e.rate, e.speed = 240.0 * q, R.uniform(17.0, 22.0)
    elif kind == "candle":
        e = Emitter(kind, xm, 0.5, z, 0.0)
        e.n, e.every = int(opts.get("shots", 8)), 0.45
        e.tilt = float(opts.get("tilt", 0.0))
        e.life = 0.1 + e.n * e.every
    elif kind == "mine":
        e = Emitter(kind, xm, 0.5, z, 0.0)
        e.color = pick_color(R)
    elif kind == "cake":
        e = Emitter(kind, xm, 0.3, z, 0.0)
        e.n, e.every = int(opts.get("shots", 16)), 0.18
        e.style = _opt(opts, "style", lambda: CAKE_STYLES[int(R.random() * len(CAKE_STYLES))])
        e.life = 0.1 + e.n * e.every
    else:
        e = Emitter(kind, xm, float(opts.get("height", 18.0)), z, _opt(opts, "duration", lambda: R.uniform(9.0, 12.0)))
        e.width = float(opts.get("width", 0.8)) * sim.x_max(z)
        e.n = max(6, int(e.width / 2.5))
        e.rate = 24.0 * e.n * q
        e.color = PALETTE["gold"]
    if kind in ("gerb", "niagara"):
        sim._pending.append(("ground", e.x, e.y + 0.5, e.z, e.color, 0.15 if kind == "gerb" else 0.4, e.life))
    return e


def _envelope(e: Emitter, ramp: float) -> float:
    """Flow of a fountain: lights over `ramp` s, full, then dies away over the last 15 % of its life."""
    up = min(1.0, e.age / ramp)
    tail = 0.15 * e.life
    return up * min(1.0, max(0.0, (e.life - e.age) / tail))


def step_device(sim, e: Emitter, dt: float, crowded: bool) -> bool:
    """Advance one device by dt; returns False when it has finished."""
    e.age += dt
    if e.kind in ("gerb", "niagara"):
        e.acc += e.rate * _envelope(e, 0.4 if e.kind == "gerb" else 1.0) * dt
        while e.acc >= 1.0:
            e.acc -= 1.0
            if not crowded:
                (_gerb_spark if e.kind == "gerb" else _niagara_spark)(sim, e)
    elif e.kind == "mine":
        _mine(sim, e)
        return False
    else:
        while e.fired < e.n and e.age >= 0.1 + e.fired * e.every:
            (_candle_shot if e.kind == "candle" else _cake_shot)(sim, e)
            e.fired += 1
    return e.age < e.life


def _star(sim, kind, e, x, y, vx, vy, vz, k, life, color, bright=1.0, size=1.0):
    from models.pyro import Star  # late: pyro imports this module lazily too
    s = Star(kind, x, y, e.z, vx, vy, vz, k, life, color, bright, size)
    s.ground = True
    return sim.add(s)


def _cone(R, half: float, speed: float):
    """A velocity in a cone of half-angle `half` about the vertical (uniform over the cap's area)."""
    th = half * math.sqrt(R.random())
    ph = R.uniform(0.0, 2.0 * math.pi)
    return math.sin(th) * math.cos(ph) * speed, math.cos(th) * speed, math.sin(th) * math.sin(ph) * speed


def _gerb_spark(sim, e: Emitter) -> None:
    R = sim.rand
    vx, vy, vz = _cone(R, 0.16, e.speed * R.uniform(0.75, 1.1))
    s = _star(sim, "spark", e, e.x, e.y, vx, vy, vz, 0.07, R.uniform(0.9, 1.6), e.color,
              0.75 if e.glitter else 0.6, 0.8)
    s.glitter = e.glitter
    s.phase = R.uniform(0.0, 6.2832)


def _niagara_spark(sim, e: Emitter) -> None:
    R = sim.rand
    i = int(R.random() * e.n)
    x = e.x - e.width / 2 + (i + 0.5) * e.width / e.n
    s = _star(sim, "spark", e, x, e.y, R.uniform(-0.6, 0.6), R.uniform(-1.5, 0.3), R.uniform(-0.4, 0.4), 0.3,
              R.uniform(2.2, 3.4), e.color, 0.8, 0.75)
    s.phase = R.uniform(0.0, 6.2832)


def _candle_shot(sim, e: Emitter) -> None:
    R = sim.rand
    a = e.tilt + R.uniform(-0.05, 0.05)
    v = R.uniform(28.0, 34.0)
    s = _star(sim, "star", e, e.x, e.y, math.sin(a) * v, math.cos(a) * v, R.uniform(-1.0, 1.0), 0.035,
              R.uniform(1.6, 2.0), pick_color(R), 1.1, 1.25)
    s.trail, s.trail_color, s.trail_life = 18.0 * sim.quality, TAIL_GOLD, 0.35
    s.phase = e.fired * 0.9
    sim.events.append(("launch", e.x, e.z, "candle"))


def _mine(sim, e: Emitter) -> None:
    R = sim.rand
    for i in range(sim.count(60)):
        vx, vy, vz = _cone(R, 0.35, R.uniform(38.0, 58.0))
        s = _star(sim, "star", e, e.x, e.y, vx, vy, vz, 0.035, R.uniform(1.4, 2.0), e.color)
        s.phase = i * 0.37
    for i in range(6):
        vx, vy, vz = _cone(R, 0.3, R.uniform(48.0, 62.0))
        s = _star(sim, "star", e, e.x, e.y, vx, vy, vz, 0.025, R.uniform(1.8, 2.3), PALETTE["gold"], 0.7, 1.4)
        s.trail, s.trail_color, s.trail_life = 40.0 * sim.quality, TAIL_GOLD, 0.6
    sim.events.append(("burst", e.x, 2.0, e.z, e.color, 0.8))


def _cake_shot(sim, e: Emitter) -> None:
    from models.pyro import SHELL_DRAG, Star
    R = sim.rand
    m = 8                                            # a fan of m tubes swept left to right and back
    j = e.fired % (2 * m - 2)
    p = j if j < m else 2 * m - 2 - j
    a = 0.45 * (2.0 * p / (m - 1) - 1.0)
    v = R.uniform(44.0, 50.0)
    s = Star("shell", e.x, e.y, e.z, math.sin(a) * v, math.cos(a) * v, 0.0, SHELL_DRAG * 1.6, 30.0,
             (255, 160, 70), 1.0, 1.0)
    s.trail, s.trail_color, s.trail_life = 30.0 * sim.quality, TAIL_GOLD, 0.4
    s.end = "burst"
    s.recipe = {"type": e.style, "color": pick_color(R), "color2": None, "pistil": None, "size": 0.42}
    sim.add(s)
    sim.events.append(("launch", e.x, e.z, "cake"))
