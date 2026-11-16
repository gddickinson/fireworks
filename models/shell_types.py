"""Shell recipes (Qt-free): what a shell does when it bursts.  JavaScript copy: web/static/fw_shells.js.

A recipe is a dict {"type", "color", "color2", "size", ...}.  `make_recipe(rand, type, color)` draws the random
choices of one shell; `burst(sim, shell)` creates its stars at the shell's position.  Types:

  peony          a sphere of bright stars without tails (often with a small pistil of another colour)
  chrysanthemum  a peony whose stars leave gold or silver spark tails
  willow         dim gold stars with heavy drag and long charcoal tails that droop like willow branches
  kamuro         dense glittering gold "crown" that hangs and falls slowly
  palm           a few large comets with thick tails (rises with a thick tail: the trunk)
  crossette      comets that split into four at about a second
  ring           stars in a ring in a tilted plane (with a pistil)
  horsetail      slow, heavy-tailed stars that pour down
  crackle        gold stars ending in delayed crackling pops ("dragon eggs")
  strobe         white stars that blink on and off
  multibreak     sub-shells that fly apart and burst again into small peonies
  salute         a bright white flash with a short spray (finale "bombs")
  pattern        stars on a flat shape facing the viewer (points from models/patterns.py)
  message        stars that burst and then glide into the dots of a text and hold it before falling
"""
from __future__ import annotations

import math

from models.pyro import Star, sphere_dirs
from models.pyro_colors import PALETTE, TAIL_GOLD, TAIL_SILVER, pick_color

TYPES = ["peony", "chrysanthemum", "willow", "kamuro", "palm", "crossette", "ring", "horsetail", "crackle",
         "strobe", "multibreak"]
LABELS = {"peony": "Peony", "chrysanthemum": "Chrysanthemum", "willow": "Willow", "kamuro": "Kamuro", "palm": "Palm",
          "crossette": "Crossette", "ring": "Ring", "horsetail": "Horsetail", "crackle": "Crackle",
          "strobe": "Strobe", "multibreak": "Multi-break", "salute": "Salute"}


def make_recipe(rand, type_: str, color=None) -> dict:
    """One shell's random choices: main colour, an optional second colour (change or pistil), size."""
    if color is None:
        color = pick_color(rand)
    second = pick_color(rand)
    r = {"type": type_, "color": tuple(color), "color2": None, "pistil": None, "size": rand.uniform(0.95, 1.35)}
    roll = rand.random()
    if type_ in ("peony", "ring", "chrysanthemum") and roll < 0.4:
        r["pistil"] = second
    elif type_ in ("peony", "crossette") and roll < 0.7:
        r["color2"] = second
    return r


def _event(sim, s, color, strength):
    sim.events.append(("burst", s.x, s.y, s.z, color, strength))


def _sphere(sim, s, n, speed, k, life, color, spread=0.08):
    """Stars on an even sphere of directions, each with its own speed and life jitter."""
    R = sim.rand
    out = []
    for dx, dy, dz in sphere_dirs(n, R.uniform(0.0, 2.0 * math.pi)):
        v = speed * R.uniform(1.0 - spread, 1.0 + spread * 0.5)
        st = Star("star", s.x, s.y, s.z, s.vx * 0.3 + dx * v, s.vy * 0.3 + dy * v, dz * v, k,
                  life * R.uniform(0.88, 1.08), color)
        st.phase = R.uniform(0.0, 6.2832)
        out.append(sim.add(st))
    return out


def _tails(stars, rate, color, life, glitter=False):
    for st in stars:
        st.trail, st.trail_color, st.trail_life, st.glitter = rate, color, life, glitter


