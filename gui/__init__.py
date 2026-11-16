# gui/__init__.py
"""
GUI components for the fireworks application.

main_window (FireworksApp), canvas (FireworksCanvas) + canvas_real (realistic renderer mixin), controls
(ControlPanel), real_show (Qt-free Sim/Director state), real_painter + real_sprites (QPainter rendering),
text_points (message text sampler), export (PNG/GIF).
"""

from gui.main_window import FireworksApp
from gui.canvas import FireworksCanvas
from gui.controls import ControlPanel
