# Fireworks Simulator — Interface Map

Flat repo (modules import each other absolutely, e.g. `from models.particle import Particle`; run from the repo root).

## Desktop app

| File | Purpose | Key names |
|------|---------|-----------|
| `main.py` | Entry point: QApplication, main window | `main()` |
| `config.py` | Physics constants and window settings (Qt-free at import; QColor made lazily) | `FireworkConfig`, `DisplayConfig`, `DEFAULT_FIREWORK_RGB`, `DEFAULT_BACKGROUND_RGB`, `DEFAULT_LAUNCH_SPEED` |
| `ui_specs.py` | Qt-free control lists and slider specs, shared by `gui/controls.py` and `web/app.py` | `PATTERNS`, `BACKGROUNDS`, `WEATHER`, `SliderSpec`, `SLIDERS` |
| `models/particle.py` | One spark: velocity, gravity, 100-frame fade | `Particle` |
| `models/firework.py` | Rocket that climbs and bursts at its apex (gravity, launch speed, pattern) | `Firework` |
| `models/patterns.py` | Explosion shapes (one burst particle per point, `Firework._explode_pattern`) | `CirclePattern`, `HeartPattern`, `StarPattern`, `SpiralPattern`, `DoubleRingPattern`, `RandomPattern`, `TextPattern` |
| `models/glyphs.py` | 5 x 7 dot-matrix glyphs A-Z, 0-9 for `TextPattern` (also generated to `web/static/fw_glyphs.js`) | `GLYPHS`, `glyph_points()` |
| `effects/weather.py` | Rain, snow, fog, lightning (update + Qt drawing) | `RainEffect`, `SnowEffect`, `FogEffect`, `FogLayer`, `LightningEffect`, `LightningBolt` |
| `effects/backgrounds.py` | Night sky, cityscape, beach, forest scenes | `NightSkyBackground`, `CityscapeBackground`, `BeachBackground`, `ForestBackground` |
| `effects/mountains.py` | Mountain ranges with snow caps | `MountainsBackground` |
| `effects/particle_effects.py` | Smoke particles (not used by the app) | `SmokeEffect` |
| `gui/canvas.py` | Display widget: 60 fps timer, spawning, painting | `FireworksCanvas` |
| `gui/controls.py` | Control panel (signals) built from `ui_specs` | `ControlPanel` |
| `gui/main_window.py` | Main window, detachable tabs, menus, QSettings, signal wiring | `FireworksApp`, `DetachableTabWidget` |
| `utils/` | Colour (`ColorUtils.random_color`), math, physics, timing helpers | `ColorUtils`, `MathUtils`, `PhysicsUtils`, `TimeUtils` |
| `standalone/fireworks_app.py` | Older single-file version | — |

## Web: `web/` (no Qt imports)

| File | Purpose | Key names |
|------|---------|-----------|
| `app.py` | FastAPI: serves `static/`, API `/api/info`, `/defaults`, `/patterns`, `/reference`, `/reference/{name}`, `/reference/scenes` | `app`, `STATIC`, `STATIC_ENDPOINTS` |
| `reference.py` | Seeded runs of the real models with a mulberry32 `random` stand-in shared with JS | `PyRand`, `seeded()`, `run_show()`, `pattern_points()`, `weather_runs()`, `background_scenes()`, `fixture()` |
| `static/core.js`, `style.css` (kit) | Router, `api()`, `slider()`, `animate()`, `rng()`; shared theme | — |
| `static/fw_rand.js` | Python-`random`-shaped seeded RNG | `pyRand` |
| `static/fw_engine.js` | Port of particle/firework/canvas logic (+ web-only pattern bursts) | `CONFIG`, `Particle`, `Firework`, `Show` |
| `static/fw_glyphs.js` | Generated copy of `models/glyphs.py` (do not edit) | `GLYPHS` |
| `static/fw_patterns.js`, `fw_weather.js`, `fw_backgrounds.js`, `fw_color.js` | Ports of patterns, weather, scenes, `random_color` | `makePattern`, `makeWeather`, `makeBackground`, `randomColor` |
| `static/fw_reference.js` | Replays the reference runs, `maxDiff` | `runShow`, `weatherRuns`, `backgroundScenes` |
| `static/show_view.js`, `show_panel.js` | Canvas display + loop; control panel DOM | `ShowView`, `paint`, `buildPanel` |
| `static/home.js`, `show.js`, `patterns.js`, `verify.js`, `about.js` | Pages `#/`, `#/show`, `#/patterns`, `#/verify`, `#/about` | — |
| `static/main.js`, `static_api.js`, `index.html`, `style_app.css`, `icon.svg` | Entry, static-site API, shell, accent theme | — |
| `static/fw_engine.test.mjs`, `fw_scenes.test.mjs` | Node tests vs `tests/fixtures/fw_reference.json` | — |

## Scripts, tests, CI

| File | Purpose |
|------|---------|
| `run_web.py` | Web app on http://127.0.0.1:8125 |
| `scripts/build_static.py` | Export the static site to `site/` |
| `scripts/screenshots.py` | Playwright smoke test (`--static` / `--base`) and README images (`--shots` → `docs/img/`) |
| `scripts/make_js_fixtures.py` | Regenerate `tests/fixtures/fw_reference.json` and `web/static/fw_glyphs.js` (needs PyQt6) |
| `tests/test_config.py`, `test_math_utils.py`, `test_patterns.py`, `test_physics.py` | Pure-logic tests (need PyQt6 via package imports) |
| `tests/test_weather.py`, `test_canvas.py`, `test_backgrounds.py` | Regression tests of the 2026-11-11 fixes (offscreen Qt) |
| `tests/test_web.py` | API, static build, fixture current, node tests (runs without Qt) |
| `.github/workflows/pages.yml` | Test, build and publish the static site on push to `main` |

## Data flow

```
main.py ─▶ FireworksApp ─┬─ ControlPanel (ui_specs) ─ signals ─▶ FireworksCanvas setters
                         └─ FireworksCanvas ─ QTimer 16 ms ─▶ Firework.update() / Particle.update(), weather.update()
                                              paintEvent ─▶ background.draw, weather.draw, rockets + particles
Web: run_web.py ─▶ web.app ─ /api/defaults (config, ui_specs), /api/patterns, /api/reference (web/reference.py)
     browser: show.js ─▶ ShowView (fw_engine Show + fw_backgrounds + fw_weather) ─▶ canvas; show_panel.js controls
     scripts/build_static.py ─▶ site/ (static/ + api/*.json) ─▶ GitHub Pages (static_api.js answers api())
```
