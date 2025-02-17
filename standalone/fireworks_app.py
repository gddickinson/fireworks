import sys
import random
import math
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QSlider, QLabel, QComboBox, QPushButton,
                            QColorDialog)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient

class Particle:
    def __init__(self, x, y, angle, speed, color, lifetime=100):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.color = color
        self.lifetime = lifetime
        self.current_life = lifetime
        self.gravity = 0.1
        self.velocity_x = math.cos(angle) * speed
        self.velocity_y = math.sin(angle) * speed

    def update(self):
        self.velocity_y += self.gravity
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.current_life -= 1
        return self.current_life > 0

    def get_color(self):
        fade = self.current_life / self.lifetime
        return QColor(
            self.color.red(),
            self.color.green(),
            self.color.blue(),
            int(255 * fade)
        )

class Firework:
    def __init__(self, x, y, color, particle_count=50):
        self.x = x
        self.y = y
        self.color = color
        self.particles = []
        self.exploded = False
        self.velocity_y = -random.uniform(8, 12)
        self.particle_count = particle_count

    def explode(self):
        self.exploded = True
        for _ in range(self.particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            self.particles.append(Particle(self.x, self.y, angle, speed, self.color))

    def update(self):
        if not self.exploded:
            self.y += self.velocity_y
            self.velocity_y += 0.1
            if self.velocity_y >= 0:
                self.explode()
        else:
            self.particles = [p for p in self.particles if p.update()]
        return len(self.particles) > 0 or not self.exploded

class FireworksCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.fireworks = []
        self.background_color = QColor(0, 0, 0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)  # ~60 FPS
        self.particle_count = 50
        self.firework_color = QColor(255, 0, 0)
        self.pattern = None
        self.background = None

    def add_firework(self, x=None):
        if x is None:
            x = random.randint(0, self.width())
        self.fireworks.append(Firework(x, self.height(), 
                                     self.firework_color,
                                     self.particle_count))

    def update_animation(self):
        self.fireworks = [fw for fw in self.fireworks if fw.update()]
        if random.random() < 0.1:  # 10% chance each frame
            self.add_firework()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), self.background_color)

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

class FireworksApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fireworks Simulator")
        self.setGeometry(100, 100, 800, 600)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create canvas
        self.canvas = FireworksCanvas()
        layout.addWidget(self.canvas)

        # Create controls
        controls_layout = QHBoxLayout()

        # Particle count slider
        particle_layout = QVBoxLayout()
        particle_label = QLabel("Particle Count:")
        self.particle_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_slider.setRange(20, 200)
        self.particle_slider.setValue(50)
        self.particle_slider.valueChanged.connect(self.update_particle_count)
        particle_layout.addWidget(particle_label)
        particle_layout.addWidget(self.particle_slider)
        controls_layout.addLayout(particle_layout)

        # Color picker button
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        controls_layout.addWidget(self.color_button)

        # Pattern selector
        pattern_label = QLabel("Pattern:")
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["Random", "Circle", "Heart", "Text"])
        self.pattern_combo.currentTextChanged.connect(self.update_pattern)
        controls_layout.addWidget(pattern_label)
        controls_layout.addWidget(self.pattern_combo)

        # Background selector
        background_label = QLabel("Background:")
        self.background_combo = QComboBox()
        self.background_combo.addItems(["Night Sky", "Cityscape", "Mountains"])
        self.background_combo.currentTextChanged.connect(self.update_background)
        controls_layout.addWidget(background_label)
        controls_layout.addWidget(self.background_combo)

        layout.addLayout(controls_layout)

    def update_particle_count(self, value):
        self.canvas.particle_count = value

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.firework_color = color

    def update_pattern(self, pattern):
        self.canvas.pattern = pattern
        # Pattern implementation will be added later

    def update_background(self, background):
        self.canvas.background = background
        # Background implementation will be added later

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FireworksApp()
    window.show()
    sys.exit(app.exec())