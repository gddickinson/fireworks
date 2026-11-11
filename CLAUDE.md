# Fireworks Simulator

PyQt6 desktop app (`python main.py`) plus a web version (`web/`, `python run_web.py`, port 8125) whose JavaScript
port (`web/static/fw_*.js`) is node-tested against seeded runs of the Python models.

- Navigation map: @INTERFACE.md. Progress: SESSION_LOG.md.
- Tests: `QT_QPA_PLATFORM=offscreen python -m pytest -q` (needs PyQt6); CI runs only `tests/test_web.py` (no Qt).
- After changing `models/`, `effects/weather.py`, `effects/backgrounds.py`, `effects/mountains.py`, `utils/color.py`
  or `web/reference.py`: update the JS port and run `python scripts/make_js_fixtures.py` (needs PyQt6).
- Keep `config.py`, `models/` and `ui_specs.py` importable without Qt (the web app and CI rely on it).
- Files < 500 lines.
