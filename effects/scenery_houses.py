"""Small lit structures and objects of the realistic scenery: a QPainter port of web/static/fw_scenery_houses.js.

Cottages (snowy roofs, chimneys, warm windows lighting the snow below), a village church with a spire, waterfront
town houses, a floodlit hilltop castle, boats with riding lights, a lit jetty, a glowing tent, wind-turbine towers
and a crowd watching the show.  Colour goes to `c`, material (albedo) to `m`; chimney / turbine positions (scenery
px) are appended to S.chimneys / S.turbines for the scene plug-ins (effects/scene_fx.py).  Same prng draws as the web.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QLinearGradient, QRadialGradient

from effects.scenery_city import glow
from effects.scenery_draw import both, ellipse, fill, fill_rect, path, poly, stroke, upper_half
from effects.scenery_noise import prng
from effects.scenery_parts import mat, rgb, vgrad
from effects.scenery_sky import tone

WARM = (255, 190, 110)


def _rect(x, y, w, h):
    return lambda k, col: fill_rect(k, x, y, w, h, col)


def _poly(pts):
    shape = poly(pts)
    return lambda k, col: fill(k, shape, col)


def lit_window(c, x, y, w, h, rnd, spill=0.0, col=WARM) -> None:
    """A lit window with a soft halo; `spill` adds a pool of light on the ground (snow) below it."""
    k = 0.75 + rnd() * 0.25
    fill_rect(c, x, y, w, h, rgb(*(v * k for v in col), 0.95))
    fill_rect(c, x + w / 2 - w * 0.06, y, w * 0.12, h, rgb(40, 25, 15, 0.7))
    fill_rect(c, x, y + h / 2 - h * 0.05, w, h * 0.1, rgb(40, 25, 15, 0.7))
    glow(c, x + w / 2, y + h / 2, max(w, h) * 1.6, col, 0.22, 0.3)
    if spill:
        g = QRadialGradient(QPointF(x + w / 2, y + h + spill * 0.3), spill)
        g.setColorAt(0, rgb(*col, 0.22))
        g.setColorAt(1, rgb(*col, 0))
        fill_rect(c, x + w / 2 - spill, y + h, 2 * spill, spill * 1.3, g)


def cottage(S, c, m, x, base, w, h, rnd, sc, snow=False, spill=0.0, haze=0.3) -> None:
    """Cottage standing on `base`: walls, steep roof (snow-covered when snow), a chimney, lit windows."""
    wall = tone(S, (16, 14, 16), haze)
    roof_c = tone(S, (72, 80, 104) if snow else (12, 12, 16), haze)
    rh, eave = h * (0.55 + rnd() * 0.3), w * 0.08
    both(c, m, rgb(*wall), 0.35, _rect(x, base - h, w, h))
    both(c, m, rgb(*roof_c), 0.8 if snow else 0.3,
         _poly([(x - eave, base - h), (x + w / 2, base - h - rh), (x + w + eave, base - h)]))
    if snow:                                                    # snow edge over the eaves, darker underside
        fill_rect(c, x - eave, base - h - 1.5 * sc, w + 2 * eave, 2.2 * sc, rgb(*(v * 1.15 for v in roof_c)))
        fill(c, poly([(x + w / 2, base - h - rh), (x + w + eave, base - h), (x + w / 2 + w * 0.12, base - h)]),
             rgb(*(v * 0.55 for v in roof_c)))
    cx, cw = x + w * (0.2 + rnd() * 0.55), w * 0.11
    ctop = base - h - rh * (0.55 + rnd() * 0.25) - 6 * sc
    both(c, m, rgb(*wall), 0.35, _rect(cx, ctop, cw, base - h - ctop - rh * 0.15))
    if snow:
        fill_rect(c, cx - 0.6 * sc, ctop - 1.4 * sc, cw + 1.2 * sc, 1.8 * sc, rgb(*roof_c))
    S.chimneys.append((cx + cw / 2, ctop - 1.5 * sc, cw))
    n = 2 + int(rnd() * 2) if w > 30 * sc else 1
    ww, wh = min(w * 0.16, 6 * sc), min(h * 0.38, 7 * sc)
    for i in range(n):
        if rnd() < 0.2:
            continue
        lit_window(c, x + w * (i + 0.5) / n - ww / 2, base - h * 0.62, ww, wh, rnd, spill)
    if rnd() < 0.5:                                             # attic light
        lit_window(c, x + w / 2 - ww * 0.35, base - h - rh * 0.55, ww * 0.7, wh * 0.7, rnd)


def church(S, c, m, x, base, sc, rnd, snow=False, haze=0.3) -> float:
    """Village church: nave with tall lit windows, a square tower with a spire, a faintly lit clock face."""
    wall = tone(S, (18, 16, 18), haze)
    roof_c = tone(S, (72, 80, 104) if snow else (12, 12, 16), haze)
    nw, nh, tw, th, sh = 70 * sc, 26 * sc, 16 * sc, 58 * sc, 52 * sc
    tx = x - tw
    both(c, m, rgb(*wall), 0.4, _rect(x, base - nh, nw, nh))
    both(c, m, rgb(*roof_c), 0.8 if snow else 0.3,
         _poly([(x - 2 * sc, base - nh), (x + 6 * sc, base - nh - 18 * sc), (x + nw - 6 * sc, base - nh - 18 * sc),
                (x + nw + 2 * sc, base - nh)]))
    for i in range(4):                                          # tall arched windows, warm
        wx, wy = x + 10 * sc + i * 15 * sc, base - nh + 6 * sc
        arch = path()
        arch.moveTo(wx, wy + 14 * sc)
        arch.lineTo(wx, wy + 2.5 * sc)
        upper_half(arch, wx + 2.5 * sc, wy + 2.5 * sc, 2.5 * sc, 2.5 * sc)
        arch.lineTo(wx + 5 * sc, wy + 14 * sc)
        arch.closeSubpath()
        fill(c, arch, rgb(255, 180, 100, 0.85))
        glow(c, wx + 2.5 * sc, wy + 8 * sc, 12 * sc, (255, 170, 90), 0.15)
    both(c, m, rgb(*wall), 0.4, _rect(tx, base - th, tw, th))
    both(c, m, rgb(*(v * 0.8 for v in roof_c)), 0.4,
         _poly([(tx - 1.5 * sc, base - th), (tx + tw / 2, base - th - sh), (tx + tw + 1.5 * sc, base - th)]))
    fill_rect(c, tx, base - th, tw, th, vgrad(base - th - sh, base, [(0, rgb(255, 210, 160, 0)),
                                                                   (1, rgb(255, 210, 160, 0.18))]))
    fill(c, ellipse(path(), tx + tw / 2, base - th + 10 * sc, 3.5 * sc, 3.5 * sc), rgb(255, 230, 180, 0.5))
    fill_rect(c, tx + tw / 2 - 2 * sc, base - th + 20 * sc, 4 * sc, 8 * sc, rgb(255, 170, 90, 0.8))
    cross = path()                                              # cross on the spire
    cross.moveTo(tx + tw / 2, base - th - sh)
    cross.lineTo(tx + tw / 2, base - th - sh - 7 * sc)
    cross.moveTo(tx + tw / 2 - 2.5 * sc, base - th - sh - 5 * sc)
    cross.lineTo(tx + tw / 2 + 2.5 * sc, base - th - sh - 5 * sc)
    stroke(c, cross, rgb(*wall), 1 * sc)
    return base - th - sh


def town_row(S, c, m, x0, x1, base, sc, rnd, haze=0.4) -> None:
    """Row of waterfront town houses (gabled, 2-4 floors, lit windows) from x0 to x1 standing on `base`."""
    x = x0
    while x < x1:
        w, floors = (14 + rnd() * 16) * sc, 2 + int(rnd() * 3)
        fh = 7.5 * sc
        h = floors * fh + 3 * sc
        col = tone(S, (14 + rnd() * 8, 13 + rnd() * 6, 16 + rnd() * 6), haze)
        gable = rnd() < 0.6
        roof = _poly([(x, base - h), (x + w / 2, base - h - w * 0.45), (x + w, base - h)]) if gable \
            else _rect(x, base - h - 2 * sc, w, 2 * sc)
        both(c, m, rgb(*col), 0.35, lambda k, cl, x=x, h=h, w=w, roof=roof: (fill_rect(k, x, base - h, w, h, cl),
                                                                            roof(k, cl)))
        for f in range(floors):
            for i in range(max(1, int(w / (6 * sc)))):
                if rnd() > 0.38:
                    continue
                wc = WARM if rnd() < 0.85 else (200, 220, 255)
                fill_rect(c, x + 2 * sc + i * 6 * sc, base - h + 3 * sc + f * fh, 2.6 * sc, 3.6 * sc,
                          rgb(*wc, 0.6 + rnd() * 0.35))
        x += w + (2 * sc if rnd() < 0.15 else 0)


def castle(S, c, m, cx, base, sc, rnd) -> None:
    """Floodlit castle centred at cx on `base`: curtain wall with crenellations, round towers with conical roofs,
    a tall keep, lit windows; floodlights from below warm the stone at the foot."""
    foot = tone(S, (62, 50, 44), 0.2)

    def stone(y0, y1):
        return vgrad(y0, y1, [(0, rgb(*foot)), (1, rgb(170, 128, 80))])

    roof_c = rgb(*tone(S, (16, 16, 24), 0.2))

    def block(x, y, w, h, crenel=True):
        both(c, m, stone(y, y + h), 0.6, _rect(x, y, w, h))
        if crenel:
            i = 0
            while i < w / (4 * sc) - 1:
                both(c, m, stone(y - 3 * sc, y + h), 0.6, _rect(x + i * 4 * sc, y - 3 * sc, 4 * sc, 3 * sc))
                i += 2

    def tower(x, w, h, cone):
        block(x, base - h, w, h, cone == 0)
        if cone:
            both(c, m, roof_c, 0.25, _poly([(x - 2 * sc, base - h), (x + w / 2, base - h - cone),
                                            (x + w + 2 * sc, base - h)]))
            stroke(c, poly([(x + w / 2, base - h - cone), (x + w / 2, base - h - cone - 6 * sc)], close=False),
                   rgb(20, 20, 28), 0.8 * sc)
        for i in range(3):
            if rnd() < 0.55:
                lit_window(c, x + w / 2 - 1.4 * sc, base - h + (8 + i * 14) * sc, 2.8 * sc, 5 * sc, rnd)

    W = 230 * sc
    block(cx - W / 2, base - 42 * sc, W, 42 * sc)               # curtain wall
    for i in range(9):                                          # arrow slits
        fill_rect(c, cx - W / 2 + (12 + i * 25) * sc, base - 30 * sc, 2 * sc, 6 * sc, rgb(30, 22, 18, 0.6))
    tower(cx - W / 2 - 12 * sc, 24 * sc, 70 * sc, 34 * sc)
    tower(cx + W / 2 - 12 * sc, 24 * sc, 64 * sc, 30 * sc)
    tower(cx - 70 * sc, 20 * sc, 92 * sc, 30 * sc)
    block(cx - 30 * sc, base - 125 * sc, 56 * sc, 83 * sc)      # keep
    tower(cx + 18 * sc, 16 * sc, 150 * sc, 36 * sc)             # slender watch tower beside the keep
    tower(cx + 60 * sc, 22 * sc, 84 * sc, 0)
    for f in range(3):
        for i in range(4):
            if rnd() < 0.5:
                lit_window(c, cx - 24 * sc + i * 13 * sc, base - 112 * sc + f * 22 * sc, 3.2 * sc, 6 * sc, rnd)
    fill_rect(c, cx - 7 * sc, base - 12 * sc, 18 * sc, 12 * sc, rgb(70, 40, 25))   # gate
    gate = upper_half(path(), cx + 2 * sc, base - 12 * sc, 9 * sc, 9 * sc)
    gate.closeSubpath()
    fill(c, gate, rgb(70, 40, 25))
    glow(c, cx + 2 * sc, base - 8 * sc, 22 * sc, (255, 170, 90), 0.25)
    glow(c, cx, base - 60 * sc, W * 0.9, (255, 170, 100), 0.07, 0.3)   # floodlight haze around the walls


def boat(k, x, y, ln, sc, rnd, sail=True, colour=(12, 13, 18), lights=True) -> tuple:
    """Boat (side view, facing right) on the waterline y: hull, cabin, mast (sailing) and riding lights.
    Returns the masthead light's offset (dx, dy)."""
    h = ln * 0.16
    hull = path()
    hull.moveTo(x - ln / 2, y - h)
    hull.lineTo(x + ln / 2 + ln * 0.06, y - h * 1.15)
    hull.quadTo(x + ln * 0.42, y + h * 0.2, x + ln * 0.25, y + h * 0.25)
    hull.lineTo(x - ln * 0.42, y + h * 0.2)
    hull.closeSubpath()
    fill(k, hull, rgb(*colour))
    fill_rect(k, x - ln / 2, y - h * 1.05, ln * 1.04, h * 0.18, rgb(*(min(255, v * 1.8 + 20) for v in colour)))
    fill_rect(k, x - ln * 0.2, y - h * 1.9, ln * 0.32, h * 0.95, rgb(*(v * 1.4 for v in colour)))   # cabin
    top = (0.0, -h * 1.9)
    if sail:
        mh = ln * (0.9 + rnd() * 0.4)
        fill_rect(k, x - 0.5 * sc, y - h - mh, 1 * sc, mh, rgb(*(v * 1.8 for v in colour)))
        stays = path()
        stays.moveTo(x, y - h - mh)
        stays.lineTo(x + ln * 0.5, y - h)
        stays.moveTo(x, y - h - mh)
        stays.lineTo(x - ln * 0.48, y - h)
        stroke(k, stays, rgb(*(v * 1.8 for v in colour)), 0.5 * sc)
        top = (0.0, -h - mh)
    if lights:
        fill(k, ellipse(path(), x + top[0], y + top[1], 1.1 * sc, 1.1 * sc), rgb(255, 245, 220))
        glow(k, x + top[0], y + top[1], 6 * sc, (255, 240, 210), 0.35)
        fill_rect(k, x - ln * 0.15, y - h * 1.6, ln * 0.06, h * 0.4, rgb(255, 200, 130, 0.85))
        fill_rect(k, x, y - h * 1.6, ln * 0.06, h * 0.4, rgb(255, 200, 130, 0.85))
    return top


