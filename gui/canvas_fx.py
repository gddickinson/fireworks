"""The realistic renderer's plug-in layers on FireworksCanvas (mixed into gui/canvas.py before RealisticMixin).

With the Realistic renderer and Realistic scenery the canvas keeps an effects.fx_base.FxLayers of: the scene's
animated objects (effects/scene_fx.py: boats, lighthouse, chimney smoke, beacons, searchlights, turbines; always on),
the sky effects that are ticked (effects/sky_fx.py, sky_aurora.py: moon, aurora, shooting stars, lanterns) and the
realistic weather (effects/wx_*.py: Rain, Snow, Fog, Mist, Clouds, Storm, Lightning).  The list is rebuilt when the
scenery object (scene, time of day, size) or a choice changes; every timer step updates it with an FxEnv (view
size, scenery, burst lights, sim time, gusty wind, the show's seed), and gui/real_painter.py draws its sky pass
behind the fireworks and its over pass in front.  With Classic scenery (or the Classic renderer) the classic weather
objects (effects/weather.py) are used as before.  Also here: time of day and the ground-device settings.
"""
from __future__ import annotations

import effects.fx_all  # noqa: F401  (registers every plug-in)
from effects.fx_base import SCENE_FX, SKY_FX, WEATHER, FxEnv, FxLayers
from models.ground_effects import DEVICES, LABELS as GROUND_LABELS
from models.pyro import DT

DEVICE_OF_LABEL = {label: k for k, label in GROUND_LABELS.items()}


class FxMixin:
    time_of_day = "night"
    weather_name = "None"
    background_name = None
    sky_fx: tuple = ()
    ground_on = False
    weather_intensity = 1.0
    _fx = None
    _fx_key = None

    # --- setters (wired to the control panel) ---------------------------------------------------------------
    def set_time_of_day(self, name: str) -> None:
        """"Night" or "Dusk" (the realistic scenery is rebuilt for the blue hour)."""
        self.time_of_day = "dusk" if str(name).lower() == "dusk" else "night"
        self.update()

    def set_sky_effects(self, keys) -> None:
        """Keys of effects.fx_base.SKY_FX to show (moon, aurora, meteors, lanterns), in a fixed order."""
        keys = set(keys or ())
        self.sky_fx = tuple(k for k in SKY_FX if k in keys)

    def set_weather_intensity(self, amount: float) -> None:
        """Rain / snow amount of the realistic weather (1 = normal; the plug-ins refill to it each step)."""
        self.weather_intensity = max(0.0, float(amount))

    def set_ground_effects(self, on: bool) -> None:
        self.ground_on = bool(on)
        if self._real is not None:
            self._real.set_ground(self.ground_on, self.niagara_height())

    def fire_ground(self, device: str) -> None:
        """Light one ground device now (a key of models.ground_effects.DEVICES or its label)."""
        kind = DEVICE_OF_LABEL.get(device, device)
        if kind in DEVICES:
            self._real_sync()
            self._ensure_real().fire_ground(kind, self.niagara_height())

    # --- state ----------------------------------------------------------------------------------------------
    def uses_fx(self) -> bool:
        return self.renderer == "Realistic" and self.scenery_mode == "Realistic"

    def niagara_height(self):
        """The bridge's deck height (m) for the niagara curtain: River Bridge with Realistic scenery, else None."""
        S = self._scenery
        if not self.uses_fx() or S is None or S.name != self.scene_name():
            return None
        return S.bridge

    def fx_env(self, W: int, H: int) -> FxEnv:
        real = self._ensure_real()
        return FxEnv(int(W), int(H), self._scenery, real.screen_lights(W, H, 8), real.sim.time, real.sim.wind,
                     real.seed, intensity=self.weather_intensity)

    def fx_layers(self, W: int, H: int):
        """The plug-in layers for the current scenery and choices (None without realistic scenery)."""
        S = self._scenery
        if not self.uses_fx() or S is None:
            return None
        key = (id(S), self.weather_name, self.sky_fx)
        env = self.fx_env(W, H)
        if self._fx is None or key != self._fx_key:
            plugins = []
            if S.name in SCENE_FX:
                plugins.append(SCENE_FX[S.name](env))
            plugins += [SKY_FX[k][1](env) for k in self.sky_fx]
            if self.weather_name in WEATHER:
                plugins.append(WEATHER[self.weather_name][1](env))
            self._fx = FxLayers()
            self._fx.set(plugins, env)
            self._fx_key = key
        else:
            self._fx.resize(env)
        return self._fx

    def _fx_step(self) -> None:
        """One timer step of the plug-ins (after the sim step)."""
        W, H = max(1, self.width()), max(1, self.height())
        fx = self.fx_layers(W, H)
        if fx is not None:
            fx.update(DT, self.fx_env(W, H))
