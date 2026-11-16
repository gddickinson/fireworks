# Fireworks Simulator — Interface Map

Flat repo (modules import each other absolutely, e.g. `from models.particle import Particle`; run from the repo root).

## Desktop app

| File | Purpose | Key names |
|------|---------|-----------|
| `main.py` | Entry point: QApplication, main window | `main()` |
| `config.py` | Physics constants and window settings (Qt-free at import; QColor made lazily) | `FireworkConfig`, `DisplayConfig`, `DEFAULT_FIREWORK_RGB`, `DEFAULT_BACKGROUND_RGB`, `DEFAULT_LAUNCH_SPEED` |
| `ui_specs.py` | Qt-free control lists and slider specs, shared by `gui/controls.py` and `web/app.py` | `PATTERNS`, `BACKGROUNDS`, `WEATHER`, `RENDERERS`, `SHELL_TYPES`, `SliderSpec`, `SLIDERS` |
| `models/particle.py` | One spark: velocity, gravity, 100-frame fade | `Particle` |
| `models/firework.py` | Rocket that climbs and bursts at its apex (gravity, launch speed, pattern) | `Firework` |
| `models/patterns.py` | Explosion shapes (one burst particle per point, `Firework._explode_pattern`) | `CirclePattern`, `HeartPattern`, `StarPattern`, `SpiralPattern`, `DoubleRingPattern`, `RandomPattern`, `TextPattern` |
| `models/pyro.py` | Realistic engine (Qt-free): 3-D shells/stars in metres, gravity + quadratic drag, tail sparks, crackle, crossette splits, events; camera geometry | `Sim`, `Star`, `sphere_dirs()`, `DT`, `G`, `FOCAL` |
| `models/shell_types.py` | Shell recipes and bursts: peony ... multi-break, salute, pattern, message | `TYPES`, `LABELS`, `make_recipe()`, `burst()` |
| `models/director.py` | Launch schedule: random auto launch, ~40 s finale programme, message shows | `Director`, `finale_cues()` |
| `models/pyro_colors.py` | Pyrotechnic palette; star colour/brightness over its life (ignition flash, cooling ember, strobe, glitter) | `PALETTE`, `pick_color()`, `star_rgb()` |
| `models/glyphs.py` | 5 x 7 dot-matrix glyphs A-Z, 0-9 for `TextPattern` (also generated to `web/static/fw_glyphs.js`) | `GLYPHS`, `glyph_points()` |
| `effects/weather.py` | Rain, snow, fog, lightning (update + Qt drawing) | `RainEffect`, `SnowEffect`, `FogEffect`, `FogLayer`, `LightningEffect`, `LightningBolt` |
| `effects/backgrounds.py` | Night sky, cityscape, beach, forest scenes | `NightSkyBackground`, `CityscapeBackground`, `BeachBackground`, `ForestBackground` |
| `effects/mountains.py` | Mountain ranges with snow caps | `MountainsBackground` |
| `effects/particle_effects.py` | Smoke particles (not used by the app) | `SmokeEffect` |
| `gui/canvas.py` | Display widget: 60 fps timer, spawning, painting; `renderer` "Classic" (constructor default) or "Realistic" | `FireworksCanvas` |
| `gui/canvas_real.py` | Realistic side of the canvas (mixin): settings → RealShow, click launch, finale, messages, `paint_real` | `RealisticMixin`, `TYPE_OF_LABEL` |
| `gui/real_show.py` | Qt-free realistic state: `Sim` + `Director` + burst lights; maps the classic sliders like the web | `RealShow`, `Light`, `HORIZON`, `BEACH_HORIZON` |
| `gui/real_painter.py` | QPainter renderer: scene, burst light, fading trail buffer with additive sprites, bloom, beach reflection, weather, vignette | `RealPainter`, `beach_water_path()` |
| `gui/real_sprites.py` | Soft radial-gradient star sprites cached per quantised colour/size | `SpriteCache` |
| `gui/text_points.py` | Message text → star points (QPainterPath.addText, staggered grid, rainbow) for `Director.queue_messages` | `text_points()`, `message()`, `clean_text()` |
| `gui/export.py` | File menu: frame as PNG, 5 s GIF at a fixed time step (optional Pillow) | `save_frame()`, `gif_frames()`, `export_gif()` |
| `gui/controls.py` | Control panel (signals) built from `ui_specs`; Show group: renderer, shell type, finale, message | `ControlPanel` |
| `gui/main_window.py` | Main window, detachable tabs, menus (incl. PNG/GIF export), QSettings, signal wiring | `FireworksApp`, `DetachableTabWidget` |
| `utils/` | Colour (`ColorUtils.random_color`), math, physics, timing helpers | `ColorUtils`, `MathUtils`, `PhysicsUtils`, `TimeUtils` |
| `standalone/fireworks_app.py` | Older single-file version | — |

