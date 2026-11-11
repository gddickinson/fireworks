# Session Log

## 2026-11-11 -- Web interface, static GitHub Pages site and bug fixes (branch `web-interface`)
- Web app (`web/`, `run_web.py`, port 8125) and static site from the shared web kit: Display, Patterns,
  Python vs JS, About. `web/static/fw_*.js` ports the models, canvas loop, weather, scenes and random colours;
  node tests replay seeded Python runs (`web/reference.py` swaps `random` for a mulberry32 `PyRand`) and agree to
  ~1e-15 relative (shows, patterns) or exactly (weather, scenes, colours).
- Qt-free imports for the web/CI: `config.py`, `models/particle.py`, `models/firework.py` import QColor lazily;
  new `ui_specs.py` (choice lists, slider specs) used by `gui/controls.py`; root `__init__.py` tolerates a missing
  PyQt6. Desktop app checked offscreen; installed PyQt6==6.9.1 in the shared venv to run the existing tests.
- Bugs fixed (each with a regression test written to fail first, own "Fix ..." commit):
  - Weather resize doubled rain/snow particles and never rescaled; fog resize scale was always 1; fog control
    points did not wrap with their layer (`tests/test_weather.py`).
  - Gravity and Launch Speed sliders were not connected; Auto Launch off froze the whole animation; a duplicate
    `set_text_pattern` stub launched a firework per keystroke; canvas started without the background/pattern the
    controls showed (`tests/test_canvas.py`). Zero-gravity rockets are dropped above the window.
  - Mountains drawn in the pen's white instead of their blue-grey (`tests/test_backgrounds.py`).
  - HeartPattern upside down on screen (`tests/test_patterns.py`).
  - README claims corrected (weather transitions, twinkling, click to launch, text pattern, clone dir, link).
- Needs George's decision: whether/how `Firework.explode()` should use the selected pattern (web uses one particle
  per pattern point, outermost at PARTICLE_SPEED_MAX x scale); lightning branches never fade; snow caps re-drawn
  with a new random width every frame (flicker); `effects/sound.py` unused and sound files missing; Text pattern
  only knows the letter A.
