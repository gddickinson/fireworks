"""Launch schedule (Qt-free): random auto-launch and a choreographed finale.  JavaScript copy: web/static/fw_director.js.

`Director.step(sim)` is called once per frame before `Sim.step()`.  Modes:
  * auto: shells at random times (`rate` per second on average), type from `shell_type` ("mixed" draws one from
    shell_types.TYPES), colour `color` (None: a random pyrotechnic colour per shell);
  * finale: a ~40 s programme (opening pairs, a fan of palms, crossettes and rings, a willow/kamuro curtain, a rapid
    crescendo and a salute barrage), after which it returns to auto.  `finale_cues(rand)` builds the cue list;
  * messages: `queue_messages()` plays an optional opening show, the message shells (text points from the front
    end) and optionally the finale (timeline in models/message_show.py).
"""
from __future__ import annotations

from models.shell_types import TYPES, make_recipe

FINALE_SECONDS = 42.0


def finale_cues(rand) -> list:
    """[(time s, type, x fraction of the half-width or None, height fraction or None, tilt), ...] sorted by time."""
    R = rand
    cues = []
    t = 0.5
    for i in range(3):                                # opening: matched pairs left and right
        typ = ("peony", "chrysanthemum", "ring")[i]
        x = R.uniform(0.35, 0.75)
        cues += [(t, typ, -x, 0.6, 0.0), (t, typ, x, 0.6, 0.0)]
        t += 1.8
    t += 0.6
    for i in range(5):                                # a fan of palms from the centre
        cues.append((t + i * 0.25, "palm", 0.0, 0.7, (i - 2) * 0.12))
    t += 4.0
    for i in range(8):                                # crossettes and rings
        cues.append((t + i * 0.5, "crossette" if i % 2 == 0 else "ring", R.uniform(-0.8, 0.8), None, 0.0))
    t += 5.0
    for i in range(6):                                # a curtain of willows and kamuro across the sky
        cues.append((t + i * 0.12, "willow" if i % 2 == 0 else "kamuro", -0.8 + i * 0.32, 0.72, 0.0))
    t += 4.5
    for i in range(4):
        cues.append((t + i * 0.6, "strobe", R.uniform(-0.7, 0.7), None, 0.0))
    t += 3.0
    n = 26                                            # crescendo: faster and faster
    for i in range(n):
        typ = ("chrysanthemum", "peony", "crackle", "multibreak", "horsetail")[int(R.random() * 5)]
        cues.append((t, typ, R.uniform(-0.9, 0.9), None, 0.0))
        t += 0.45 - 0.3 * i / n
    t += 0.4
    for i in range(10):                               # salutes and a final gold canopy
        cues.append((t + i * 0.15, "salute", R.uniform(-0.8, 0.8), R.uniform(0.5, 0.8), 0.0))
    for i in range(3):
        cues.append((t + 1.2 + i * 0.1, "kamuro", -0.5 + i * 0.5, 0.78, 0.0))
    return sorted(cues, key=lambda c: c[0])


class Director:
    def __init__(self, rand):
        self.rand = rand
        self.mode = "auto"
        self.auto = True
        self.rate = 1.1
        self.shell_type = "mixed"
        self.color = None
        self.pattern = None          # an object with get_points(x, y) (models/patterns.py) or None
        self.pattern_scale = 1.0
        self.cues: list = []
        self.t0 = 0.0
        self.until = 0.0             # programme time before auto launching may resume

    def recipe(self, type_=None) -> dict:
        R = self.rand
        if type_ is None:
            if self.pattern is not None:
                type_ = "pattern"
            elif self.shell_type == "mixed":
                type_ = TYPES[int(R.random() * len(TYPES))]
            else:
                type_ = self.shell_type
        rec = make_recipe(R, "peony" if type_ == "pattern" else type_, self.color)
        if type_ == "pattern":
            rec["type"] = "pattern"
            rec["points"] = [list(p) for p in self.pattern.get_points(0.0, 0.0)]
            rec["scale"] = self.pattern_scale
        return rec

    def start_finale(self, sim) -> None:
        self.mode = "finale"
        self.t0 = sim.time
        self.cues = finale_cues(self.rand)
        self.until = 0.0

    def queue_messages(self, sim, messages: list, opener: str = "off", finale: bool = False,
                       gentle: bool = False) -> float:
        """messages: [{"points": [[u, v, r, g, b], ...], "hold": s}, ...], shown one after another, after an opening
        show ("off", "short", "medium", "long"; models/message_show.py) and optionally before the finale.
        Returns the show's duration in seconds."""
        from models.message_show import show_cues  # late: message_show imports this module
        self.mode = "finale"
        self.t0 = sim.time
        lift = sim.lift_time if sim.lift_time is not None else 6.0
        self.cues, duration = show_cues(self.rand, messages, opener, finale, gentle, lift)
        self.until = duration         # no random shells while letters are in the sky
        return duration

    def step(self, sim) -> None:
        if self.mode == "finale":
            now = sim.time - self.t0
            while self.cues and self.cues[0][0] <= now:
                cue = self.cues.pop(0)
                if cue[1] == "message":
                    m = cue[2]
                    rec = {"type": "message", "color": (255, 240, 220), "color2": None, "pistil": None, "size": 1.0,
                           "points": m["points"], "hold": m.get("hold", 2.5)}
                    sim.launch(rec, 0.0, 450.0, m.get("height", 0.62), 0.0)
                else:
                    _, typ, x, h, tilt = cue
                    sim.launch(self.recipe(typ), x, None, h, tilt)
            if not self.cues and now > max(1.0, self.until):
                self.mode = "auto"
            return
        if self.auto and self.rand.random() < self.rate / 60.0:
            sim.launch(self.recipe())
