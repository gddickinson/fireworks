"""Imports every realistic weather plug-in so each registers itself with effects/fx_base.WEATHER:
Rain, Snow, Fog, Mist, Clouds, Storm (label "Thunderstorm") and Lightning (effects/wx_*.py)."""
from effects import wx_clouds, wx_fog, wx_lightning, wx_rain, wx_snow  # noqa: F401
from effects.fx_base import WEATHER

NAMES = ["Rain", "Snow", "Fog", "Mist", "Clouds", "Storm", "Lightning"]
assert all(n in WEATHER for n in NAMES)