def jetty(S, c, m, x0, x1, y, sc, rnd) -> list:
    """Jetty on piles from x0 to x1 at deck height y, with lamp posts; returns the lamp positions."""
    col, lamps = rgb(*tone(S, (10, 10, 14), 0.3)), []

    def deck(k, cl):
        fill_rect(k, x0, y - 3 * sc, x1 - x0, 4 * sc, cl)
        x = x0
        while x < x1:
            fill_rect(k, x, y, 1.6 * sc, 7 * sc, cl)
            x += 9 * sc
    both(c, m, col, 0.3, deck)
    fill_rect(c, x0, y - 3 * sc, x1 - x0, 0.8 * sc, rgb(90, 80, 70, 0.3))   # lamp-lit plank edge
    x = x0 + 12 * sc
    while x < x1:
        both(c, m, col, 0.3, _rect(x - 0.6 * sc, y - 22 * sc, 1.2 * sc, 19 * sc))
        fill(c, ellipse(path(), x, y - 23 * sc, 1.6 * sc, 1.6 * sc), rgb(255, 215, 150))
        glow(c, x, y - 23 * sc, 14 * sc, (255, 180, 100), 0.45)
        glow(c, x, y - 2 * sc, 10 * sc, (255, 180, 100), 0.15)  # light pool on the planks
        lamps.append((x, y - 23 * sc))
        x += (34 + rnd() * 8) * sc
    return lamps


