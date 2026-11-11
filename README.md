# Fireworks Simulator

A PyQt6-based interactive fireworks simulation application featuring realistic physics, customizable effects, and a modular design.

![Fireworks Demo](screenshots/demo.gif)

## Features

### Firework Effects
- Realistic particle physics simulation
- Customizable particle count and colors
- Explosion pattern shapes (`models/patterns.py`), selectable in the control panel:
  - Circle
  - Heart
  - Star (customizable points)
  - Spiral (adjustable arms)
  - Double Ring
  - Text (only the letter A has a shape so far)
- Random pattern generation
- Adjustable scale and rotation for patterns
- Note: the desktop burst (`Firework.explode()`) does not use the selected pattern yet; every rocket bursts
  into a uniform random spray. The web version below draws the pattern shapes.
- Adjustable gravity and launch speed for new rockets

### Weather Effects
- Rain (intensity parameter in `RainEffect`, not in the control panel)
- Snow with wind effects
- Dynamic fog with layered opacity
- Lightning with realistic branching

### Backgrounds
- Night sky with stars
- Cityscape with illuminated windows
- Mountain range with snow caps
- Beach scene with animated waves
- Forest with fireflies

### User Interface
- Detachable display and control panels
- Real-time parameter adjustment
- Customizable launch controls
- Pattern randomization options
- Intuitive color selection

## Installation

### Prerequisites
- Python 3.11 or higher
- PyQt6

### Basic Installation
1. Clone the repository:
```bash
git clone https://github.com/gddickinson/fireworks.git
cd fireworks
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
python main.py
```

## Usage

### Basic Controls
- **Launch**: auto-launch, or untick Auto Launch and use the Launch Firework button
- **Colors**: Choose specific colors or enable random colors
- **Patterns**: Select predefined patterns or create custom ones
- **Weather**: Toggle different weather effects
- **Backgrounds**: Choose from various scene backgrounds

### Advanced Features
- **Double-click** tabs to detach display or control panels
- **Adjust parameters** in real-time:
  - Particle count
  - Launch speed
  - Gravity effect
  - Pattern scale/rotation
- **Customize patterns** with specific options for each type
- **Save settings** for future sessions

### Keyboard Shortcuts
- `Ctrl+S`: Save current settings
- `Ctrl+R`: Reset to defaults
- `F11`: Toggle fullscreen
- `Ctrl+T`: Toggle control panel
- `Ctrl+Q`: Quit application

## Project Structure
```
fireworks/
├── config.py               # Configuration settings
├── effects/               # Special effects modules
│   ├── backgrounds.py     # Background scenes
│   ├── particle_effects.py # Particle system
│   ├── sound.py          # Sound effects
│   └── weather.py        # Weather effects
├── gui/                  # User interface components
│   ├── canvas.py        # Display canvas
│   ├── controls.py      # Control panel
│   └── main_window.py   # Main application window
├── models/              # Core simulation models
│   ├── firework.py     # Firework behavior
│   ├── particle.py     # Particle physics
│   └── patterns.py     # Explosion patterns
├── utils/              # Utility functions
│   ├── color.py       # Color management
│   ├── math.py        # Mathematical utilities
│   ├── physics.py     # Physics calculations
│   └── time.py        # Timing utilities
└── main.py            # Application entry point
```

## Configuration

### Display Settings
Edit `config.py` to modify default values:
- Window dimensions
- Frame rate
- Particle limits
- Default colors
- Physics parameters

### Custom Patterns
Add new patterns by:
1. Subclassing the `Pattern` class in `patterns.py`
2. Implementing the `get_points()` method
3. Registering the pattern in the control panel

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add docstrings for new functions/classes
- Include type hints
- Write unit tests for new features
- Update documentation as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Contact

george.dickinson@gmail.com

Project Link: [https://github.com/gddickinson/fireworks](https://github.com/gddickinson/fireworks)
