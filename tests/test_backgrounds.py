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


if __name__ == "__main__":
    unittest.main()
