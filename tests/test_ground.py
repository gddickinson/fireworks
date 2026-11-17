"""Ground devices of the realistic engine (models/ground_effects.py, Sim.ground, Director.ground). Qt-free."""
import random

import pytest

from models.director import Director, finale_cues, ground_cues
from models.ground_effects import AUTO_DEVICES, DEVICES
from models.pyro import DT, Sim
from web.reference import PyRand


def _sim(seed=1):
    s = Sim(random.Random(seed))
    s.wind = 0.0
    return s


def _run(sim, seconds, watch=None):
    """Step for `seconds`; returns (events by name, max height of ground stars, all ground stars seen)."""
    counts, top, seen = {}, 0.0, set()
    for _ in range(int(seconds * 60)):
        sim.step()
        for e in sim.events:
            counts[e[0]] = counts.get(e[0], 0) + 1
        for s in sim.stars:
            if s.ground:
                top = max(top, s.y)
                seen.add(s)
                if watch:
                    watch(s)
    return counts, top, seen


def test_gerb_sprays_a_fountain_for_its_duration():
    sim = _sim()
    e = sim.ground("gerb", 0.0, 200.0, {"duration": 5.0, "color": "gold", "glitter": False})
    assert sim.emitters == [e]

    def inside(s):
        assert -0.5 < s.y < 14.0 and abs(s.x - e.x) < 6.0 and abs(s.z - 200.0) < 6.0

    counts, top, seen = _run(sim, 5.1, inside)
    assert counts.get("ground") == 1
    assert 6.0 < top < 14.0                           # a fountain 8-10 m high
    assert 800 < len(seen) < 1300                      # ~240 sparks/s, ramped in and out
    assert all(s.kind == "spark" for s in seen)
    assert not sim.emitters                            # finished after its 5 s
    _run(sim, 2.0)
    assert not any(s.ground for s in sim.stars)       # the last sparks burnt out or fell to the ground


def test_roman_candle_fires_single_stars_one_by_one():
    sim = _sim(2)
    sim.ground("candle", -0.2, 220.0, {"shots": 8})
    shots = []
    for i in range(int(4.0 * 60)):
        sim.step()
        shots += [i * DT for e in sim.events if e[0] == "launch"]
    assert len(shots) == 8 and all(abs(b - a - 0.45) < 2 * DT for a, b in zip(shots, shots[1:]))
    sim = _sim(2)
    sim.ground("candle", 0.0, 220.0, {"shots": 1})
    _, top, seen = _run(sim, 3.0)
    assert 15.0 < top < 26.0                          # a roman candle star burns out near its ~20 m apex
    assert len([s for s in seen if s.kind == "star"]) == 1


def test_mine_bursts_from_the_ground_in_a_cone():
    sim = _sim(3)
    e = sim.ground("mine", 0.3, 200.0)
    sim.step()
    assert any(ev[0] == "burst" and ev[2] < 3.0 for ev in sim.events)
    stars = [s for s in sim.stars if s.kind == "star"]
    assert len(stars) == sim.count(60) + 6
    assert all(s.vy > 0.9 * abs(s.vx) for s in stars)  # upward, within ~20 degrees of the vertical
    assert not sim.emitters
    _, top, _ = _run(sim, 2.5)
    assert 22.0 < top < 45.0 and abs(e.x - 0.3 * sim.x_max(200.0)) < 1e-9


def test_cake_fires_a_fan_of_small_shells_that_burst():
    sim = _sim(4)
    sim.ground("cake", 0.0, 220.0, {"shots": 16, "style": "peony"})
    xs, heights = [], []
    for _ in range(int(8 * 60)):
        sim.step()
        for ev in sim.events:
            if ev[0] == "burst":
                xs.append(ev[1])
                heights.append(ev[2])
    assert len(xs) == 16
    assert 35.0 < min(heights) and max(heights) < 70.0
    assert min(xs) < -15.0 and max(xs) > 15.0         # a fan both ways


def test_niagara_drops_a_curtain_from_the_bridge():
    sim = _sim(5)
    e = sim.ground("niagara", 0.0, 210.0, {"height": 20.0, "width": 0.5, "duration": 10.0})

    def below_bridge(s):
        assert -0.5 < s.y <= 20.3 and abs(s.x) < e.width / 2 + 4.0

    counts, top, seen = _run(sim, 6.0, below_bridge)
    assert counts["ground"] == 1
    lowest = min(s.y for s in sim.stars if s.ground)
    assert lowest < 8.0                               # falling at ~5.7 m/s for up to 3.4 s
    assert sim.emitters                               # still running at 6 s
    _run(sim, 8.0)
    assert not sim.emitters and not any(s.ground for s in sim.stars)


@pytest.mark.parametrize("kind", DEVICES)
def test_devices_are_deterministic(kind):
    def run():
        sim = Sim(PyRand(9))
        sim.ground(kind)
        _run(sim, 1.5)
        return [(s.kind, s.x, s.y, s.vx) for s in sim.stars]
    a = run()
    assert a and a == run()


def test_unknown_device_is_refused():
    with pytest.raises(ValueError):
        _sim().ground("volcano")


def test_director_ground_is_off_by_default_and_adds_devices_when_on():
    assert Director(PyRand(1)).ground is False
    sim = Sim(PyRand(7))
    d = Director(sim.rand)
    d.ground, d.rate = True, 20.0
    kinds, shells = [], 0
    orig = sim.ground
    sim.ground = lambda kind, *a: kinds.append(kind) or orig(kind, *a)
    for _ in range(60 * 10):
        d.step(sim)
        sim.step()
        shells += sum(1 for e in sim.events if e[0] == "launch" and e[3] not in ("candle", "cake"))
    assert set(kinds) <= set(AUTO_DEVICES) and 10 <= len(kinds) <= 50   # ~15 % of ~200 launches
    assert shells > 4 * len(kinds)


def test_finale_ground_segment():
    R = PyRand(3)
    base = finale_cues(PyRand(3))
    d = Director(R)
    d.ground, d.niagara_height = True, 22.0
    d.start_finale(Sim(R))
    ground = [c for c in d.cues if c[1] == "ground"]
    assert [c for c in d.cues if c[1] != "ground"] == base   # the shells' programme is unchanged
    assert {c[2] for c in ground} == {"candle", "niagara", "gerb", "mine", "cake"}
    assert all(d.cues[i][0] <= d.cues[i + 1][0] for i in range(len(d.cues) - 1))
    assert not any(c[2] == "niagara" for c in ground_cues(PyRand(1)))   # no bridge, no niagara


def test_message_shows_have_no_ground_devices():
    from web.reference_pyro import message_points
    sim = Sim(PyRand(5))
    d = Director(sim.rand)
    d.ground = True
    d.queue_messages(sim, [{"points": message_points("HI"), "hold": 2.0}], "short", True)
    assert not any(c[1] == "ground" for c in d.cues)


def test_ground_stars_die_below_the_ground():
    sim = _sim(6)
    sim.ground("candle", 0.0, 200.0, {"shots": 1, "tilt": 1.2})   # nearly horizontal: comes down quickly
    _run(sim, 6.0)
    assert not any(s.ground for s in sim.stars)
