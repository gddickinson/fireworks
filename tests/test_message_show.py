"""Message shows (models/message_show.py via Director.queue_messages): opener lengths, order, nothing bursting
while letters hold, determinism. Qt-free; the JS copy is checked by web/static/fw_message_show.test.mjs."""
import random

from models.director import Director
from models.message_show import show_cues
from models.pyro import DT, Sim
from web.reference_pyro import message_points


def _msgs(*texts):
    return [{"points": message_points(t), "hold": 3.0} for t in texts]


def test_opener_lengths_and_dark_beat():
    for level, want in (("short", 8), ("medium", 15), ("long", 25)):
        cues, _ = show_cues(random.Random(1), _msgs("HI"), level)
        m = next(c for c in cues if c[1] == "message")
        before = [c[0] for c in cues if c[0] < m[0]]
        assert abs(m[0] - want) < 1.5 and m[0] - max(before) >= 1.4
    cues, _ = show_cues(random.Random(1), _msgs("HI"), "off")
    assert cues[0][1] == "message"


def _play(seed, opener, lift):
    R = random.Random(seed)
    sim, d = Sim(R), Director(R)
    sim.lift_time = lift
    dur = d.queue_messages(sim, _msgs("HAPPY", "2027"), opener, False)
    held_bursts, bursts, held = 0, [], 0
    for _ in range(int((dur + 3) / DT)):
        d.step(sim)
        sim.step()
        hold = any(s.target is not None and s.glide + 1.1 <= s.age < s.hold for s in sim.stars)
        held += hold
        for e in sim.events:
            if e[0] == "burst":
                bursts.append(round(e[1], 6))
                held_bursts += hold
    return held, held_bursts, bursts, d.mode


def test_nothing_bursts_while_letters_hold_and_runs_are_deterministic():
    for opener, lift in (("short", 3.0), ("long", 2.0), ("medium", None)):
        held, held_bursts, bursts, mode = _play(4, opener, lift)
        assert held > 200 and held_bursts == 0 and len(bursts) > 5 and mode == "auto", opener
    assert _play(7, "short", 3.0)[2] == _play(7, "short", 3.0)[2]
