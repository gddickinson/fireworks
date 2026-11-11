# Fireworks Simulator — Roadmap

## Current State
A well-structured PyQt6 fireworks simulation with modular architecture: `models/` (particle, firework, patterns), `effects/` (weather, backgrounds, particles), `gui/` (canvas, controls, main_window), and `utils/` (physics, color, math, time). Has a standalone version in `standalone/fireworks_app.py`. Good separation of concerns. Missing `requirements.txt` and no test suite.

## Short-term Improvements
- [x] Add `requirements.txt` with PyQt6 and any other dependencies pinned to versions
- [x] Remove `project-structure.py` and `init-files.py` — these are scaffolding scripts, not runtime code
- [x] Add unit tests for `utils/physics.py`, `utils/math.py`, and `models/patterns.py` (pure logic, easy to test)
- [ ] Add type hints throughout `models/particle.py` and `models/firework.py`
- [ ] Add docstrings to `gui/canvas.py` and `gui/controls.py` methods
- [x] Validate config values in `config.py` (e.g., particle count limits, FPS range)

## Feature Enhancements
- [ ] Add preset firework shows (choreographed sequences with timing)
- [ ] Implement sound effects tied to launches and explosions (the unused, file-less `effects/sound.py` was removed 2026-11-11)
- [ ] Add a recording/replay feature to save and replay firework shows
- [ ] Support custom color gradient palettes for explosions
- [ ] Add a performance monitor overlay (FPS, particle count)
- [ ] Implement multi-monitor support for the detachable panels

## Long-term Vision
- [ ] Add a timeline editor for scripting full firework shows with music sync
- [ ] Implement GPU-accelerated rendering (OpenGL) for higher particle counts
- [ ] Package as a standalone app with PyInstaller or cx_Freeze
- [ ] Add network mode for synchronized multi-display shows
- [ ] Export shows as video (ffmpeg integration)

## Technical Debt
- [ ] `standalone/fireworks_app.py` likely duplicates logic from the modular version — consolidate or remove
- [ ] `effects/mountains.py` exists separately from `effects/backgrounds.py` — merge or clarify the distinction
- [ ] No CI/CD pipeline or linting configuration
- [x] The `screenshots/` directory should be managed by `.gitignore` rules if auto-generated
- [x] Missing error handling for PyQt6 initialization failures in `main.py`
