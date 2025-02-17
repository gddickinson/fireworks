from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPainter, QPen, QColor
import random

from config import FireworkConfig, DisplayConfig
from models.firework import Firework

from utils.color import ColorUtils

from models.patterns import (
    Pattern, CirclePattern, HeartPattern, StarPattern,
    SpiralPattern, DoubleRingPattern, TextPattern, RandomPattern
)

from effects.weather import (
    WeatherEffect,
    RainEffect,
    SnowEffect,
    FogEffect,
    LightningEffect
)


from effects.backgrounds import (
    Background,
    NightSkyBackground,
    CityscapeBackground,
    MountainsBackground,
    BeachBackground,
    ForestBackground
)

class FireworksCanvas(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize display properties
        self.background_color = DisplayConfig().BACKGROUND_COLOR

        # Initialize fireworks properties
        self.fireworks = []
        self.particle_count = FireworkConfig.DEFAULT_PARTICLES
        self.firework_color = FireworkConfig().DEFAULT_COLOR
        self.use_random_colors = False  # Add this property

        # Initialize pattern properties
        self.pattern = None
        self.pattern_scale = 1.0
        self.pattern_rotation = 0.0
        self.pattern_options = {
            'star_points': 5,
            'spiral_arms': 3,
            'text': ""
        }
        self.use_random_patterns = False

        # Initialize effects
        self.background = None
        self.weather_effect = None

        # Set up animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(1000 // FireworkConfig.FRAME_RATE)

        # Set minimum size
        self.setMinimumSize(DisplayConfig.MIN_WINDOW_WIDTH,
                           DisplayConfig.MIN_WINDOW_HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), self.background_color)

        # Draw current background effect if any
        if self.background:
            self.background.draw(painter)

        # Draw weather effect if any
        if self.weather_effect:
            self.weather_effect.draw(painter)

        # Draw fireworks
        for firework in self.fireworks:
            if not firework.exploded:
                painter.setPen(QPen(firework.color, 4))
                painter.drawPoint(int(firework.x), int(firework.y))
            else:
                for particle in firework.particles:
                    color = particle.get_color()
                    painter.setPen(QPen(color, 2))
                    painter.drawPoint(int(particle.x), int(particle.y))

    def update_animation(self):
        """Update fireworks animation"""
        # Update existing fireworks
        self.fireworks = [fw for fw in self.fireworks if fw.update()]

        # Add new fireworks
        if random.random() < FireworkConfig.SPAWN_RATE:
            self.add_firework()

        # Update weather effect if any
        if self.weather_effect:
            self.weather_effect.update()

        # Trigger repaint
        self.update()

    def add_firework(self, x=None):
        """Add a new firework with the current pattern"""
        if x is None:
            x = random.randint(0, self.width())

        # Get color for the firework
        if self.use_random_colors:
            color = ColorUtils.random_color(
                min_saturation=0.7,
                min_value=0.8
            )
        else:
            color = self.firework_color

        # Create firework
        firework = Firework(x, self.height(), color, self.particle_count)

        # Apply pattern if one is set
        if self.pattern:
            if self.use_random_patterns:
                firework.pattern = RandomPattern()
            else:
                firework.pattern = self.pattern

        self.fireworks.append(firework)

    def set_particle_count(self, count: int):
        """Set the number of particles for new fireworks"""
        self.particle_count = count

    def set_firework_color(self, color: QColor):
        """Set the color for new fireworks"""
        self.firework_color = color

    def set_random_colors(self, enabled: bool):
        """Enable or disable random colors"""
        self.use_random_colors = enabled

    def set_pattern(self, pattern_name: str):
        """Set the explosion pattern based on pattern name"""
        if self.use_random_patterns:
            self.pattern = RandomPattern()
            return

        if pattern_name == "Random":
            self.pattern = RandomPattern()
        elif pattern_name == "Circle":
            self.pattern = CirclePattern(
                scale=self.pattern_scale,
                rotation=self.pattern_rotation
            )
        elif pattern_name == "Heart":
            self.pattern = HeartPattern(
                scale=self.pattern_scale,
                rotation=self.pattern_rotation
            )
        elif pattern_name == "Star":
            self.pattern = StarPattern(
                scale=self.pattern_scale,
                rotation=self.pattern_rotation,
                points=self.pattern_options['star_points']
            )
        elif pattern_name == "Spiral":
            self.pattern = SpiralPattern(
                scale=self.pattern_scale,
                rotation=self.pattern_rotation,
                arms=self.pattern_options['spiral_arms']
            )
        elif pattern_name == "Double Ring":
            self.pattern = DoubleRingPattern(
                scale=self.pattern_scale,
                rotation=self.pattern_rotation
            )
        elif pattern_name == "Text":
            self.pattern = TextPattern(
                text=self.pattern_options['text'],
                scale=self.pattern_scale
            )
        else:
            self.pattern = None

    def set_pattern_scale(self, scale: float):
        """Set the scale factor for patterns"""
        self.pattern_scale = scale
        if self.pattern and not self.use_random_patterns:
            self.pattern.scale = scale

    def set_pattern_rotation(self, rotation: float):
        """Set the rotation angle for patterns"""
        self.pattern_rotation = rotation
        if self.pattern and not self.use_random_patterns:
            self.pattern.rotation = rotation

    def set_pattern_option(self, option: str, value: any):
        """Set pattern-specific options"""
        self.pattern_options[option] = value
        # Update current pattern if it matches the option type
        if self.pattern:
            if isinstance(self.pattern, StarPattern) and option == 'star_points':
                self.pattern.num_points = value
            elif isinstance(self.pattern, SpiralPattern) and option == 'spiral_arms':
                self.pattern.arms = value

    def set_text_pattern(self, text: str):
        """Set the text for text pattern"""
        self.pattern_options['text'] = text
        if isinstance(self.pattern, TextPattern):
            self.pattern = TextPattern(
                text=text,
                scale=self.pattern_scale
            )

    def set_random_patterns(self, enabled: bool):
        """Enable or disable random patterns"""
        self.use_random_patterns = enabled
        if enabled:
            self.pattern = RandomPattern()

    def set_background(self, background_name: str):
        """Set the background effect based on the selected name"""
        if background_name == "Night Sky":
            self.background = NightSkyBackground(self.width(), self.height())
        elif background_name == "Cityscape":
            self.background = CityscapeBackground(self.width(), self.height())
        elif background_name == "Mountains":
            self.background = MountainsBackground(self.width(), self.height())
        elif background_name == "Beach":
            self.background = BeachBackground(self.width(), self.height())
        elif background_name == "Forest":
            self.background = ForestBackground(self.width(), self.height())
        else:
            self.background = None  # Clear background if none selected

    def set_weather(self, weather_name: str):
        """Set the weather effect based on the selected name"""
        if weather_name == "Rain":
            self.weather_effect = RainEffect(self.width(), self.height())
        elif weather_name == "Snow":
            self.weather_effect = SnowEffect(self.width(), self.height())
        elif weather_name == "Fog":
            self.weather_effect = FogEffect(self.width(), self.height())
        elif weather_name == "Lightning":
            self.weather_effect = LightningEffect(self.width(), self.height())

        elif weather_name == "None" or not weather_name:
            self.weather_effect = None

        # Recreate the effect when window is resized
        if self.weather_effect:
            self.weather_effect.resize(self.width(), self.height())

    def set_auto_launch(self, enabled: bool):
        """Enable or disable automatic launching"""
        if enabled:
            self.timer.start()
        else:
            self.timer.stop()

    def manual_launch(self):
        """Manually launch a firework"""
        self.add_firework()

    def set_text_pattern(self, text: str):
        """Set the text to be displayed in fireworks"""
        if not text:
            return

        # TODO: Implement text rendering to points
        # For now, just launch a regular firework
        self.add_firework()

    def set_launch_speed(self, speed: float):
        """Set the launch speed for new fireworks"""
        self.launch_speed = speed

    def set_gravity(self, gravity: float):
        """Set the gravity effect for particles"""
        self.gravity = gravity

    def resizeEvent(self, event):
        """Handle resize events to update background dimensions"""
        super().resizeEvent(event)
        # Recreate the background with new dimensions if one exists
        if self.background:
            current_type = type(self.background)
            self.background = current_type(self.width(), self.height())

    def reset_to_defaults(self):
        """Reset all canvas settings to default values"""
        # Reset firework properties
        self.particle_count = FireworkConfig.DEFAULT_PARTICLES
        self.firework_color = FireworkConfig().DEFAULT_COLOR
        self.use_random_colors = False

        # Reset pattern properties
        self.pattern = None
        self.pattern_scale = 1.0
        self.pattern_rotation = 0.0
        self.pattern_options = {
            'star_points': 5,
            'spiral_arms': 3,
            'text': ""
        }
        self.use_random_patterns = False

        # Reset effects
        self.background = None
        self.weather_effect = None

        # Clear existing fireworks
        self.fireworks.clear()

        # Ensure timer is running
        if not self.timer.isActive():
            self.timer.start()

        # Force a redraw
        self.update()
