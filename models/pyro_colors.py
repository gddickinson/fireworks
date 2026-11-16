"""Pyrotechnic star colours and how a burning star's colour and brightness change over its life (Qt-free).

Colours are the emitters used in real stars: strontium red, barium green, copper blue, strontium + copper purple,
sodium yellow/orange, calcium orange, charcoal gold (the orange-gold of willows and tails) and magnesium/titanium
white-silver.  `star_rgb` turns a star's age into a colour and intensity: a white-hot flash at ignition, the
emitter's colour while it burns, then a cooling orange-red ember that fades.  It is shared by the desktop renderer
(gui/real_painter.py); the web renderers carry a JavaScript copy (web/static/fw_palette.js).
"""
from __future__ import annotations

import math

PALETTE = {
    "red": (255, 38, 28), "green": (64, 255, 96), "blue": (52, 110, 255), "purple": (190, 70, 255),
    "yellow": (255, 226, 70), "orange": (255, 128, 30), "aqua": (60, 230, 255), "pink": (255, 90, 190),
    "gold": (255, 172, 68), "silver": (226, 232, 255), "white": (255, 250, 240),
}
SHOW_COLORS = ["red", "green", "blue", "purple", "yellow", "orange", "aqua", "pink", "gold", "silver"]
TAIL_GOLD = (255, 150, 52)     # charcoal sparks of rising shells, willows, palms
TAIL_SILVER = (220, 228, 255)  # titanium/aluminium glitter
EMBER = (255, 70, 12)


def pick_color(rand) -> tuple:
    return PALETTE[rand.choice(SHOW_COLORS)]


def _mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def star_rgb(star, time: float = 0.0, flashes: bool = True):
    """(r, g, b, intensity) of a star now. Intensity ~1 for a normal star, >1 for flashes; 0 when invisible."""
    if star.age < 0:
        return (0.0, 0.0, 0.0, 0.0)
    t = star.age / star.life if star.life > 0 else 1.0
    base = star.color
    if star.color2 is not None and t > star.change:
        base = star.color2
    kind = star.kind
    if kind == "pop":                                   # crackle: a tiny white flash
        return (255.0, 245.0, 225.0, 3.0 * (1.0 - t))
    if kind == "spark":                                 # tail spark: hot then cooling
        c = _mix(base, EMBER, _smooth(0.3, 1.0, t))
        i = (1.0 - t) * (1.0 - t) * star.bright
        if star.glitter and flashes:
            i *= 0.35 + 1.6 * (0.5 + 0.5 * math.sin(star.phase + star.age * 47.0)) ** 6
        return (c[0], c[1], c[2], i)
    if kind == "shell":                                 # the rising shell: a dim orange spark
        return (TAIL_GOLD[0], TAIL_GOLD[1], TAIL_GOLD[2], 0.9 * star.bright)
    c = _mix((255.0, 250.0, 240.0), base, _smooth(0.0, 0.12, t))
    c = _mix(c, EMBER, _smooth(0.78, 1.0, t))
    i = star.bright * (1.0 + 1.2 * (1.0 - _smooth(0.0, 0.08, t))) * (1.0 - _smooth(0.82, 1.0, t))
    if star.target is not None:                         # message letters: a subtle twinkle
        i *= 0.88 + 0.12 * math.sin(star.phase + star.age * 9.0)
    elif star.strobe > 0 and flashes:
        i *= 1.0 if (star.age + star.phase) % star.strobe < star.strobe * 0.35 else 0.05
    elif star.glitter and flashes:
        i *= 0.55 + 0.9 * (0.5 + 0.5 * math.sin(star.phase + star.age * 31.0)) ** 4
    else:
        i *= 0.9 + 0.1 * math.sin(star.phase + star.age * 23.0)   # gentle flicker of a burning star
    return (c[0], c[1], c[2], i)
