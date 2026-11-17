"""Small canvas-2D-like drawing helpers for the scenery painters (effects/scenery_city.py, scenery_props.py,
scenery_houses.py, scenery_more.py, scenery_land.py): polygons and strokes with the non-zero fill rule of canvas 2D,
rectangles with any sign of width/height, and the web's `both(c, m, col, albedo, fn)` (same shape on the colour and
material layers)."""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QPainterPath, QPen

from effects.scenery_parts import mat


def path() -> QPainterPath:
    p = QPainterPath()
    p.setFillRule(Qt.FillRule.WindingFill)
    return p


def poly(pts, close=True) -> QPainterPath:
    """Canvas beginPath + lineTo per point (+ closePath)."""
    p = path()
    for i, (x, y) in enumerate(pts):
        p.lineTo(x, y) if i else p.moveTo(x, y)
    if close:
        p.closeSubpath()
    return p


def polyline(xs, ys) -> QPainterPath:
    p = path()
    for i, (x, y) in enumerate(zip(xs, ys)):
        p.lineTo(float(x), float(y)) if i else p.moveTo(float(x), float(y))
    return p


def rect(x, y, w, h) -> QRectF:
    """Canvas fillRect geometry (negative sizes allowed)."""
    return QRectF(x, y, w, h).normalized()


def fill_rect(layer, x, y, w, h, brush) -> None:
    layer.p.fillRect(rect(x, y, w, h), QBrush(brush))


def fill(layer, pth: QPainterPath, brush) -> None:
    p = layer.p
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(brush))
    p.drawPath(pth)


def stroke(layer, pth: QPainterPath, brush, width, cap=Qt.PenCapStyle.FlatCap) -> None:
    p = layer.p
    p.setPen(QPen(QBrush(brush), width, Qt.PenStyle.SolidLine, cap, Qt.PenJoinStyle.MiterJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(pth)
    p.setPen(Qt.PenStyle.NoPen)


def circle(pth: QPainterPath, x, y, r) -> QPainterPath:
    pth.addEllipse(QPointF(x, y), r, r)
    return pth


def ellipse(pth: QPainterPath, x, y, rx, ry) -> QPainterPath:
    pth.addEllipse(QPointF(x, y), rx, ry)
    return pth


def upper_half(pth: QPainterPath, x, y, rx, ry) -> QPainterPath:
    """Canvas arc/ellipse from pi to 0 (through the top), joined to the current point if any."""
    r = QRectF(x - rx, y - ry, 2 * rx, 2 * ry)
    if pth.elementCount() <= 1:                                 # empty (or only the implicit start point)
        pth.moveTo(x - rx, y)
    pth.arcTo(r, 180, -180)
    return pth


def both(c, m, col, albedo, fn) -> None:
    """fn(layer, brush) on the colour layer with `col` and on the material layer with mat(albedo)."""
    fn(c, col)
    fn(m, mat(albedo))


TAU = 2 * math.pi