## Web: `web/` (no Qt imports)

| File | Purpose | Key names |
|------|---------|-----------|
| `app.py` | FastAPI: serves `static/`, API `/api/info`, `/defaults`, `/patterns`, `/reference`, `/reference/{name}`, `/reference/scenes`, `/reference/pyro` | `app`, `STATIC`, `STATIC_ENDPOINTS` |
| `reference_pyro.py` | Seeded runs of the realistic engine (finale, auto, every type, heart pattern, message) | `PYRO_CASES`, `run_pyro()`, `message_points()`, `pyro_fixture()` |
| `reference.py` | Seeded runs of the real models with a mulberry32 `random` stand-in shared with JS | `PyRand`, `seeded()`, `run_show()`, `pattern_points()`, `weather_runs()`, `background_scenes()`, `fixture()` |
| `static/core.js`, `style.css` (kit) | Router, `api()`, `slider()`, `animate()`, `rng()`; shared theme | — |
| `static/fw_rand.js` | Python-`random`-shaped seeded RNG | `pyRand` |
| `static/fw_pyro.js`, `fw_shells.js`, `fw_director.js`, `fw_palette.js` | JS copies of `models/pyro.py`, `shell_types.py`, `director.py`, `pyro_colors.py` (same random order) | `Sim`, `Star`, `burst`, `Director`, `starRGB` |
| `static/fw_reference_pyro.js` | Replays the realistic reference runs (Verify page, node test) | `runPyro`, `messagePoints` |
| `static/real_view.js` | Realistic display: fixed-step loop, settings from the panel's `Show`, adaptive resolution/particle budget, events to listeners | `RealView`, `reducedMotion` |
| `static/fw_render_gl.js`, `fw_shaders.js` | WebGL2 renderer: HDR point sprites with fading trails, lit smoke, 3-level bloom, composite (scene light, water reflections, tone map, vignette, grain) | `GLRenderer` |
| `static/fw_render_2d.js` | Canvas 2D fallback of the same layers | `Canvas2DRenderer` |
| `static/fw_atmos.js` | Camera projection, particle list, burst lights, smoke puffs | `Camera`, `Atmos`, `buildParticles`, `STRIDE` |
| `static/fw_scenery.js`, `fw_scenery_parts.js`, `fw_noise.js` | Seeded procedural scenery painted once per size into back/front/material canvases (sky, stars, Milky Way, ridgelines, skyline, water, trees) | `buildScenery`, `SCENERY_HORIZON` |
| `static/fw_audio.js` | WebAudio launch thumps, booms, crackles with distance delay; MediaStream for video | `FireworkAudio` |
| `static/fw_text.js`, `msg_link.js` | Message text → star points (real fonts, wrap/fit, colour modes); validated share-link encode/decode | `textPoints`, `splitMessages`, `encodeQuery`, `decodeQuery` |
| `static/fw_export.js`, `export_panel.js`, `gif_encoder.js`, `gif_worker.js` | PNG/WebP, GIF (own LZW encoder, median-cut palette, frame differencing, Web Worker), MP4/WebM via MediaRecorder; Web Share | `recordGIF`, `recordVideo`, `GifWriter`, `encodeGIF`, `buildExportPanel` |
| `static/show_real_panel.js` | Display page "Show" group: renderer, shell type, finale, sound | `buildShowGroup`, `RENDERERS` |
| `static/messages.js` | Page `#/messages`: presets, options, live preview, link, exports | — |
| `static/fw_engine.js` | Port of particle/firework/canvas logic (+ web-only pattern bursts) | `CONFIG`, `Particle`, `Firework`, `Show` |
| `static/fw_glyphs.js` | Generated copy of `models/glyphs.py` (do not edit) | `GLYPHS` |
| `static/fw_patterns.js`, `fw_weather.js`, `fw_backgrounds.js`, `fw_color.js` | Ports of patterns, weather, scenes, `random_color` | `makePattern`, `makeWeather`, `makeBackground`, `randomColor` |
| `static/fw_reference.js` | Replays the reference runs, `maxDiff` | `runShow`, `weatherRuns`, `backgroundScenes` |
| `static/show_view.js`, `show_panel.js` | Classic canvas display + loop; control panel DOM (used by both renderers) | `ShowView`, `paint`, `buildPanel` |
| `static/home.js`, `show.js`, `patterns.js`, `verify.js`, `about.js` | Pages `#/`, `#/show`, `#/patterns`, `#/verify`, `#/about` | — |
| `static/main.js`, `static_api.js`, `index.html`, `style_app.css`, `icon.svg` | Entry, static-site API, shell, accent theme | — |
| `static/fw_engine.test.mjs`, `fw_scenes.test.mjs`, `fw_pyro.test.mjs` | Node tests vs `tests/fixtures/fw_reference.json` | — |
| `static/fw_text.test.mjs`, `gif_encoder.test.mjs` | Node tests: message text and share link; GIF encoder (own decoder, round trips) | — |

