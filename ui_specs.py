"""Qt-free control specifications shared by the desktop control panel (gui/controls.py) and the web app (web/).

The choice lists (patterns, backgrounds, weather, renderers, shell types) and the slider ranges/defaults/scales live here once, so the web
version offers exactly the controls of the desktop app. A slider's real value is ``slider_value * scale``.
"""
from dataclasses import asdict, dataclass

from config import DEFAULT_LAUNCH_SPEED, FireworkConfig
from models.ground_effects import DEVICES as GROUND_DEVICES, LABELS as GROUND_LABELS
from models.shell_types import LABELS, TYPES

PATTERNS = ["Random", "Circle", "Heart", "Star", "Spiral", "Double Ring", "Text"]
BACKGROUNDS = ["Night Sky", "Cityscape", "Mountains", "Beach", "Forest"]
WEATHER = ["None", "Rain", "Snow", "Fog", "Lightning"]
RENDERERS = ["Realistic", "Classic"]    # desktop: gui/real_painter.py (3-D shells) or the original particle model
SCENERIES = ["Realistic", "Classic"]    # desktop realistic renderer: effects/scenery.py or effects/backgrounds.py
SHELL_TYPES = ["Mixed"] + [LABELS[t] for t in TYPES]   # realistic mode; "Mixed" draws a type per shell
# Desktop realistic renderer with realistic scenery only (effects/scenery_more.py, scenery_land.py, effects/fx_*.py):
REAL_BACKGROUNDS = BACKGROUNDS + ["Harbour", "River Bridge", "Waterfront", "Desert", "Snowy Village", "Castle",
                                  "Countryside"]
TIMES_OF_DAY = ["Night", "Dusk"]
REAL_WEATHER = ["None", "Rain", "Snow", "Fog", "Mist", "Clouds", "Storm", "Lightning"]
SKY_EFFECTS = {"moon": "Moon", "aurora": "Aurora", "meteors": "Shooting stars", "lanterns": "Sky lanterns"}
GROUND_DEVICE_LABELS = [GROUND_LABELS[k] for k in GROUND_DEVICES]
OPENERS = {"Off": "off", "Short (~8 s)": "short", "Medium (~15 s)": "medium", "Long (~25 s)": "long"}  # message shows


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

# Desktop realistic renderer (not in SLIDERS, which the web panel builds): seconds from launch to burst at most,
# 1.5-5 s in 0.5 s steps; the top value means real time (models.pyro.Sim.lift_time = None, about 4.5 s).
LIFT_TIME = SliderSpec("lift_time", "Lift time", 3, 10, 6, 0.5)
LIFT_REAL_TIME = LIFT_TIME.hi * LIFT_TIME.scale
# Realistic weather amount (the web's "Rain / snow amount", env.intensity): 30-250 % in 10 % steps.
WX_INTENSITY = SliderSpec("wx_intensity", "Rain / snow amount", 3, 25, 10, 0.1)

SLIDERS = [PARTICLE_COUNT, PATTERN_SCALE, PATTERN_ROTATION, STAR_POINTS, SPIRAL_ARMS, GRAVITY, LAUNCH_SPEED]


def specs_as_dicts() -> list:
    return [asdict(s) for s in SLIDERS]
