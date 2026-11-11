"""Qt-free control specifications shared by the desktop control panel (gui/controls.py) and the web app (web/).

The choice lists (patterns, backgrounds, weather) and the slider ranges/defaults/scales live here once, so the web
version offers exactly the controls of the desktop app. A slider's real value is ``slider_value * scale``.
"""
from dataclasses import asdict, dataclass

from config import DEFAULT_LAUNCH_SPEED, FireworkConfig

PATTERNS = ["Random", "Circle", "Heart", "Star", "Spiral", "Double Ring", "Text"]
BACKGROUNDS = ["Night Sky", "Cityscape", "Mountains", "Beach", "Forest"]
WEATHER = ["None", "Rain", "Snow", "Fog", "Lightning"]


@dataclass(frozen=True)
class SliderSpec:
    key: str
    label: str
    lo: int
    hi: int
    default: int
    scale: float = 1.0  # real value = slider value * scale


PARTICLE_COUNT = SliderSpec("particle_count", "Particle Count", FireworkConfig.MIN_PARTICLES,
                            FireworkConfig.MAX_PARTICLES, FireworkConfig.DEFAULT_PARTICLES)
PATTERN_SCALE = SliderSpec("pattern_scale", "Scale", 50, 200, 100, 0.01)
PATTERN_ROTATION = SliderSpec("pattern_rotation", "Rotation", 0, 360, 0)  # degrees (the canvas gets radians)
STAR_POINTS = SliderSpec("star_points", "Points", 3, 12, 5)
SPIRAL_ARMS = SliderSpec("spiral_arms", "Arms", 1, 8, 3)
GRAVITY = SliderSpec("gravity", "Gravity", 0, 100, int(FireworkConfig.GRAVITY * 100), 0.01)
LAUNCH_SPEED = SliderSpec("launch_speed", "Launch Speed", 50, 200, round(DEFAULT_LAUNCH_SPEED * 10), 0.1)

SLIDERS = [PARTICLE_COUNT, PATTERN_SCALE, PATTERN_ROTATION, STAR_POINTS, SPIRAL_ARMS, GRAVITY, LAUNCH_SPEED]


def specs_as_dicts() -> list:
    return [asdict(s) for s in SLIDERS]