## Scripts, tests, CI

| File | Purpose |
|------|---------|
| `run_web.py` | Web app on http://127.0.0.1:8125 |
| `scripts/build_static.py` | Export the static site to `site/` |
| `scripts/screenshots.py` | Playwright smoke test (`--static` / `--base`) and README images (`--shots` → `docs/img/`) |
| `scripts/make_js_fixtures.py` | Regenerate `tests/fixtures/fw_reference.json` and `web/static/fw_glyphs.js` (needs PyQt6) |
| `tests/test_config.py`, `test_math_utils.py`, `test_patterns.py`, `test_physics.py` | Pure-logic tests (need PyQt6 via package imports) |
| `tests/test_weather.py`, `test_canvas.py`, `test_backgrounds.py` | Regression tests of the 2026-11-11 fixes (offscreen Qt) |
| `tests/test_pyro.py` | Realistic engine physics and shell behaviour (Qt-free) |
| `tests/test_real_canvas.py` | Desktop realistic mode, text sampler, PNG/GIF export (offscreen Qt) |
| `tests/conftest.py` | Points the main window's QSettings at a temp INI file in every test |
| `tests/test_web.py` | API, static build, fixture current (realistic runs skipped on CI), node tests (runs without Qt) |
| `.github/workflows/pages.yml` | Test, build and publish the static site on push to `main` |

## Data flow

```
main.py ─▶ FireworksApp ─┬─ ControlPanel (ui_specs) ─ signals ─▶ FireworksCanvas setters
                         └─ FireworksCanvas ─ QTimer 16 ms ─▶ Firework.update() / Particle.update(), weather.update()
                                              paintEvent ─▶ background.draw, weather.draw, rockets + particles
Web: run_web.py ─▶ web.app ─ /api/defaults (config, ui_specs), /api/patterns, /api/reference (web/reference.py)
     browser: show.js ─▶ RealView (fw_director ─▶ fw_pyro/fw_shells; fw_scenery; fw_atmos ─▶ GLRenderer | Canvas2DRenderer)
              or ShowView (classic: fw_engine Show + fw_backgrounds + fw_weather) ─▶ canvas; show_panel.js controls
              messages.js ─▶ fw_text points ─▶ Director.queueMessages; export_panel ─▶ fw_export (gif_worker, MediaRecorder)
     scripts/build_static.py ─▶ site/ (static/ + api/*.json) ─▶ GitHub Pages (static_api.js answers api())
```
