"""Regression tests for effects/weather.py (resize and fog wrapping)."""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from effects.weather import FogEffect, FogLayer, RainEffect, SnowEffect  # noqa: E402


class TestWeatherResize(unittest.TestCase):

    def test_resize_to_same_size_keeps_particle_count(self):
        """FireworksCanvas.set_weather resizes right after creating the effect: that used to double the drops."""
        for cls, n in ((RainEffect, 100), (SnowEffect, 50)):
            eff = cls(800, 600)
            eff.resize(800, 600)
            self.assertEqual(len(eff.particles), n, cls.__name__)

    def test_resize_rescales_particle_positions(self):
        eff = RainEffect(800, 600)
        before = [(p.x, p.y) for p in eff.particles]
        eff.resize(1600, 1200)
        self.assertEqual(len(eff.particles), 100)
        for (x, y), p in zip(before, eff.particles):
            self.assertAlmostEqual(p.x, 2 * x)
            self.assertAlmostEqual(p.y, 2 * y)

    def test_fog_resize_scales_layers(self):
        fog = FogEffect(800, 600)
        widths = [layer.width for layer in fog.fog_layers]
        fog.resize(1600, 600)
        for w, layer in zip(widths, fog.fog_layers):
            self.assertAlmostEqual(layer.width, 2 * w)


class TestFogLayerWrap(unittest.TestCase):

    def test_control_points_move_with_the_layer_when_it_wraps(self):
        layer = FogLayer(0, 100, 400, 50)
        layer.velocity = 0.5
        offsets = [cx - layer.x for cx, _ in layer.control_points]
        layer.x = 801  # past the right edge of an 800 px window
        layer.control_points = [(layer.x + o, y) for o, (_, y) in zip(offsets, layer.control_points)]
        layer.update(800)
        self.assertEqual(layer.x, -400)
        for o, (cx, _) in zip(offsets, layer.control_points):
            self.assertAlmostEqual(cx - layer.x, o)


if __name__ == "__main__":
    unittest.main()
