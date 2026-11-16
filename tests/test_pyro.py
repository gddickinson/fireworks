"""The realistic engine (models/pyro.py, shell_types.py, director.py, pyro_colors.py): physics and shell behaviour.
Qt-free. The JavaScript copy is checked against seeded runs of these modules by web/static/fw_pyro.test.mjs."""
import math
import random

from models.director import Director, finale_cues
from models.pyro import DT, G, Sim, sphere_dirs
from models.pyro_colors import star_rgb
from models.shell_types import TYPES


def _sim(seed=1):
    s = Sim(random.Random(seed))
    s.wind = 0.0
    return s, Director(s.rand)


def _burst_of(sim, d, typ):
    sim.launch(d.recipe(typ), 0.0, 500.0, 0.6)
    for _ in range(1200):
        sim.step()
        if any(e[0] == "burst" for e in sim.events):
            return
    raise AssertionError("no burst")


def test_shell_bursts_at_requested_height():
    sim, d = _sim()
    sh = sim.launch(d.recipe("peony"), 0.0, 500.0, 0.6)
    want = 0.6 * sim.y_top(500.0)
    while sh in sim.stars:
        sim.step()
    assert abs(sh.y - want) < 0.03 * want
    assert 3.0 < sim.time < 6.0  # a real 150 m shell rises for about 4 s


def test_drag_slows_stars_to_terminal_velocity():
    sim, d = _sim(2)
    _burst_of(sim, d, "peony")
    v0 = max(math.hypot(s.vx, s.vy, s.vz) for s in sim.stars if s.kind == "star")
    for _ in range(90):
        sim.step()
    stars = [s for s in sim.stars if s.kind == "star"]
    v = [math.hypot(s.vx, s.vy, s.vz) for s in stars]
    vt = math.sqrt(G / stars[0].k)
    assert v0 > 45 and max(v) < 1.2 * vt
    assert sum(s.vy for s in stars) < 0  # drooping


def test_every_type_bursts_and_makes_light():
    for typ in TYPES + ["salute"]:
        sim, d = _sim(3)
        _burst_of(sim, d, typ)
        for _ in range(30):
            sim.step()
        lit = [star_rgb(s)[3] for s in sim.stars if s.kind != "shell"]
        assert lit and max(lit) > 0.3, typ


def test_crossette_splits_and_crackle_pops():
    sim, d = _sim(4)
    _burst_of(sim, d, "crossette")
    n0 = sum(s.kind == "star" for s in sim.stars)
    for _ in range(80):
        sim.step()
    assert sum(s.kind == "star" for s in sim.stars) > 2 * n0
    sim, d = _sim(5)
    _burst_of(sim, d, "crackle")
    pops = 0
    for _ in range(150):
        sim.step()
        pops += sum(s.kind == "pop" for s in sim.stars)
    assert pops > 0


def test_message_stars_hold_their_letters():
    sim, d = _sim(6)
    pts = [[-10.0, 0.0, 255, 0, 0], [10.0, 5.0, 0, 255, 0]]
    d.queue_messages(sim, [{"points": pts, "hold": 2.0}])
    for _ in range(int(9 / DT)):
        d.step(sim)
        sim.step()
        msg = [s for s in sim.stars if s.target is not None]
        if msg and msg[0].age > msg[0].glide + 1.5:
            break
    for s in msg:
        assert math.hypot(s.x - s.target[0], s.y - s.target[1]) < 0.5


def test_finale_runs_and_returns_to_auto():
    sim, d = _sim(7)
    d.start_finale(sim)
    bursts = 0
    for _ in range(int(45 / DT)):
        d.step(sim)
        sim.step()
        bursts += sum(e[0] == "burst" for e in sim.events)
    assert d.mode == "auto" and bursts > 60
    assert finale_cues(random.Random(1))[-1][1] == "kamuro"


def test_sphere_dirs_even():
    ds = sphere_dirs(200, 1.0)
    assert all(abs(math.sqrt(x * x + y * y + z * z) - 1) < 1e-12 for x, y, z in ds)
    assert abs(sum(x for x, _, _ in ds)) < 2 and abs(sum(y for _, y, _ in ds)) < 1e-9
