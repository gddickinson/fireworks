# effects/__init__.py
"""
Special effects including weather, backgrounds, and sound.
"""

from effects.weather import (
    WeatherEffect,
    RainEffect,
    SnowEffect,
    WeatherParticle
)
from effects.backgrounds import (
    Background,
    NightSkyBackground,
    CityscapeBackground
)
from effects.sound import SoundManager
from effects.particle_effects import (
    SmokeEffect,
    SmokeParticle
)
