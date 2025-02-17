import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSlider,
                            QLabel, QComboBox, QPushButton, QColorDialog,
                            QSpinBox, QGroupBox, QCheckBox, QGridLayout,
                            QStackedWidget, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from config import FireworkConfig, DisplayConfig

class ControlPanel(QWidget):
    # Signal definitions
    particle_count_changed = pyqtSignal(int)
    color_changed = pyqtSignal(QColor)
    pattern_changed = pyqtSignal(str)
    background_changed = pyqtSignal(str)
    launch_speed_changed = pyqtSignal(float)
    gravity_changed = pyqtSignal(float)
    auto_launch_toggled = pyqtSignal(bool)
    weather_changed = pyqtSignal(str)
    text_pattern_changed = pyqtSignal(str)
    random_colors_toggled = pyqtSignal(bool)

    # Pattern-specific signals
    pattern_option_signal = pyqtSignal(str, int)  # (option_name, value)
    pattern_scale_signal = pyqtSignal(float)
    pattern_rotation_signal = pyqtSignal(float)
    pattern_random_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the complete control panel UI"""
        main_layout = QVBoxLayout(self)

        # Create horizontal layouts for different control groups
        top_controls = QHBoxLayout()
        bottom_controls = QHBoxLayout()

        # Add control groups
        top_controls.addWidget(self.create_particle_controls())
        top_controls.addWidget(self.create_color_controls())
        top_controls.addWidget(self.create_pattern_controls())

        bottom_controls.addWidget(self.create_physics_controls())
        bottom_controls.addWidget(self.create_background_controls())
        bottom_controls.addWidget(self.create_launch_controls())

        main_layout.addLayout(top_controls)
        main_layout.addLayout(bottom_controls)

    def create_particle_controls(self) -> QGroupBox:
        """Create particle count and size control group"""
        group = QGroupBox("Particle Controls")
        layout = QVBoxLayout()

        # Particle count slider
        count_label = QLabel("Particle Count:")
        self.particle_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_slider.setRange(FireworkConfig.MIN_PARTICLES,
                                    FireworkConfig.MAX_PARTICLES)
        self.particle_slider.setValue(FireworkConfig.DEFAULT_PARTICLES)
        self.particle_slider.valueChanged.connect(self.particle_count_changed.emit)

        # Add value display
        self.count_display = QLabel(str(FireworkConfig.DEFAULT_PARTICLES))
        self.particle_slider.valueChanged.connect(
            lambda v: self.count_display.setText(str(v)))

        layout.addWidget(count_label)
        layout.addWidget(self.particle_slider)
        layout.addWidget(self.count_display)
        group.setLayout(layout)
        return group

    def create_color_controls(self) -> QGroupBox:
        """Create color selection control group"""
        group = QGroupBox("Color Controls")
        layout = QVBoxLayout()

        # Color picker button
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.show_color_dialog)

        # Random color checkbox
        self.random_color = QCheckBox("Random Colors")
        self.random_color.toggled.connect(self.random_colors_toggled.emit)
        self.random_color.toggled.connect(self.toggle_color_button)

        layout.addWidget(self.color_button)
        layout.addWidget(self.random_color)
        group.setLayout(layout)
        return group

    def create_pattern_controls(self) -> QGroupBox:
        """Create pattern selection and customization controls"""
        group = QGroupBox("Pattern Controls")
        layout = QVBoxLayout()

        # Pattern type selector
        pattern_layout = QHBoxLayout()
        pattern_label = QLabel("Pattern:")
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Random",
            "Circle",
            "Heart",
            "Star",
            "Spiral",
            "Double Ring",
            "Text"
        ])
        pattern_layout.addWidget(pattern_label)
        pattern_layout.addWidget(self.pattern_combo)
        layout.addLayout(pattern_layout)

        # Random patterns checkbox
        self.random_patterns = QCheckBox("Randomize Patterns")
        self.random_patterns.toggled.connect(self.toggle_pattern_controls)
        self.random_patterns.toggled.connect(self.pattern_random_toggled)
        layout.addWidget(self.random_patterns)

        # Pattern customization controls
        self.pattern_options = QWidget()
        options_layout = QGridLayout(self.pattern_options)

        # Scale control
        scale_label = QLabel("Scale:")
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(100)
        self.scale_value = QLabel("1.0")
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_value.setText(f"{v/100:.1f}")
        )
        self.scale_slider.valueChanged.connect(
            lambda v: self.pattern_scale_signal.emit(v/100)
        )
        options_layout.addWidget(scale_label, 0, 0)
        options_layout.addWidget(self.scale_slider, 0, 1)
        options_layout.addWidget(self.scale_value, 0, 2)

        # Rotation control
        rotation_label = QLabel("Rotation:")
        self.rotation_slider = QSlider(Qt.Orientation.Horizontal)
        self.rotation_slider.setRange(0, 360)
        self.rotation_slider.setValue(0)
        self.rotation_value = QLabel("0°")
        self.rotation_slider.valueChanged.connect(
            lambda v: self.rotation_value.setText(f"{v}°")
        )
        self.rotation_slider.valueChanged.connect(
            lambda v: self.pattern_rotation_signal.emit(math.radians(v))
        )
        options_layout.addWidget(rotation_label, 1, 0)
        options_layout.addWidget(self.rotation_slider, 1, 1)
        options_layout.addWidget(self.rotation_value, 1, 2)

        # Pattern-specific controls
        self.pattern_specific = QStackedWidget()

        # Star pattern controls
        star_widget = QWidget()
        star_layout = QGridLayout(star_widget)
        points_label = QLabel("Points:")
        self.star_points = QSpinBox()
        self.star_points.setRange(3, 12)
        self.star_points.setValue(5)
        star_layout.addWidget(points_label, 0, 0)
        star_layout.addWidget(self.star_points, 0, 1)
        self.pattern_specific.addWidget(star_widget)

        # Spiral pattern controls
        spiral_widget = QWidget()
        spiral_layout = QGridLayout(spiral_widget)
        arms_label = QLabel("Arms:")
        self.spiral_arms = QSpinBox()
        self.spiral_arms.setRange(1, 8)
        self.spiral_arms.setValue(3)
        spiral_layout.addWidget(arms_label, 0, 0)
        spiral_layout.addWidget(self.spiral_arms, 0, 1)
        self.pattern_specific.addWidget(spiral_widget)

        # Text pattern controls
        text_widget = QWidget()
        text_layout = QGridLayout(text_widget)
        text_label = QLabel("Text:")
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text...")
        text_layout.addWidget(text_label, 0, 0)
        text_layout.addWidget(self.text_input, 0, 1)
        self.pattern_specific.addWidget(text_widget)

        # Add pattern-specific controls to layout
        options_layout.addWidget(self.pattern_specific, 2, 0, 1, 3)
        layout.addWidget(self.pattern_options)

        # Connect signals
        self.pattern_combo.currentTextChanged.connect(self.on_pattern_changed)
        self.star_points.valueChanged.connect(self.pattern_option_changed)
        self.spiral_arms.valueChanged.connect(self.pattern_option_changed)
        self.text_input.textChanged.connect(self.text_pattern_changed)

        group.setLayout(layout)
        return group

    def toggle_pattern_controls(self, enabled: bool):
        """Enable/disable pattern customization controls"""
        self.pattern_options.setEnabled(not enabled)
        if enabled:
            self.pattern_combo.setCurrentText("Random")

    def on_pattern_changed(self, pattern_name: str):
        """Handle pattern type changes"""
        # Emit the pattern change signal
        self.pattern_changed.emit(pattern_name)

        # Show appropriate pattern-specific controls
        if pattern_name == "Star":
            self.pattern_specific.setCurrentIndex(0)  # Star controls
            self.pattern_specific.setVisible(True)
        elif pattern_name == "Spiral":
            self.pattern_specific.setCurrentIndex(1)  # Spiral controls
            self.pattern_specific.setVisible(True)
        elif pattern_name == "Text":
            self.pattern_specific.setCurrentIndex(2)  # Text controls
            self.pattern_specific.setVisible(True)
        else:
            self.pattern_specific.setVisible(False)

        # Enable/disable options based on pattern type
        has_options = pattern_name in ["Star", "Spiral", "Text"]
        self.pattern_options.setEnabled(has_options and not self.random_patterns.isChecked())

    def pattern_option_changed(self):
        """Handle changes to pattern-specific options"""
        current_pattern = self.pattern_combo.currentText()

        if current_pattern == "Star":
            self.pattern_option_signal.emit("star_points", self.star_points.value())
        elif current_pattern == "Spiral":
            self.pattern_option_signal.emit("spiral_arms", self.spiral_arms.value())


    def create_physics_controls(self) -> QGroupBox:
        """Create physics parameter control group"""
        group = QGroupBox("Physics Controls")
        layout = QVBoxLayout()

        # Gravity control
        gravity_label = QLabel("Gravity:")
        self.gravity_slider = QSlider(Qt.Orientation.Horizontal)
        self.gravity_slider.setRange(0, 100)  # 0.0 to 1.0 in steps of 0.01
        self.gravity_slider.setValue(int(FireworkConfig.GRAVITY * 100))
        self.gravity_slider.valueChanged.connect(
            lambda v: self.gravity_changed.emit(v / 100))

        # Launch speed control
        speed_label = QLabel("Launch Speed:")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)  # 5.0 to 20.0 in steps of 0.1
        self.speed_slider.setValue(100)  # Default 10.0
        self.speed_slider.valueChanged.connect(
            lambda v: self.launch_speed_changed.emit(v / 10))

        layout.addWidget(gravity_label)
        layout.addWidget(self.gravity_slider)
        layout.addWidget(speed_label)
        layout.addWidget(self.speed_slider)
        group.setLayout(layout)
        return group

    def create_background_controls(self) -> QGroupBox:
        """Create background and weather control group"""
        group = QGroupBox("Background Controls")
        layout = QVBoxLayout()

        # Background scene selector
        background_label = QLabel("Background:")
        self.background_combo = QComboBox()
        self.background_combo.addItems([
            "Night Sky",
            "Cityscape",
            "Mountains",
            "Beach",
            "Forest"
        ])
        self.background_combo.currentTextChanged.connect(self.background_changed.emit)

        # Weather effect selector
        weather_label = QLabel("Weather Effect:")
        self.weather_combo = QComboBox()
        self.weather_combo.addItems([
            "None",
            "Rain",
            "Snow",
            "Fog",
            "Lightning"
        ])
        self.weather_combo.currentTextChanged.connect(self.weather_changed.emit)

        layout.addWidget(background_label)
        layout.addWidget(self.background_combo)
        layout.addWidget(weather_label)
        layout.addWidget(self.weather_combo)
        group.setLayout(layout)
        return group

    def create_launch_controls(self) -> QGroupBox:
        """Create firework launch control group"""
        group = QGroupBox("Launch Controls")
        layout = QVBoxLayout()

        # Auto-launch toggle
        self.auto_launch = QCheckBox("Auto Launch")
        self.auto_launch.setChecked(True)
        self.auto_launch.toggled.connect(self.auto_launch_toggled.emit)

        # Manual launch button
        self.launch_button = QPushButton("Launch Firework")
        self.launch_button.setEnabled(False)
        self.auto_launch.toggled.connect(
            lambda checked: self.launch_button.setEnabled(not checked))

        layout.addWidget(self.auto_launch)
        layout.addWidget(self.launch_button)
        group.setLayout(layout)
        return group

    def show_color_dialog(self):
        """Show color picker dialog and emit selected color"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_changed.emit(color)
            self.color_button.setStyleSheet(
                f"background-color: {color.name()};"
            )

    def toggle_color_button(self, random_enabled: bool):
        """Enable/disable color picker based on random color checkbox"""
        self.color_button.setEnabled(not random_enabled)
        if random_enabled:
            self.color_button.setStyleSheet("")

    def get_current_values(self) -> dict:
        """Get current values of all controls"""
        return {
            'particle_count': self.particle_slider.value(),
            'pattern': self.pattern_combo.currentText(),
            'background': self.background_combo.currentText(),
            'weather': self.weather_combo.currentText(),
            'gravity': self.gravity_slider.value() / 100,
            'launch_speed': self.speed_slider.value() / 10,
            'auto_launch': self.auto_launch.isChecked(),
            'random_colors': self.random_color.isChecked()
        }

    def reset_to_defaults(self):
        """Reset all controls to their default values"""
        self.particle_slider.setValue(FireworkConfig.DEFAULT_PARTICLES)
        self.pattern_combo.setCurrentText("Random")
        self.background_combo.setCurrentText("Night Sky")
        self.weather_combo.setCurrentText("None")
        self.gravity_slider.setValue(int(FireworkConfig.GRAVITY * 100))
        self.speed_slider.setValue(100)
        self.auto_launch.setChecked(True)
        self.random_color.setChecked(False)
        self.color_button.setStyleSheet("")