def tent(c, m, x, base, sc) -> None:
    """Small tent glowing from a lantern inside, with a pool of light on the sand."""
    w, h = 26 * sc, 16 * sc
    glow(c, x, base, 45 * sc, (255, 150, 70), 0.18, 0.2)
    g = QLinearGradient(x, base - h, x, base)
    g.setColorAt(0, rgb(150, 80, 40))
    g.setColorAt(1, rgb(240, 140, 60))
    shape = poly([(x - w / 2, base), (x, base - h), (x + w / 2, base)])
    fill(c, shape, g)
    fill(m, shape, mat(0.5))
    fill(c, poly([(x - 3 * sc, base), (x, base - h * 0.55), (x + 3 * sc, base)]), rgb(255, 210, 140))
    stroke(c, poly([(x, base - h), (x, base - h - 4 * sc)], close=False), rgb(30, 20, 18), 0.8 * sc)


def turbine(S, c, m, x, base, h, sc) -> None:
    """Wind-turbine tower and nacelle (blades animated by effects/scene_fx.py); hub appended to S.turbines."""
    col = rgb(*tone(S, (44, 48, 64), 0.8))
    tower = poly([(x - 1.6 * sc, base), (x - 0.7 * sc, base - h), (x + 0.7 * sc, base - h), (x + 1.6 * sc, base)])
    both(c, m, col, 0.3, lambda k, cl: (fill(k, tower, cl),
                                        fill_rect(k, x - 1.5 * sc, base - h - 1.5 * sc, 5 * sc, 3 * sc, cl)))
    S.turbines.append((x, base - h, h * 0.42))


