"""The realistic renderer's side of FireworksCanvas (mixed into gui/canvas.py).

With `renderer == "Realistic"` the canvas's timer steps a gui.real_show.RealShow (models/pyro.py shells driven by
models/director.py) instead of the classic Firework list, and paints it with gui.real_painter.RealPainter.  The
classic settings carry over (see RealShow.sync); weather keeps updating and is drawn on top.  "Classic" is the
original behaviour and the constructor's default; the main window starts in Realistic (ui_specs.RENDERERS[0]).

Scenery (realistic renderer only): "Realistic" paints the chosen background with effects/scenery.py (built once per
size in device pixels, rebuilt after a resize once the size has settled for RESIZE_SETTLE s; the sim's horizon is the
scenery's, so shells rise from behind the skyline or waterline); "Classic" (the constructor's default) draws the
effects/backgrounds.py object as before.  The realistic-only scenes (effects/scenery_more.py, scenery_land.py) are
chosen by name (background_name); the time of day, sky effects, scene animations, realistic weather and ground
devices live in gui/canvas_fx.py (FxMixin).  Lift time (ui_specs.LIFT_TIME) sets Sim.lift_time; 5 s means real time.
"""
from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPainter

from effects import backgrounds as B
from effects.backgrounds import BeachBackground
from effects.mountains import MountainsBackground
from effects.scenery import NEW_SCENERY_HORIZON, SCENE_HORIZON, build_scenery
from gui.real_painter import RealPainter
from gui.real_show import BEACH_HORIZON, HORIZON, RealShow
from gui.text_points import message
from models.patterns import TextPattern
from models.shell_types import LABELS
from ui_specs import LIFT_REAL_TIME

TYPE_OF_LABEL = {label: t for t, label in LABELS.items()}
SCENE_OF_CLASS = {B.NightSkyBackground: "Night Sky", B.CityscapeBackground: "Cityscape",
                  MountainsBackground: "Mountains", B.BeachBackground: "Beach", B.ForestBackground: "Forest"}
RESIZE_SETTLE = 0.25      # s without resizing before the scenery is rebuilt at the new size
LIFT_REAL = LIFT_REAL_TIME  # lift time setting meaning "real time" (Sim.lift_time = None)


class RealisticMixin:
    renderer = "Classic"
    shell_type = "Mixed"
    pattern_name = None
    scenery_mode = "Classic"
    lift_time = 3.0
    _real = None
    _real_painter = None
    _scenery = None
    _resized_at = 0.0

    # --- setters (wired to the control panel) ---------------------------------------------------------------
    def set_renderer(self, name: str) -> None:
        self.renderer = "Realistic" if name == "Realistic" else "Classic"
        if self.renderer == "Realistic":
            self._ensure_real()
        self.update()

    def set_scenery_mode(self, name: str) -> None:
        """"Realistic" (effects/scenery.py) or "Classic" (effects/backgrounds.py) scenes in the realistic renderer."""
        self.scenery_mode = "Realistic" if name == "Realistic" else "Classic"
        self.update()

    def set_lift_time(self, seconds) -> None:
        """Seconds from launch to burst at most (shorter climbs are played faster); >= 5 or None: real time."""
        self.lift_time = None if seconds is None or seconds >= LIFT_REAL else float(seconds)
        if self._real is not None:
            self._real.set_lift_time(self.lift_time)

    def set_shell_type(self, label: str) -> None:
        self.shell_type = label
        if self._real is not None:
            self._real.set_shell_type(TYPE_OF_LABEL.get(label, "mixed"))

    def start_finale(self) -> None:
        self._ensure_real().start_finale()

    def show_message(self, text: str, hold: float = 2.5, opener: str = "off", finale: bool = False) -> bool:
        """Queue a message show spelling `text` (opening show "off"/"short"/"medium"/"long" first, optional finale
        after); False when the text gives no stars."""
        real = self._ensure_real()
        self._real_sync()
        msgs = message(text, real.sim.aspect, real.sim.horizon, hold)
        if not msgs:
            return False
        real.queue_messages(msgs, opener, finale)
        return True

    # --- state ----------------------------------------------------------------------------------------------
    @property
    def real_show(self):
        return self._ensure_real()

    def _ensure_real(self) -> RealShow:
        if self._real is None:
            self._real = RealShow(self._real_aspect(), self._real_horizon())
            self._real.set_shell_type(TYPE_OF_LABEL.get(self.shell_type, "mixed"))
            self._real.set_lift_time(self.lift_time)
            self._real_painter = RealPainter()
        return self._real

    def _real_aspect(self) -> float:
        return max(1, self.width()) / max(1, self.height())

    def scene_name(self) -> str:
        """The background's name for effects/scenery.py ("None" without a background)."""
        if self.background_name in NEW_SCENERY_HORIZON:
            return self.background_name
        return SCENE_OF_CLASS.get(type(self.background), "None") if self.background is not None else "None"

    def _real_horizon(self) -> float:
        if self.scenery_mode == "Realistic":
            return SCENE_HORIZON[self.scene_name()]
        return BEACH_HORIZON if isinstance(self.background, BeachBackground) else HORIZON

    def scenery(self, W: int, H: int, dpr: float = 1.0):
        """The realistic scenery for a W x H view (built at W*dpr x H*dpr device pixels, cached; while the view is
        being resized the previous build of the same scene is reused, scaled)."""
        name, tod = self.scene_name(), self.time_of_day
        w, h = max(2, round(W * dpr)), max(2, round(H * dpr))
        S = self._scenery
        same = S is not None and S.name == name and S.time == tod
        if same and (S.W, S.H) == (w, h):
            return S
        if same and time.monotonic() - self._resized_at < RESIZE_SETTLE:
            QTimer.singleShot(int(RESIZE_SETTLE * 1000) + 20, self.update)
            return S
        self._scenery = build_scenery(name, w, h, time=tod)
        return self._scenery

    def resizeEvent(self, event):
        self._resized_at = time.monotonic()
        super().resizeEvent(event)

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
        real.set_ground(self.ground_on, self.niagara_height())

    # --- frame ----------------------------------------------------------------------------------------------
    def _update_real(self) -> None:
        self._real_sync()
        self._real.step()
        if self.uses_fx():
            self._fx_step()
        elif self.weather_effect:
            self.weather_effect.update()
        self.update()

    def _real_launch(self, x=None) -> None:
        """Launch one shell; x in widget pixels (None: random position)."""
        self._real_sync()
        frac = None if x is None else max(-0.98, min(0.98, (x - self.width() / 2) / (self.width() / 2)))
        self._real.launch(frac)

    def paint_real(self, painter: QPainter, W: int, H: int) -> None:
        real = self._ensure_real()
        if self.scenery_mode == "Realistic":
            dpr = painter.device().devicePixelRatioF() if painter.device() is not None else 1.0
            S = self.scenery(W, H, dpr)
            fx = self.fx_layers(W, H)
            self._real_painter.render(painter, W, H, real, scenery=S, fx=fx,
                                      fx_env=self.fx_env(W, H) if fx is not None else None)
            return
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
