"""Built structures of the realistic scenery: a QPainter port of web/static/fw_scenery_city.js.

City skylines with lit windows and aviation lights, street-light rows, soft light glows, and the waterfront pieces:
tall towers with lit crowns, a ferris wheel and a cable-stayed bridge.  Colour goes to `c`, material (albedo) to `m`
(effects/scenery_parts.Layer); positions of blinking lights are appended to S.beacons (scenery px) for the scene
plug-ins (effects/scene_fx.py).  Same prng draws as the web.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QBrush, QLinearGradient, QRadialGradient

from effects.scenery_draw import circle, fill, fill_rect, path, poly, rect, stroke
from effects.scenery_noise import prng
from effects.scenery_parts import mat, rgb, vgrad
from effects.scenery_sky import tone


def glow(c, x, y, r, col, a=0.6, core=0.12) -> None:
    """Soft round glow (a lamp, a lit window's halo): radial gradient, `core` fraction of r at full strength."""
    if r <= 0:
        return
    g = QRadialGradient(QPointF(x, y), r)
    g.setColorAt(0, rgb(*col, a))
    g.setColorAt(core, rgb(*col, a * 0.45))
    g.setColorAt(1, rgb(*col, 0))
    c.p.fillRect(QRectF(x - r, y - r, 2 * r, 2 * r), QBrush(g))


def skyline(c, m, W, H, wl, seed, far, S=None, tall=1.0, sc=None) -> None:
    """City skyline on the far bank at wl. Far: lower, hazier, tiny windows. Near: towers with roof details.
    S (optional): the scene, for dusk tones and beacon positions; tall: taller cluster (big-city waterfront)."""
    rnd = prng(seed)
    sc = H / 800 if sc is None else sc
    centre = 0.3 + rnd() * 0.4
    x = -rnd() * 30 * sc
    while x < W:
        w = (14 + rnd() * 30 if far else 22 + rnd() * 48) * sc
        d = (x / W - centre) / 0.28
        cluster = math.exp(-d * d)
        if far:
            h = (30 + rnd() * 50 + 90 * cluster * rnd()) * sc
        else:
            h = (24 + rnd() * 50 + 170 * tall * cluster * rnd() ** 0.7) * sc
        if not far and rnd() < 0.12:
            h *= 0.35
        building(c, m, x, wl, w, h, rnd, far, sc, S)
        x += w + (rnd() * 8 * sc if rnd() < 0.2 else 0)


def building(c, m, x, base, w, h, rnd, far, sc, S=None) -> None:
    p, top = c.p, base - h
    col = (24, 24, 36) if far else (9, 10, 16)
    if S is not None:
        col = tone(S, col, 0.8 if far else 0.4)
    p.fillRect(QRectF(x, top, w, h), QBrush(vgrad(top, base, [(0, rgb(*(v * 1.25 for v in col))), (1, rgb(*col))])))
    m.p.fillRect(QRectF(x, top, w, h), mat(0.25 if far else 0.35))
    roof, r = top, rnd()                                        # roof details
    if not far and r < 0.3 and h > 120 * sc:                    # setbacks
        w2, h2, w3, h3 = w * 0.7, h * 0.12, w * 0.4, h * 0.08
        p.fillRect(QRectF(x + (w - w2) / 2, top - h2, w2, h2), rgb(*col))
        p.fillRect(QRectF(x + (w - w3) / 2, top - h2 - h3, w3, h3), rgb(*col))
        m.p.fillRect(QRectF(x + (w - w2) / 2, top - h2, w2, h2), mat(0.35))
        roof = top - h2 - h3
    elif not far and r < 0.45 and h > 150 * sc:                 # spire
        fill(c, poly([(x + w * 0.3, top), (x + w / 2, top - h * 0.22), (x + w * 0.7, top)]), rgb(*col))
        roof = top - h * 0.22
    elif r < 0.65:                                              # plant room / water tank
        p.fillRect(QRectF(x + w * (0.1 + rnd() * 0.4), top - 6 * sc, w * 0.3, 6 * sc), rgb(*col))
    if not far and (r > 0.85 or h > 220 * sc):                  # antenna with a red aviation light
        ax, ay = x + w / 2, roof - 26 * sc
        p.fillRect(QRectF(ax - sc * 0.6, ay, 1.2 * sc, 26 * sc), rgb(20, 20, 26))
        p.setBrush(rgb(255, 40, 30, 0.9))
        p.drawEllipse(QPointF(ax, ay), 1.6 * sc, 1.6 * sc)
        g = QRadialGradient(QPointF(ax, ay), 9 * sc)
        g.setColorAt(0, rgb(255, 40, 30, 0.35))
        g.setColorAt(1, rgb(255, 40, 30, 0))
        p.fillRect(QRectF(ax - 9 * sc, roof - 35 * sc, 18 * sc, 18 * sc), QBrush(g))
        if S is not None:
            S.beacons.append((ax, ay, 1.6 * sc))
    windows(c, x, top, w, base, rnd, far, sc)


def windows(c, x, top, w, base, rnd, far, sc) -> None:
    """Window grid of a building face: a random share lit, warm or cool, sometimes whole floors."""
    p = c.p
    cw, chh = (2.2 if far else 3.2) * sc, (3.2 if far else 4.4) * sc
    lit = 0.06 + rnd() * (0.2 if far else 0.32)
    warm, floor_lit = rnd() < 0.7, rnd() < 0.3
    a0 = 0.35 if far else 0.55
    fy = top + chh
    while fy < base - chh * 1.5:
        whole = floor_lit and rnd() < 0.15
        fx = x + cw * 0.7
        while fx < x + w - cw * 1.2:
            if whole or rnd() < lit:
                if warm:
                    t = (255, 196, 120) if rnd() < 0.85 else (190, 215, 255)
                else:
                    t = (200, 225, 255) if rnd() < 0.7 else (255, 210, 150)
                p.fillRect(QRectF(fx, fy, cw, chh * 0.75), rgb(*t, a0 + rnd() * 0.4))
            fx += cw * 1.7
        fy += chh * 1.6


def street_lights(c, W, H, wl, seed, sc=None) -> None:
    rnd, p = prng(seed), c.p
    sc = H / 800 if sc is None else sc
    x = rnd() * 20 * sc
    while x < W:
        y, r = wl - (2 + rnd() * 3) * sc, (6 + rnd() * 6) * sc
        col = (255, 170, 80) if rnd() < 0.75 else (220, 235, 255)
        g = QRadialGradient(QPointF(x, y), r)
        g.setColorAt(0, rgb(*col, 0.9))
        g.setColorAt(0.15, rgb(*col, 0.35))
        g.setColorAt(1, rgb(*col, 0))
        p.fillRect(QRectF(x - r, y - r, 2 * r, 2 * r), QBrush(g))
        x += (14 + rnd() * 18) * sc


def crown_tower(S, c, m, x, base, w, h, rnd, sc, col) -> float:
    """A slender tower with a floodlit crown (pyramid or stepped), a mast with a beacon. Returns the mast top y."""
    body, top = tone(S, (8, 9, 15), 0.35), base - h
    g = QLinearGradient(x, 0, x + w, 0)                         # a faint lit edge on one side
    g.setColorAt(0, rgb(*(v * 1.6 for v in body)))
    g.setColorAt(0.25, rgb(*body))
    g.setColorAt(1, rgb(*(v * 0.8 for v in body)))
    c.p.fillRect(QRectF(x, top, w, h), QBrush(g))
    m.p.fillRect(QRectF(x, top, w, h), mat(0.35))
    windows(c, x, top + 4 * sc, w, base, rnd, False, sc)
    fill_rect(c, x + w * 0.15, top, 1.2 * sc, h * 0.7, rgb(*col, 0.25))
    fill_rect(c, x + w * 0.85 - 1.2 * sc, top, 1.2 * sc, h * 0.7, rgb(*col, 0.25))
    kind, ch = rnd(), h * (0.1 + rnd() * 0.06)
    if kind < 0.5:                                              # pyramid crown, lit from below
        crown = poly([(x, top), (x + w / 2, top - ch), (x + w, top)])
    else:                                                       # stepped crown
        pts = [(x, top)]
        for i in range(4):
            ix, y = w * 0.12 * (i + 1), top - ch * (i + 1) / 4
            pts += [(x + ix - w * 0.12, y), (x + ix, y)]
        pts.append((x + w - w * 0.48, top - ch))
        for i in range(3, -1, -1):
            ix, y = w * 0.12 * (i + 1), top - ch * (i + 1) / 4
            pts += [(x + w - ix, y), (x + w - ix + w * 0.12, y)]
        pts.append((x + w, top))
        crown = poly(pts)
    p = c.p
    p.save()
    fill(c, crown, vgrad(top - ch, top, [(0, rgb(*col, 0.35)), (1, rgb(*col, 0.95))]))
    p.setClipPath(crown)
    for i in range(1, 6):
        p.fillRect(QRectF(x + w * i / 6 - sc * 0.4, top - ch, sc * 0.8, ch), rgb(0, 0, 0, 0.35))
    p.restore()
    m.p.fillRect(rect(x, top - ch, w, ch), mat(0.5))
    glow(c, x + w / 2, top - ch * 0.4, w * 1.4, col, 0.22, 0.2)
    mh = h * 0.12                                               # mast with an aviation light
    fill_rect(c, x + w / 2 - sc * 0.6, top - ch - mh, 1.2 * sc, mh, rgb(*(v * 1.8 for v in body)))
    S.beacons.append((x + w / 2, top - ch - mh, 1.8 * sc))
    return top - ch - mh


def ferris_wheel(c, m, cx, cy, r, sc, rnd) -> None:
    """Ferris wheel with lit rim and cabins (rim radius r, hub at cx, cy)."""
    legs = poly([(cx - r * 0.45, cy + r * 1.12), (cx, cy), (cx + r * 0.45, cy + r * 1.12)], close=False)
    stroke(c, legs, rgb(30, 32, 44), 2.2 * sc)
    stroke(m, legs, mat(0.4), 2.2 * sc)
    n, hue = 32, ((120, 200, 255) if rnd() < 0.5 else (255, 120, 210))
    spokes = path()
    for i in range(0, n, 2):
        a = i / n * 6.2832
        spokes.moveTo(cx, cy)
        spokes.lineTo(cx + math.cos(a) * r, cy + math.sin(a) * r)
    stroke(c, spokes, rgb(*hue, 0.35), 0.7 * sc)
    for rr, a, w in ((r, 0.9, 1.6), (r * 0.93, 0.5, 1)):
        stroke(c, circle(path(), cx, cy, rr), rgb(*hue, a), w * sc)
    glow(c, cx, cy, r * 1.35, hue, 0.12, 0.5)
    for i in range(n):                                          # cabins: bright dots on the rim
        a = i / n * 6.2832
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        c.p.fillRect(QRectF(x - 1.3 * sc, y, 2.6 * sc, 2.4 * sc), rgb(255, 235, 200, 0.95))


def cable_bridge(S, c, m, deck, topY, pylons, sc, seed, wl) -> None:
    """Cable-stayed bridge across the frame (side view): deck at `deck` (px), pylons at fractions of W rising to
    `topY`, fans of lit stay cables, a row of deck lights."""
    W, rnd, dk, thick = S.W, prng(seed), tone(S, (10, 11, 16), 0.3), 7 * sc
    for k in (c, m):                                            # deck girder and its piers
        col = mat(0.35) if k is m else rgb(*dk)
        fill_rect(k, 0, deck, W, thick, col)
        for pf in pylons:
            fill_rect(k, pf * W - 9 * sc, deck, 18 * sc, wl - deck, col)
    span, nC = (pylons[1] - pylons[0]) * W, 9
    for pf in pylons:                                           # pylons: tapered inverted-Y legs into a mast
        x, mid = pf * W, deck - (deck - topY) * 0.35
        shape = poly([(x - 16 * sc, deck + thick), (x - 4 * sc, mid), (x - 3 * sc, topY), (x + 3 * sc, topY),
                      (x + 4 * sc, mid), (x + 16 * sc, deck + thick), (x + 10 * sc, deck + thick),
                      (x, mid + 14 * sc), (x - 10 * sc, deck + thick)])
        for k in (c, m):
            fill(k, shape, mat(0.45) if k is m else rgb(*(v * 1.3 for v in dk)))
        fill_rect(c, x - 4 * sc, topY, 8 * sc, deck - topY,
                  vgrad(topY, deck, [(0, rgb(200, 220, 255, 0.05)), (1, rgb(200, 220, 255, 0.28))]))
        S.beacons.append((x, topY - 2 * sc, 2 * sc))
        for i in range(1, nC + 1):                              # stay cables both ways from the mast top
            ay, reach = topY + (mid - topY) * 0.45 * i / nC, span * 0.46 * i / nC
            for s in (-1, 1):
                ex = x + s * reach
                cg = QLinearGradient(x, ay, ex, deck)
                cg.setColorAt(0, rgb(170, 200, 255, 0.35))
                cg.setColorAt(1, rgb(210, 230, 255, 0.6))
                line = poly([(x, ay), (ex, deck)], close=False)
                stroke(c, line, cg, 0.9 * sc)
                stroke(m, line, mat(0.3), 0.9 * sc)
    x = rnd() * 10 * sc
    while x < W:                                                # deck lights along the parapet
        fill_rect(c, x - sc, deck - 3 * sc, 2 * sc, 2 * sc, rgb(255, 205, 140, 0.95))
        glow(c, x, deck - 2 * sc, 7 * sc, (255, 180, 100), 0.4)
        x += 22 * sc
    fill_rect(c, 0, deck + thick - 1.2 * sc, W, 1.2 * sc, rgb(120, 150, 210, 0.22))   # lit underside edge
