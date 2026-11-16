"""Message text -> star positions for message shells (desktop counterpart of web/static/fw_text.js textPoints).

The text is laid out with a bold QFont as a QPainterPath (QPainterPath.addText), wrapped into the number of lines
(1-4) that makes the letters biggest, and scaled to fit the sky at the message distance (z = 450 m):
width <= 0.86 * 450 * aspect / FOCAL and height <= 0.62 * 450 * horizon / FOCAL metres.  About `density` points
are picked on a staggered (hexagonal) grid inside the letters (QPainterPath.contains) and coloured as a rainbow
across the text.  The result feeds models.director.Director.queue_messages:
[{"points": [[u, v, r, g, b], ...], "hold": s}] with u, v in metres from the text centre, v up.
"""
from __future__ import annotations

import colorsys
import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QFont, QFontMetricsF, QPainterPath

from models.pyro import FOCAL

MAX_CHARS = 80
PX = 96.0               # layout font size in px
Z = 450.0               # message distance in metres (Director launches messages at z = 450)


def clean_text(text: str) -> str:
    """Printable text, at most MAX_CHARS characters, lines trimmed, empty lines dropped."""
    t = "".join(ch for ch in str(text or "") if ch == "\n" or ch.isprintable())[:MAX_CHARS]
    return "\n".join(line.strip() for line in t.split("\n") if line.strip())


def wrap_lines(text: str, n: int) -> list:
    """Words into lines of roughly len/n characters (explicit newlines kept)."""
    out = []
    for para in text.split("\n"):
        words, target = para.split(), math.ceil(len(para) / n)
        line = ""
        for w in words:
            if line and len(line) + 1 + len(w) / 2 > target:
                out.append(line)
                line = w
            else:
                line = f"{line} {w}" if line else w
        if line:
            out.append(line)
    return out


def _font() -> QFont:
    f = QFont()
    f.setFamilies(["Helvetica Neue", "Helvetica", "Arial", "Segoe UI", "DejaVu Sans"])
    f.setStyleHint(QFont.StyleHint.SansSerif)
    f.setPixelSize(int(PX))
    f.setWeight(QFont.Weight.Black)
    return f


def text_path(text: str, aspect: float, horizon: float):
    """(path in layout px centred on (0, 0), metres per px, lines) for the best wrapping of text."""
    font = _font()
    fm = QFontMetricsF(font)
    width_m = 0.86 * Z * aspect / FOCAL
    height_m = 0.62 * Z * horizon / FOCAL
    paras = len(text.split("\n"))
    best = None
    for n in range(1, 5):
        lines = text.split("\n") if n == 1 else wrap_lines(text, n)
        if n > 1 and len(lines) <= paras:
            continue
        w = max(fm.horizontalAdvance(line) for line in lines)
        h = len(lines) * PX * 1.15
        k = min(width_m / max(w, 1.0), height_m / h)
        if best is None or k > best[0] * 1.08:
            best = (k, lines, h)
    k, lines, h = best
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    for i, line in enumerate(lines):
        w = fm.horizontalAdvance(line)
        base = -h / 2 + (i + 0.5) * PX * 1.15 + (fm.ascent() - fm.descent()) / 2   # line centred in its slot
        path.addText(QPointF(-w / 2, base), font, line)
    return path, k, lines


def text_points(text: str, aspect: float, horizon: float, density: int = 400) -> list:
    """[[u, v, r, g, b], ...] (metres, v up) of about `density` stars spelling `text`; [] for empty text."""
    text = clean_text(text)
    if not text:
        return []
    path, k, lines = text_path(text, aspect, horizon)
    box = path.boundingRect()
    if box.width() <= 0 or box.height() <= 0:
        return []
    # ink area from a coarse grid, then the grid step that gives ~density points
    nx = 60
    ny = max(4, int(nx * box.height() / box.width()))
    hit = sum(path.contains(QPointF(box.left() + (i + 0.5) * box.width() / nx,
                                    box.top() + (j + 0.5) * box.height() / ny))
              for i in range(nx) for j in range(ny))
    if not hit:
        return []
    ink = box.width() * box.height() * hit / (nx * ny)
    step = max(1.5, math.sqrt(ink / density / 0.866))
    cx, cy = box.center().x(), box.center().y()
    pts = []
    row = 0
    y = box.top() + step / 2
    n_lines = len(lines)
    while y < box.bottom():
        x = box.left() + (step / 2 if row % 2 else 0.0) + step / 4
        li = min(n_lines - 1, max(0, int((y - box.top()) / max(box.height(), 1e-9) * n_lines)))
        while x < box.right():
            if path.contains(QPointF(x, y)):
                t = (x - box.left()) / box.width()
                r, g, b = colorsys.hsv_to_rgb((t * 0.85 + li * 0.13) % 1.0, 0.75, 1.0)
                pts.append([(x - cx) * k, (cy - y) * k, round(r * 255), round(g * 255), round(b * 255)])
            x += step
        y += step * 0.866
        row += 1
    return pts


def message(text: str, aspect: float, horizon: float, hold: float = 2.5, density: int = 400) -> list:
    """The `messages` list for Director.queue_messages (one message), or [] when the text has no stars."""
    pts = text_points(text, aspect, horizon, density)
    return [{"points": pts, "hold": hold}] if pts else []
