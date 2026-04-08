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

# models/__init__.py
"""
Core models for firework simulation including particles and patterns.
"""

from .particle import Particle
from .firework import Firework
from .patterns import (
    Pattern,
    CirclePattern,
    HeartPattern
)

# gui/__init__.py
"""
GUI components for the fireworks application.
"""

from .main_window import FireworksApp
from .canvas import FireworksCanvas
from .controls import ControlPanel

# effects/__init__.py
"""
Special effects including weather, backgrounds, and sound.
"""

from .weather import (
    WeatherEffect,
    RainEffect,
    SnowEffect,
    WeatherParticle
)
from .backgrounds import (
    Background,
    NightSkyBackground,
    CityscapeBackground
)
from .sound import SoundManager
from .particle_effects import (
    SmokeEffect,
    SmokeParticle
)

# utils/__init__.py
"""
Utility functions for physics, colors, math, and timing.
"""

from .physics import PhysicsUtils
from .color import ColorUtils
from .math import MathUtils
from .time import TimeUtils

# standalone/__init__.py
"""
Standalone versions of the application.
"""

from .fireworks_app import main as run_standalone