def crowd(c, m, W, H, seed, sc, top) -> None:
    """A crowd along the bottom edge: heads and shoulders, a few raised phones with lit screens."""
    rnd = prng(seed)
    for row, dark, sz in ((0, (9, 9, 12), 0.85), (1, (4, 4, 6), 1.15)):
        y0 = top + row * 16 * sc
        x = -10 * sc
        while x < W + 10 * sc:
            s = sc * sz * (0.85 + rnd() * 0.3)
            hx, hy = x + (rnd() - 0.5) * 4 * sc, y0 + (rnd() - 0.5) * 6 * sc
            arm = rnd() < 0.07
            person = ellipse(path(), hx, hy, 4.2 * s, 5.2 * s)
            body = path()
            body.moveTo(hx - 11 * s, H)
            body.lineTo(hx - 10 * s, hy + 9 * s)
            body.quadTo(hx, hy + 4 * s, hx + 10 * s, hy + 9 * s)
            body.lineTo(hx + 11 * s, H)
            body.closeSubpath()
            person.addPath(body)
            if arm:
                person.addRect(hx + 6 * s, hy - 12 * s, 2 * s, 18 * s)
                ellipse(person, hx + 7 * s, hy - 13 * s, 2.4 * s, 2.4 * s)
            fill(c, person, rgb(*dark))
            fill(m, person, mat(0.25))
            if row == 1 and rnd() < 0.08:                       # phone held up, screen glowing
                px, py = hx + (rnd() - 0.5) * 10 * s, hy - 16 * s
                fill_rect(c, px - 0.8 * s, py + 4 * s, 1.6 * s, 10 * s, rgb(*dark))
                fill_rect(c, px - 2.6 * s, py - 4 * s, 5.2 * s, 8 * s, rgb(190, 215, 255, 0.85))
                glow(c, px, py, 14 * s, (170, 200, 255), 0.18)
            x += (12 + rnd() * 8) * sc * sz

