from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath, QPen
from PyQt6.QtCore import Qt, QPointF
import random
from typing import List, Tuple

class MountainsBackground:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.colors: List[QColor] = []  # one per range, filled by _generate_mountain_range
        self.mountains = self._generate_mountains()
        self.stars = self._generate_stars()

    def _generate_mountains(self) -> List[List[Tuple[float, float]]]:
        """Generate multiple mountain ranges with different heights and positions"""
        mountains = []
        
        # Far mountains (background)
        far_peaks = self._generate_mountain_range(
            peak_count=5,
            height_range=(0.3, 0.4),
            color=QColor(40, 40, 60)  # Dark blue-grey
        )
        mountains.append(far_peaks)
        
        # Middle mountains
        mid_peaks = self._generate_mountain_range(
            peak_count=4,
            height_range=(0.4, 0.5),
            color=QColor(50, 50, 70)  # Slightly lighter blue-grey
        )
        mountains.append(mid_peaks)
        
        # Near mountains (foreground)
        near_peaks = self._generate_mountain_range(
            peak_count=3,
            height_range=(0.45, 0.6),
            color=QColor(60, 60, 80)  # Lightest blue-grey
        )
        mountains.append(near_peaks)
        
        return mountains

    def _generate_mountain_range(
        self, 
        peak_count: int,
        height_range: Tuple[float, float],
        color: QColor
    ) -> List[Tuple[float, float]]:
        """Generate a single mountain range with multiple peaks"""
        self.colors.append(color)
        points = []
        segment_width = self.width / (peak_count - 1)
        
        # Start at the left edge
        points.append((0, self.height))
        
        # Generate peaks
        for i in range(peak_count):
            x = i * segment_width
            # Random height within the specified range
            height_factor = random.uniform(height_range[0], height_range[1])
            y = self.height * (1 - height_factor)
            points.append((x, y))
            
            # Add sub-peaks between main peaks
            if i < peak_count - 1:
                sub_peaks = random.randint(2, 4)
                for j in range(sub_peaks):
                    sub_x = x + segment_width * (j + 1) / (sub_peaks + 1)
                    # Sub-peaks are slightly lower than main peaks
                    sub_height_factor = height_factor * random.uniform(0.7, 0.9)
                    sub_y = self.height * (1 - sub_height_factor)
                    points.append((sub_x, sub_y))
        
        # End at the right edge
        points.append((self.width, self.height))
        
        # Sort points by x coordinate
        points.sort(key=lambda p: p[0])
        return points

    def _generate_stars(self) -> List[Tuple[float, float, float]]:
        """Generate random stars with positions and brightness"""
        stars = []
        star_count = int((self.width * self.height) / 2000)  # Adjust density as needed
        
        for _ in range(star_count):
            x = random.uniform(0, self.width)
            # Only place stars in the upper portion of the sky
            y = random.uniform(0, self.height * 0.7)
            brightness = random.uniform(0.3, 1.0)
            stars.append((x, y, brightness))
            
        return stars

    def draw(self, painter: QPainter):
        """Draw the complete mountain scene"""
        # Draw sky gradient
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, QColor(0, 0, 40))    # Dark blue at top
        gradient.setColorAt(0.5, QColor(20, 20, 60)) # Lighter blue in middle
        gradient.setColorAt(1, QColor(40, 40, 80))   # Lightest at bottom
        painter.fillRect(0, 0, self.width, self.height, gradient)

        # Draw stars
        for x, y, brightness in self.stars:
            color = QColor(255, 255, 255, int(255 * brightness))
            painter.setPen(color)
            painter.drawPoint(int(x), int(y))

        # Draw mountain ranges (from back to front)
        for mountain_range, base_color in zip(self.mountains, self.colors):
            # Create mountain shape
            path = QPainterPath()
            path.moveTo(QPointF(*mountain_range[0]))
            
            # Draw mountain outline
            for point in mountain_range[1:]:
                path.lineTo(QPointF(*point))
            
            # Fill mountains with gradient
            mountain_gradient = QLinearGradient(0, 0, 0, self.height)
            mountain_gradient.setColorAt(0, base_color.lighter(120))  # Lighter at top
            mountain_gradient.setColorAt(1, base_color.darker(120))   # Darker at bottom
            
            # Fill mountain shape
            painter.fillPath(path, mountain_gradient)
            
            # Draw snow caps on peaks
            snow_pen = QPen(QColor(255, 255, 255, 180), 2)
            painter.setPen(snow_pen)
            
            # Find peaks (local minima in y-coordinates)
            for i in range(1, len(mountain_range) - 1):
                prev_y = mountain_range[i-1][1]
                curr_y = mountain_range[i][1]
                next_y = mountain_range[i+1][1]
                
                if curr_y < prev_y and curr_y < next_y:
                    # This is a peak - add snow
                    x, y = mountain_range[i]
                    snow_width = random.uniform(20, 40)
                    snow_path = QPainterPath()
                    snow_path.moveTo(x - snow_width/2, y)
                    snow_path.quadTo(x, y - snow_width/4, x + snow_width/2, y)
                    painter.drawPath(snow_path)