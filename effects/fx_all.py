"""Loads every plug-in module of the desktop realistic renderer (each registers itself with effects/fx_base.py):
weather (effects/wx_all.py), sky effects (sky_fx.py, sky_aurora.py) and scene animations (scene_fx.py)."""
import effects.scene_fx  # noqa: F401
import effects.sky_aurora  # noqa: F401
import effects.sky_fx  # noqa: F401
import effects.wx_all  # noqa: F401
from effects.fx_base import SCENE_FX, SKY_FX, WEATHER  # noqa: F401
