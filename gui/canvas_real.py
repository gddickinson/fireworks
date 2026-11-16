"""The realistic renderer's side of FireworksCanvas (mixed into gui/canvas.py).

With `renderer == "Realistic"` the canvas's timer steps a gui.real_show.RealShow (models/pyro.py shells driven by
models/director.py) instead of the classic Firework list, and paints it with gui.real_painter.RealPainter.  The
classic settings carry over (see RealShow.sync); weather keeps updating and is drawn on top.  "Classic" is the
original behaviour and the constructor's default; the main window starts in Realistic (ui_specs.RENDERERS[0]).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter

from effects.backgrounds import BeachBackground
from gui.real_painter import RealPainter
from gui.real_show import BEACH_HORIZON, HORIZON, RealShow
from gui.text_points import message
from models.patterns import TextPattern
from models.shell_types import LABELS

TYPE_OF_LABEL = {label: t for t, label in LABELS.items()}


class RealisticMixin:
    renderer = "Classic"
    shell_type = "Mixed"
    pattern_name = None
    _real = None
    _real_painter = None

    # --- setters (wired to the control panel) ---------------------------------------------------------------
    def set_renderer(self, name: str) -> None:
        self.renderer = "Realistic" if name == "Realistic" else "Classic"
        if self.renderer == "Realistic":
            self._ensure_real()
        self.update()

    def set_shell_type(self, label: str) -> None:
        self.shell_type = label
        if self._real is not None:
            self._real.set_shell_type(TYPE_OF_LABEL.get(label, "mixed"))

    def start_finale(self) -> None:
        self._ensure_real().start_finale()

    def show_message(self, text: str, hold: float = 2.5) -> bool:
        """Queue a message shell spelling `text`; False when the text gives no stars."""
        real = self._ensure_real()
        self._real_sync()
        msgs = message(text, real.sim.aspect, real.sim.horizon, hold)
        if not msgs:
            return False
        real.queue_messages(msgs)
        return True

    # --- state ----------------------------------------------------------------------------------------------
    @property
    def real_show(self):
        return self._ensure_real()

    def _ensure_real(self) -> RealShow:
        if self._real is None:
            self._real = RealShow(self._real_aspect(), self._real_horizon())
            self._real.set_shell_type(TYPE_OF_LABEL.get(self.shell_type, "mixed"))
            self._real_painter = RealPainter()
        return self._real

    def _real_aspect(self) -> float:
        return max(1, self.width()) / max(1, self.height())

    def _real_horizon(self) -> float:
        return BEACH_HORIZON if isinstance(self.background, BeachBackground) else HORIZON

    def _real_pattern(self):
        """The burst shape for new shells: None (real shell types) unless a shape is chosen.

        The Pattern combo's "Random" entry is the classic default; in realistic mode it means "no shape" unless
        "Randomize Patterns" is ticked, so the shell type choice applies."""
        p = self.pattern
        if p is None or (self.pattern_name in (None, "Random") and not self.use_random_patterns):
            return None
        if isinstance(p, TextPattern) and not p.text.strip():
            return None
        return p

    def _real_sync(self) -> None:
        real = self._ensure_real()
        real.set_view(self._real_aspect(), self._real_horizon())
        c = self.firework_color
        color = None if self.use_random_colors or c is None else (c.red(), c.green(), c.blue())
        real.sync(self.particle_count, self.gravity, self.launch_speed, color, self._real_pattern(),
                  self.pattern_scale, self.auto_launch)

    # --- frame ----------------------------------------------------------------------------------------------
    def _update_real(self) -> None:
        self._real_sync()
        self._real.step()
        if self.weather_effect:
            self.weather_effect.update()
        self.update()

    def _real_launch(self, x=None) -> None:
        """Launch one shell; x in widget pixels (None: random position)."""
        self._real_sync()
        frac = None if x is None else max(-0.98, min(0.98, (x - self.width() / 2) / (self.width() / 2)))
        self._real.launch(frac)

    def paint_real(self, painter: QPainter, W: int, H: int) -> None:
        real = self._ensure_real()
        water = BEACH_HORIZON * H if isinstance(self.background, BeachBackground) else None
        self._real_painter.render(painter, W, H, real, self.background, self.weather_effect, self.background_color,
                                  water)

    def render_real_image(self) -> QImage:
        """The current realistic frame as a QImage of the widget's size (no stepping)."""
        img = QImage(max(1, self.width()), max(1, self.height()), QImage.Format.Format_ARGB32_Premultiplied)
        p = QPainter(img)
        self.paint_real(p, img.width(), img.height())
        p.end()
        return img

    def mousePressEvent(self, event):
        if self.renderer == "Realistic" and event.button() == Qt.MouseButton.LeftButton:
            self._real_launch(event.position().x())
            event.accept()
            return
        super().mousePressEvent(event)

    def reset_real(self) -> None:
        if self._real is not None:
            self._real.clear()
            self._real_painter.clear()
