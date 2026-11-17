"""Seeded runs of the realistic engine (models/pyro.py, shell_types.py, director.py) for the JavaScript copy.

Same idea as web/reference.py: a mulberry32 `PyRand` replaces ``random``, so the JS copy (fw_pyro.js, fw_shells.js,
fw_director.js) consumes the same stream; fw_pyro.test.mjs and the Verify page replay these cases.  The realistic
engine takes its random source as an argument, so no module patching is needed.  Snapshots hold, per star kind, the
count and the sums of positions and velocities, plus the event counts so far.
"""
from __future__ import annotations

import math

from models.director import Director
from models.glyphs import glyph_points
from models.patterns import HeartPattern
from models.pyro import Sim
from models.shell_types import TYPES
from web.reference import PyRand

PYRO_CASES = [
    {"name": "finale", "seed": 11, "seconds": 46, "snap_every": 120, "mode": "finale"},
    {"name": "auto_mixed", "seed": 23, "seconds": 20, "snap_every": 120, "mode": "auto", "aspect": 0.5},
    {"name": "physical_lift", "seed": 29, "seconds": 12, "snap_every": 120, "mode": "auto", "lift": None},
    {"name": "every_type", "seed": 31, "seconds": 10, "snap_every": 60, "mode": "types"},
    {"name": "heart_pattern", "seed": 37, "seconds": 9, "snap_every": 60, "mode": "pattern",
     "gravity": 0.5, "height": 1.2, "stars": 0.6},
    {"name": "message", "seed": 41, "seconds": 12, "snap_every": 60, "mode": "message", "text": "HI 2026"},
    {"name": "message_show", "seed": 43, "seconds": 36, "snap_every": 120, "mode": "message", "text": "HELLO|2027",
     "opener": "short", "finale": False},
]
PYRO_BY_NAME = {c["name"]: c for c in PYRO_CASES}


def message_points(text: str, height_m: float = 40.0) -> list:
    """Dots of the 5 x 7 glyphs as [u, v, r, g, b] in metres around the text centre (v up), rainbow colours."""
    dots = []
    for i, ch in enumerate(text):
        dots += [(i * 6 + c, r) for c, r in glyph_points(ch)]
    width = len(text) * 6 - 1
    k = height_m / 7.0
    out = []
    for c, r in dots:
        hue = c / max(1, width)
        out.append([(c - (width - 1) / 2) * k, ((7 - 1) / 2 - r) * k,
                    255, int(120 + 135 * hue), int(255 - 200 * hue)])
    return out


def _snap(sim: Sim, counts: dict) -> dict:
    kinds = {}
    for s in sim.stars:
        kinds.setdefault(s.kind, []).append(s)
    return {"frame": sim.frame, "events": dict(counts), "kinds": {
        k: {"n": len(v), "x": math.fsum(s.x for s in v), "y": math.fsum(s.y for s in v),
            "z": math.fsum(s.z for s in v), "vx": math.fsum(s.vx for s in v), "vy": math.fsum(s.vy for s in v)}
        for k, v in sorted(kinds.items())}}


def run_pyro(case: dict) -> dict:
    rand = PyRand(case["seed"])
    sim = Sim(rand, aspect=case.get("aspect", 16 / 9))
    sim.gravity_scale = case.get("gravity", 1.0)
    sim.height_scale = case.get("height", 1.0)
    sim.star_scale = case.get("stars", 1.0)
    sim.lift_time = case.get("lift", 3.0)
    d = Director(rand)
    mode = case["mode"]
    if mode == "finale":
        d.start_finale(sim)
    elif mode == "pattern":
        d.pattern = HeartPattern()
    elif mode == "message":
        msgs = [{"points": message_points(t), "hold": 2.0} for t in case["text"].split("|")]
        duration = d.queue_messages(sim, msgs, case.get("opener", "off"), case.get("finale", False))
    elif mode == "types":
        d.auto = False
        for i, t in enumerate(TYPES + ["salute"]):
            sim.launch(d.recipe(t), -0.9 + i * 0.15, None, None, 0.0)
    if mode != "message":
        duration = None
    counts = {"launch": 0, "burst": 0, "crackle": 0}
    snaps = []
    steps = int(case["seconds"] * 60)
    for step in range(steps + 1):
        if step % case["snap_every"] == 0:
            snaps.append(_snap(sim, counts))
        d.step(sim)
        sim.step()
        for e in sim.events:
            counts[e[0]] += 1
    return {"case": case, "snapshots": snaps, "duration": duration}


def pyro_fixture() -> list:
    return [run_pyro(c) for c in PYRO_CASES]
