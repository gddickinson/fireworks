"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# --- Fireworks specific -------------------------------------------------------------------------------------------
def test_defaults_come_from_python_modules():
    import config
    import ui_specs
    d = client.get("/api/defaults").json()
    assert d["firework"]["GRAVITY"] == config.FireworkConfig.GRAVITY
    assert d["firework"]["MAX_PARTICLES"] == config.FireworkConfig.MAX_PARTICLES
    assert d["firework_rgb"] == list(config.DEFAULT_FIREWORK_RGB)
    assert d["patterns"] == ui_specs.PATTERNS and d["backgrounds"] == ui_specs.BACKGROUNDS
    assert d["weather"] == ui_specs.WEATHER
    assert [s["key"] for s in d["sliders"]] == [s.key for s in ui_specs.SLIDERS]
    for s in d["sliders"]:
        assert s["lo"] <= s["default"] <= s["hi"], s
    assert client.get("/api/info").json()["patterns"] == 7


def test_patterns_and_reference_runs():
    pats = client.get("/api/patterns").json()
    assert {p["name"] for p in pats} >= {"Circle", "Heart", "Star", "Spiral", "Double Ring", "Text", "Random"}
    names = [c["name"] for c in client.get("/api/reference").json()]
    r = client.get(f"/api/reference/{names[0]}").json()
    assert len(r["snapshots"]) > 1 and r["snapshots"][-1]["fireworks"]
    assert client.get("/api/reference/nope").status_code == 404
    assert set(client.get("/api/reference/scenes").json()) == {"weather", "backgrounds", "colors"}


def _close(a, b, path="$"):
    """Recursive comparison allowing last-digit float differences between platforms (libm)."""
    if isinstance(a, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            _close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _close(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        assert abs(a - b) <= 1e-9 * max(1.0, abs(a)), (path, a, b)
    else:
        assert a == b, (path, a, b)


def test_js_fixture_is_current():
    """tests/fixtures/fw_reference.json must match a fresh run of the Python code (scripts/make_js_fixtures.py).
    The weather/background/colour part needs PyQt6 and is only re-checked where it is installed."""
    import json
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_js_fixtures
    from web.reference import fixture, has_qt
    committed = json.loads(make_js_fixtures.FIXTURE.read_text())
    fresh = json.loads(make_js_fixtures.dumps(fixture()))
    assert "qt" in committed
    if not has_qt():
        committed.pop("qt")
    _close(committed, fresh)
