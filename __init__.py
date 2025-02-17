# Root __init__.py
"""
Fireworks Simulation Application
A PyQt6-based application for simulating fireworks displays with various effects.
"""

from . import models
from . import gui
from . import effects
from . import utils
from .config import FireworkConfig, DisplayConfig

__version__ = '1.0.0'
