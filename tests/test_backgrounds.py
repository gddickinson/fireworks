"""Regression tests for effects/mountains.py (offscreen Qt painting)."""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

from effects.mountains import MountainsBackground  # noqa: E402


class TestMountains(unittest.TestCase):

    def test_ranges_are_painted_in_their_blue_grey_colours(self):
        bg = MountainsBackground(400, 300)
        self.assertEqual([c.getRgb()[:3] for c in bg.colors], [(40, 40, 60), (50, 50, 70), (60, 60, 80)])
        img = QImage(400, 300, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0))
        p = QPainter(img)
        bg.draw(p)
        p.end()
        r, g, b, _ = img.pixelColor(200, 295).getRgb()  # bottom of the front range
        self.assertLess(max(r, g, b), 120, (r, g, b))      # was white-ish (the pen colour)
        self.assertGreater(b, r)

    def _render(self, bg):
        img = QImage(400, 300, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0))
        p = QPainter(img)
        bg.draw(p)
        p.end()
        return img

    def test_snow_caps_are_fixed_per_peak_not_redrawn_at_random(self):
        bg = MountainsBackground(400, 300)
        peaks = sum(1 for rng in bg.mountains for i in range(1, len(rng) - 1)
                    if rng[i][1] < rng[i - 1][1] and rng[i][1] < rng[i + 1][1])
        self.assertEqual(len(bg.snow_caps), peaks)
        self.assertTrue(all(20 <= w <= 40 for _, _, _, w in bg.snow_caps))
        self.assertEqual(self._render(bg), self._render(bg), "the scene changes between frames (flicker)")


if __name__ == "__main__":
    unittest.main()
