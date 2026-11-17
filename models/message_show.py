"""Message shows (Qt-free): an opening show that builds up, then the messages, then optionally the finale.
JavaScript copy: web/static/fw_message_show.js (same random order; checked by fw_pyro.test.mjs).

Timeline (seconds from the start, all launches; a shell bursts `lift` seconds after its launch):
  opener   single shells one by one, then matched pairs, then volleys across the sky, faster and faster;
  dark     a 1.5 s beat with nothing launched;
  message  the message shell; its letters hold for `hold` s. Nothing is launched that could burst while any
           letters are in the sky: shells launched before it are short-lived types that have burnt out before the
           letters settle, and the next shells are launched only when the letters are released;
  gap      between messages two light, low shells at the sides, then the next message;
  finale   optional, after the last message has fallen.
Cues are (time, type, x fraction of the half-width, height fraction, tilt) or (time, "message", message dict),
as for Director (models/director.py), which plays them.
"""
from __future__ import annotations

from models.director import finale_cues

OPENERS = {"off": None, "short": (3, 2, 1), "medium": (4, 4, 3), "long": (5, 7, 8)}  # singles, pairs, volleys
SHORT_TYPES = ("peony", "chrysanthemum", "ring", "crackle")         # burnt out within ~2.4 s of the burst
SINGLE_TYPES = ("peony", "chrysanthemum", "ring", "willow", "palm")
PAIR_TYPES = ("chrysanthemum", "crossette", "ring", "kamuro", "peony", "horsetail")
VOLLEY_TYPES = ("peony", "chrysanthemum", "crackle", "multibreak", "strobe", "ring", "willow")
GENTLE_OUT = ("strobe", "crackle", "multibreak")                  # left out for prefers-reduced-motion
DARK_BEAT = 1.5
SAFE_TAIL = 3.5    # cues this close to the end of the opener use SHORT_TYPES only


def _pick(R, types, gentle):
    if gentle:
        types = tuple(t for t in types if t not in GENTLE_OUT)
    return types[int(R.random() * len(types))]


def opener_cues(R, level: str, gentle: bool = False):
    """(cues, time of the last launch) of the opening show; ([], 0.0) for "off"."""
    spec = OPENERS.get(level)
    if spec is None:
        return [], 0.0
    ns, np_, nv = (3, 2, 0) if gentle else spec
    slots = []                                       # (time, kind, index) first; types once the end is known
    t = 0.3
    for i in range(ns):
        slots.append((t, "single", i))
        t += 1.3
    for i in range(np_):
        slots.append((t, "pair", i))
        t += 1.1
    for i in range(nv):
        slots.append((t, "volley", i))
        t += max(0.9, 1.4 - 0.1 * i)
    end = slots[-1][0]
    cues = []
    for when, kind, i in slots:
        tail = when > end - SAFE_TAIL
        if kind == "single":
            typ = _pick(R, SHORT_TYPES if tail else SINGLE_TYPES, gentle)
            x = (-1.0 if i % 2 == 0 else 1.0) * R.uniform(0.15, 0.55)
            cues.append((when, typ, x, R.uniform(0.5, 0.72), 0.0))
        elif kind == "pair":
            typ = _pick(R, SHORT_TYPES if tail else PAIR_TYPES, gentle)
            x, h = R.uniform(0.35, 0.8), R.uniform(0.45, 0.7)
            cues += [(when, typ, -x, h, 0.0), (when, typ, x, h, 0.0)]
        else:
            k = 3 + min(2, i)
            for j in range(k):
                typ = _pick(R, SHORT_TYPES if tail else VOLLEY_TYPES, gentle)
                x = -0.8 + 1.6 * j / (k - 1) + R.uniform(-0.08, 0.08)
                cues.append((when + 0.05 * j, typ, x, R.uniform(0.45, 0.75), 0.0))
    return cues, end + (0.05 * (2 + min(2, nv - 1)) if nv else 0.0)   # + spread of the last volley


def show_cues(R, messages: list, opener: str = "short", finale: bool = False, gentle: bool = False,
              lift: float = 3.0):
    """(cues sorted by time, duration in s) of a whole message show. lift: launch-to-burst time of a shell."""
    cues, last = opener_cues(R, opener, gentle)
    t = last + DARK_BEAT if cues else 0.3
    end = t
    for i, m in enumerate(messages):
        cues.append((t, "message", m))
        release = t + lift + 0.45 + 1.1 + m.get("hold", 2.5)   # burst, glide (<= 0.45 + 1.1 s), hold
        if i < len(messages) - 1:
            cues.append((release, _pick(R, SHORT_TYPES, gentle), -0.85, 0.4, 0.0))
            cues.append((release + 0.8, _pick(R, SHORT_TYPES, gentle), 0.85, 0.4, 0.0))
            t = release + 2.5
        end = release + 2.0                                     # the letters have fallen and faded
    if finale and messages:
        fc = finale_cues(R)
        cues += [(end + c[0],) + tuple(c[1:]) for c in fc]
        end += fc[-1][0] + lift + 4.0
    elif not messages:
        end = t
    return sorted(cues, key=lambda c: c[0]), end
