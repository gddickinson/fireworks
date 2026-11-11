"""FastAPI web app for the Fireworks Simulator: serves the front end in static/ and the JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8125, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below.

Everything served here is read from the desktop app's own Qt-free modules: config.py (physics constants, default
colours, window sizes), ui_specs.py (the control panel's choice lists and slider ranges), models/patterns.py (the
explosion shapes) and web/reference.py (seeded runs of the real models for the Verify page).
"""
import ast
import json
import sys
from dataclasses import fields
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import ui_specs as U  # noqa: E402
from web.reference import SHOW_BY_NAME, SHOW_CASES, pattern_points, run_show  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
FIXTURE = ROOT / "tests" / "fixtures" / "fw_reference.json"
TITLE = "Fireworks Simulator"

app = FastAPI(title=TITLE)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _version() -> str:
    tree = ast.parse((ROOT / "__init__.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "__version__":
            return node.value.value
    return ""


def _consts(cls) -> dict:
    return {f.name: getattr(cls, f.name) for f in fields(cls) if not f.name.endswith("_COLOR")}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/info")
def info():
    """Project summary and counts for the home page."""
    return {
        "title": TITLE, "version": _version(),
        "summary": "A PyQt6-based interactive fireworks simulation application featuring realistic physics, "
                   "customizable effects, and a modular design.",
        "patterns": len(U.PATTERNS), "backgrounds": len(U.BACKGROUNDS),
        "weather": len([w for w in U.WEATHER if w != "None"]), "sliders": len(U.SLIDERS),
        "max_particles": config.FireworkConfig.MAX_PARTICLES, "frame_rate": config.FireworkConfig.FRAME_RATE,
    }


@app.get("/api/defaults")
def defaults():
    """Physics constants, default colours and window sizes (config.py) and the control specs (ui_specs.py)."""
    return {
        "firework": _consts(config.FireworkConfig),
        "display": _consts(config.DisplayConfig),
        "firework_rgb": list(config.DEFAULT_FIREWORK_RGB),
        "background_rgb": list(config.DEFAULT_BACKGROUND_RGB),
        "patterns": U.PATTERNS, "backgrounds": U.BACKGROUNDS, "weather": U.WEATHER,
        "sliders": U.specs_as_dicts(),
    }


@app.get("/api/patterns")
def patterns():
    """Points of each explosion pattern from models/patterns.py (centre 400, 300), incl. seeded RandomPatterns."""
    return pattern_points()


@app.get("/api/reference")
def reference_list():
    """The seeded firework-show runs."""
    return [{k: c[k] for k in ("name", "seed", "width", "height", "particles", "steps")} for c in SHOW_CASES]


@app.get("/api/reference/scenes")
def reference_scenes():
    """Weather, background and colour reference runs. They need PyQt6 (effects/ and utils/color.py import it), so
    they are read from the committed fixture written by scripts/make_js_fixtures.py."""
    data = json.loads(FIXTURE.read_text())
    if "qt" not in data:
        raise HTTPException(404, "fixture has no Qt reference runs")
    return data["qt"]


@app.get("/api/reference/{name}")
def reference(name: str):
    """A seeded run of the real Firework/Particle models in the canvas loop, snapshots every few frames."""
    if name not in SHOW_BY_NAME:
        raise HTTPException(404, f"unknown reference run {name!r}")
    return run_show(SHOW_BY_NAME[name])


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/defaults", "/patterns", "/reference", "/reference/scenes"] + [
    f"/reference/{c['name']}" for c in SHOW_CASES]