def burst(sim, s) -> None:
    """Burst shell (or sub-shell) `s` according to its recipe."""
    rec = s.recipe
    t, R, q = rec["type"], sim.rand, sim.quality
    size = rec.get("size", 1.0)
    c = rec["color"]
    if t == "peony":
        st = _sphere(sim, s, sim.count(110), 52.0 * size, 0.034, R.uniform(1.6, 2.1), c)
        _change(st, rec)
    elif t == "chrysanthemum":
        st = _sphere(sim, s, sim.count(95), 52.0 * size, 0.034, R.uniform(1.7, 2.2), c)
        _tails(st, 22.0 * q, TAIL_GOLD if R.random() < 0.6 else TAIL_SILVER, 0.55)
    elif t == "willow":
        st = _sphere(sim, s, sim.count(70), 40.0 * size, 0.09, R.uniform(3.6, 4.6), PALETTE["gold"])
        for x in st:
            x.bright = 0.55
        _tails(st, 30.0 * q, TAIL_GOLD, 1.3)
    elif t == "kamuro":
        st = _sphere(sim, s, sim.count(85), 44.0 * size, 0.07, R.uniform(3.0, 3.8), (255, 205, 130))
        for x in st:
            x.bright = 0.8
        _tails(st, 38.0 * q, (255, 214, 150), 1.0, glitter=True)
    elif t == "palm":
        st = _sphere(sim, s, max(6, int(9 * sim.star_scale)), 60.0 * size, 0.02, R.uniform(2.0, 2.5), c)
        for x in st:
            x.size = 1.8
        _tails(st, 90.0 * q, TAIL_GOLD, 0.8)
    elif t == "crossette":
        st = _sphere(sim, s, max(6, int(14 * sim.star_scale)), 44.0 * size, 0.03, R.uniform(1.0, 1.2), c)
        for x in st:
            x.end = "split"
            x.size = 1.3
        _tails(st, 28.0 * q, TAIL_GOLD, 0.5)
        _change(st, rec)
    elif t == "ring":
        _ring(sim, s, sim.count(64), 54.0 * size, c)
    elif t == "horsetail":
        st = _sphere(sim, s, sim.count(34), 20.0 * size, 0.03, R.uniform(2.8, 3.4), c)
        _tails(st, 48.0 * q, TAIL_SILVER if R.random() < 0.5 else TAIL_GOLD, 1.5)
    elif t == "crackle":
        st = _sphere(sim, s, sim.count(80), 48.0 * size, 0.04, R.uniform(1.3, 1.7), PALETTE["gold"])
        for x in st:
            x.end = "crackle"
        _tails(st, 14.0 * q, TAIL_GOLD, 0.4)
    elif t == "strobe":
        st = _sphere(sim, s, sim.count(70), 44.0 * size, 0.05, R.uniform(2.4, 3.0), PALETTE["white"])
        for x in st:
            x.strobe = R.uniform(0.08, 0.16)
    elif t == "multibreak":
        n = 4 + int(R.random() * 3)
        for i, (dx, dy, dz) in enumerate(sphere_dirs(n, R.uniform(0.0, 6.2832))):
            sub = Star("sub", s.x, s.y, s.z, dx * 30.0, dy * 30.0 + 6.0, dz * 30.0, 0.01, R.uniform(0.45, 0.8),
                       (255, 190, 110), 0.6, 0.9)
            sub.end, sub.trail, sub.trail_color, sub.trail_life = "burst", 25.0 * q, TAIL_GOLD, 0.4
            sub.recipe = {"type": "peony", "color": pick_color(R), "color2": None, "pistil": None, "size": 0.5}
            sim.add(sub)
        _event(sim, s, (255, 200, 140), 0.6)
        return
    elif t == "salute":
        st = _sphere(sim, s, sim.count(36), 65.0, 0.1, R.uniform(0.3, 0.45), PALETTE["white"])
        for x in st:
            x.bright = 1.6
            x.end = "crackle"
        _event(sim, s, (255, 245, 230), 2.5)
        return
    elif t == "pattern":
        _pattern(sim, s, rec)
    elif t == "message":
        _message(sim, s, rec)
    if rec.get("pistil") is not None:
        _sphere(sim, s, sim.count(26), 20.0 * size, 0.04, R.uniform(1.1, 1.4), rec["pistil"])
    _event(sim, s, c, size * (0.7 if t in ("willow", "horsetail") else 1.0))


def _change(stars, rec):
    if rec.get("color2") is not None:
        for st in stars:
            st.color2, st.change = rec["color2"], 0.55


def _ring(sim, s, n, speed, c):
    """A ring in a plane tilted by a random angle towards the viewer and turned about the vertical."""
    R = sim.rand
    tilt, turn = R.uniform(0.3, 1.3), R.uniform(0.0, 2.0 * math.pi)
    life = R.uniform(1.6, 2.0)
    ct, st_, cu, su = math.cos(tilt), math.sin(tilt), math.cos(turn), math.sin(turn)
    for i in range(n):
        a = 2.0 * math.pi * i / n
        px, py = math.cos(a), math.sin(a)                    # ring in the x-y plane ...
        y, z = py * ct, py * st_                              # ... tilted about x ...
        x, z = px * cu - z * su, px * su + z * cu             # ... turned about y
        v = speed * R.uniform(0.97, 1.02)
        star = Star("star", s.x, s.y, s.z, s.vx * 0.3 + x * v, s.vy * 0.3 + y * v, z * v, 0.034,
                    life * R.uniform(0.95, 1.05), c)
        star.phase = a
        sim.add(star)


def _pattern(sim, s, rec):
    """Flat shape facing the viewer: pattern points (screen offsets, y down) become star velocities."""
    pts = rec["points"]
    r = max([math.hypot(px, py) for px, py in pts] + [1e-9])
    speed = 50.0 * rec.get("scale", 1.0)
    life = sim.rand.uniform(1.8, 2.2)
    for i, (px, py) in enumerate(pts):
        st = Star("star", s.x, s.y, s.z, s.vx * 0.2 + px / r * speed, s.vy * 0.2 - py / r * speed, 0.0, 0.03,
                  life, rec["color"], 1.0, 1.1)
        st.phase = i * 0.7
        sim.add(st)


def _message(sim, s, rec):
    """Stars burst out, glide into the text's dots (world metres around the burst point), hold, then fall.

    rec["points"]: [[u, v, r, g, b], ...] with u, v in metres from the text centre (v up); rec["hold"]: seconds."""
    R = sim.rand
    hold = rec.get("hold", 2.5)
    for i, p in enumerate(rec["points"]):
        u, v = p[0], p[1]
        a, e = R.uniform(0.0, 2.0 * math.pi), R.uniform(-1.0, 1.0)
        sp = R.uniform(18.0, 34.0)
        r = math.sqrt(1.0 - e * e)
        st = Star("star", s.x, s.y, s.z, r * math.cos(a) * sp + u * 0.8, e * sp + v * 0.8, r * math.sin(a) * sp,
                  0.06, 0.0, (p[2], p[3], p[4]), 0.9, 0.5)
        st.target = (s.x + u, s.y + v)
        st.glide = R.uniform(0.25, 0.45)
        st.hold = st.glide + 1.1 + hold
        st.life = st.hold + R.uniform(1.4, 2.0)
        st.nograv = True
        st.phase = i * 0.37
        st.trail, st.trail_color, st.trail_life = 0.8 * sim.quality, (p[2], p[3], p[4]), 0.35
        sim.add(st)
