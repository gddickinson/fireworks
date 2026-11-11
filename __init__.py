# Root __init__.py
"""
Fireworks Simulation Application
A PyQt6-based application for simulating fireworks displays with various effects.
"""

from .config import FireworkConfig, DisplayConfig

try:
    from . import models
    from . import gui
    from . import effects
    from . import utils
except ImportError:  # PyQt6 not installed (e.g. the web app's CI): the Qt-free modules still import on their own
    pass

__version__ = '1.0.0'
