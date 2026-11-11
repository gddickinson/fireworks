"""Web interface for the Fireworks Simulator (no Qt needed).

Contents:
    app.py        FastAPI app: front end from static/, JSON API under /api (defaults and control specs from config.py
                  and ui_specs.py, pattern shapes from models/patterns.py, seeded reference runs); STATIC_ENDPOINTS are
                  exported by scripts/build_static.py for the GitHub Pages site.
    reference.py  Seeded runs of the real Python models with a mulberry32 stream shared with the JS port.
    static/       ES-module front end (no build step); fw_*.js is the JavaScript port of the display, checked by
                  fw_*.test.mjs against tests/fixtures/fw_reference.json.
"""
