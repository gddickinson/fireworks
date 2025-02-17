# utils/color_utils.py
from PyQt6.QtGui import QColor
from typing import List, Tuple
import random
import colorsys

class ColorUtils:
    @staticmethod
    def random_color(
        min_hue: float = 0.0,
        max_hue: float = 1.0,
        min_saturation: float = 0.5,
        max_saturation: float = 1.0,
        min_value: float = 0.5,
        max_value: float = 1.0
    ) -> QColor:
        """Generate a random color within given HSV ranges"""
        h = random.uniform(min_hue, max_hue)
        s = random.uniform(min_saturation, max_saturation)
        v = random.uniform(min_value, max_value)

        # Convert HSV to RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

        # Convert to 0-255 range
        return QColor(int(r * 255), int(g * 255), int(b * 255))

    @staticmethod
    def interpolate_color(
        color1: QColor,
        color2: QColor,
        factor: float
    ) -> QColor:
        """Interpolate between two colors"""
        r = int(color1.red() + (color2.red() - color1.red()) * factor)
        g = int(color1.green() + (color2.green() - color1.green()) * factor)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * factor)
        a = int(color1.alpha() + (color2.alpha() - color1.alpha()) * factor)
        return QColor(r, g, b, a)

    @staticmethod
    def create_gradient(
        start_color: QColor,
        end_color: QColor,
        steps: int
    ) -> List[QColor]:
        """Create a list of colors forming a gradient"""
        gradient = []
        for i in range(steps):
            factor = i / (steps - 1)
            gradient.append(ColorUtils.interpolate_color(start_color, end_color, factor))
        return gradient

    @staticmethod
    def complementary_color(color: QColor) -> QColor:
        """Get the complementary color"""
        # Convert to HSV
        h, s, v = color.getHsvF()[:3]

        # Add 0.5 to hue (180 degrees)
        h = (h + 0.5) % 1.0

        # Convert back to RGB
        return QColor.fromHsvF(h, s, v)

    @staticmethod
    def analogous_colors(
        color: QColor,
        angle: float = 30
    ) -> Tuple[QColor, QColor]:
        """Get analogous colors (colors adjacent on color wheel)"""
        h, s, v = color.getHsvF()[:3]

        # Convert angle to percentage of color wheel
        angle_factor = angle / 360

        # Calculate adjacent hues
        h1 = (h - angle_factor) % 1.0
        h2 = (h + angle_factor) % 1.0

        return (
            QColor.fromHsvF(h1, s, v),
            QColor.fromHsvF(h2, s, v)
        )
