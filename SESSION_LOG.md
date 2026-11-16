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

## 2026-11-16 -- Realistic overhaul: engine, renderer, scenery, messages, sound, exports (branch `web-interface`)
- Realistic engine, Qt-free Python with a JS copy replaying seeded Python runs to <1e-9 relative
  (fw_pyro.test.mjs, Verify page): `models/pyro.py` (3-D metres, gravity + quadratic drag relative to the wind,
  tail sparks, crackle pops, crossette splits), `shell_types.py` (11 types + salutes, pattern and message shells),
  `director.py` (auto, ~40 s finale, message queue), `pyro_colors.py`. Fixture regenerated (`pyro` section); the
  fixture-currency test skips that section on CI (apex detection after libm maths is a discrete choice).
- Web: realistic display is the default (`real_view.js`): WebGL2 HDR renderer (`fw_render_gl.js`, `fw_shaders.js`)
  with trails, lit smoke, bloom, scene/sky light, water reflections, auto exposure, vignette, grain; Canvas 2D
  fallback; adaptive resolution/particle budget; reduced motion = still frame + Play, no strobe/flash.
  Classic (verified desktop port) kept as a renderer option.
- Scenery rewritten (`fw_scenery*.js`, `fw_noise.js`, seeded, painted once per size): airglow/light pollution,
  magnitude-distributed stars, Milky Way with dust lanes, fractal ridgelines with haze and snow, harbour skyline
  (setbacks, spires, antennas with aviation lights, sparse warm/cool windows, street lights), lake/sea with rippled
  reflections, conifers/broadleaf/palms, fireflies. The classic backgrounds (and their seeded checks) are unchanged.
- Messages page (`messages.js`, `fw_text.js`, `msg_link.js`): real fonts, wrap/fit, Unicode, colour modes, hold,
  sequences, presets, validated share link. Sound (`fw_audio.js`, off by default, distance delay).
- Exports (`fw_export.js`, `export_panel.js`, `gif_encoder.js`, `gif_worker.js`): PNG/WebP, GIF (own encoder,
  median-cut palette, frame differencing, worker), MP4/WebM via MediaRecorder, fixed-time-step capture, Web Share.
- Desktop: Realistic renderer (default in the window; `gui/canvas_real.py`, `real_show.py`, `real_painter.py`,
  `real_sprites.py`), shell type, finale, message text (`gui/text_points.py`), PNG/GIF export (`gui/export.py`,
  optional Pillow). Desktop keeps the classic backgrounds. `tests/conftest.py` redirects QSettings in all tests;
  George's plist unchanged (sha1 checked).
- Checks: pytest 101 passed; node 11+10+11+4+7; screenshots --static (10 routes) and --base (6 routes) all ok,
  phone 0 px (also show/messages at 390 px). Frame time: 16.7 ms median (vsync-bound), JS work 0.5-0.8 ms/frame
  WebGL, 2 ms Canvas2D, at up to 12.5k stars (headless Chrome, M1 Max).
