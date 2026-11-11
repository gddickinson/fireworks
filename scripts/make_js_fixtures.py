"""Write tests/fixtures/fw_reference.json: numbers from the real Python models (patterns, firework show, and, with
PyQt6 installed, weather, backgrounds and random colours) that the node tests (web/static/*.test.mjs) compare the
JavaScript port against.

Run after changing models/, effects/weather.py, effects/backgrounds.py, effects/mountains.py, utils/color.py or
web/reference.py (needs PyQt6 for the full fixture):
    python scripts/make_js_fixtures.py
Also writes web/static/fw_glyphs.js (the TextPattern glyphs of models/glyphs.py for the JS port).
tests/test_web.py fails if the committed fixture is out of date.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.reference import fixture, glyphs_js, has_qt  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "fw_reference.json"
GLYPHS_JS = ROOT / "web" / "static" / "fw_glyphs.js"


def dumps(data) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def main():
    if not has_qt():
        sys.exit("PyQt6 is needed for the weather/background/colour part of the fixture: pip install PyQt6")
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(dumps(fixture()))
    GLYPHS_JS.write_text(glyphs_js())
    print(f"wrote {FIXTURE} ({FIXTURE.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
