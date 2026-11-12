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
- Open points from that session were decided by George (see below); launch-speed mapping kept.

## 2026-11-11 (later) -- Fixes approved by George (branch `web-interface`, after merge to main)
- Desktop burst now uses the chosen pattern (`Firework._explode_pattern`: one particle per pattern point,
  outermost at PARTICLE_SPEED_MAX x scale), the rule the web already used; web attaches the pattern after
  building the rocket as the canvas does. `tests/test_firework.py`; new seeded reference shows "star",
  "random_patterns", "text" (JS = Python to ~1e-15).
- Lightning branches fade with their main bolt (`TestLightningFade`).
- Text pattern: A-Z and 0-9 as 5 x 7 dot-matrix glyphs in `models/glyphs.py`; `web/static/fw_glyphs.js` is
  generated from it by `scripts/make_js_fixtures.py` and checked by `tests/test_web.py` (`TestTextPattern`).
- Removed unused `effects/sound.py` and its references (`tests/test_effects_package.py`); `_archive/` untouched.
- Checks: full suite 78 passed (offscreen Qt), test_web 19 passed (also without PyQt6), node 11 + 11,
  screenshots static/base all ok, phone 0 px; desktop text burst checked offscreen.
- Snow-cap flicker fixed (4497c37): cap widths drawn once per peak at scene generation (desktop and web,
  seeded check covers them); test_snow_caps_are_fixed_per_peak_not_redrawn_at_random. Suite 79 passed.
