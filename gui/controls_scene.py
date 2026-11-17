"""Scene controls of the desktop control panel (gui/controls.py, Show group) for the realistic renderer with realistic
scenery: time of day, sky effects, ground devices; and the Background / Weather combos' lists, which offer the
realistic-only scenes (ui_specs.REAL_BACKGROUNDS) and weathers (ui_specs.REAL_WEATHER) only when the Realistic
renderer and Realistic scenery are both chosen (otherwise the classic ui_specs.BACKGROUNDS / WEATHER); and the
Rain / snow amount slider (ui_specs.WX_INTENSITY, the web's env.intensity) for the realistic weather."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QLabel, QPushButton, QSlider, QWidget

import ui_specs as U


def add_scene_controls(panel, layout) -> None:
    """Adds the time-of-day combo, sky-effect checkboxes and ground-device controls to `layout` (a QVBoxLayout of
    the Show group) and stores them on `panel` (a ControlPanel with the matching signals)."""
    panel.time_combo = QComboBox()
    panel.time_combo.addItems(U.TIMES_OF_DAY)
    panel.time_combo.setToolTip("Dusk: the blue hour, a warm afterglow and only the brightest stars")
    panel.time_combo.currentTextChanged.connect(panel.time_of_day_changed.emit)

    sky = QWidget()
    grid = QGridLayout(sky)
    grid.setContentsMargins(0, 0, 0, 0)
    panel.sky_checks = {}
    for i, (key, label) in enumerate(U.SKY_EFFECTS.items()):
        box = QCheckBox(label)
        box.toggled.connect(lambda _on, p=panel: p.sky_effects_changed.emit(p.sky_effects()))
        grid.addWidget(box, i // 2, i % 2)
        panel.sky_checks[key] = box

    panel.ground_check = QCheckBox("Ground effects")
    panel.ground_check.setToolTip("Gerbs, roman candles, mines and cakes in the show and the finale "
                                  "(a niagara curtain from the River Bridge)")
    panel.ground_check.toggled.connect(panel.ground_toggled.emit)
    panel.device_combo = QComboBox()
    panel.device_combo.addItems(U.GROUND_DEVICE_LABELS)
    panel.fire_button = QPushButton("Fire")
    panel.fire_button.clicked.connect(lambda: panel.ground_fire_requested.emit(panel.ground_device()))

    spec = U.WX_INTENSITY
    panel.wx_slider = QSlider(Qt.Orientation.Horizontal)
    panel.wx_slider.setRange(spec.lo, spec.hi)
    panel.wx_slider.setValue(spec.default)
    panel.wx_slider.setToolTip("How much rain or snow falls with the realistic weather")
    panel.wx_label = QLabel()
    panel.wx_slider.valueChanged.connect(lambda v: _wx_changed(panel, v))
    _wx_changed(panel, spec.default, emit=False)

    layout.addWidget(QLabel("Time of day:"))
    layout.addWidget(panel.time_combo)
    layout.addWidget(QLabel("Sky effects:"))
    layout.addWidget(sky)
    layout.addWidget(panel.wx_label)
    layout.addWidget(panel.wx_slider)
    layout.addWidget(panel.ground_check)
    layout.addWidget(panel.device_combo)
    layout.addWidget(panel.fire_button)

    panel.renderer_combo.currentTextChanged.connect(lambda _t: update_scene_lists(panel))
    panel.scenery_combo.currentTextChanged.connect(lambda _t: update_scene_lists(panel))


def weather_intensity(panel) -> float:
    return panel.wx_slider.value() * U.WX_INTENSITY.scale


def _wx_changed(panel, value: int, emit: bool = True) -> None:
    amount = value * U.WX_INTENSITY.scale
    panel.wx_label.setText(f"{U.WX_INTENSITY.label}: {round(amount * 100)}%")
    if emit:
        panel.weather_intensity_changed.emit(amount)


def realistic_scenes(panel) -> bool:
    return panel.renderer_combo.currentText() == "Realistic" and panel.scenery_combo.currentText() == "Realistic"


def _set_items(combo: QComboBox, items: list, fallback: str) -> None:
    """Replace the combo's items, keeping the current choice if it is still offered (one change signal at most)."""
    cur = combo.currentText()
    if [combo.itemText(i) for i in range(combo.count())] == items:
        return
    combo.blockSignals(True)
    combo.clear()
    combo.addItems(items)
    combo.setCurrentText(cur if cur in items else fallback)
    combo.blockSignals(False)
    if combo.currentText() != cur:
        combo.currentTextChanged.emit(combo.currentText())


def update_scene_lists(panel) -> None:
    real = realistic_scenes(panel)
    _set_items(panel.background_combo, U.REAL_BACKGROUNDS if real else U.BACKGROUNDS, U.BACKGROUNDS[0])
    _set_items(panel.weather_combo, U.REAL_WEATHER if real else U.WEATHER, "None")
    for w in [panel.time_combo, *panel.sky_checks.values(), panel.wx_slider]:
        w.setEnabled(real)
    on = panel.renderer_combo.currentText() == "Realistic"
    for w in (panel.ground_check, panel.device_combo, panel.fire_button):
        w.setEnabled(on)


def sky_effects(panel) -> list:
    return [k for k, box in panel.sky_checks.items() if box.isChecked()]


def ground_device(panel) -> str:
    return U.GROUND_DEVICES[max(0, panel.device_combo.currentIndex())]


def scene_values(panel) -> dict:
    return {"time_of_day": panel.time_combo.currentText(), "sky_effects": ",".join(sky_effects(panel)),
            "ground": panel.ground_check.isChecked(), "ground_device": ground_device(panel),
            "wx_intensity": weather_intensity(panel)}


def reset_scene_controls(panel) -> None:
    panel.time_combo.setCurrentText(U.TIMES_OF_DAY[0])
    for box in panel.sky_checks.values():
        box.setChecked(False)
    panel.ground_check.setChecked(False)
    panel.device_combo.setCurrentIndex(0)
    panel.wx_slider.setValue(U.WX_INTENSITY.default)


def load_scene_settings(panel, settings) -> None:
    """Restore the scene controls from QSettings (after the renderer/scenery combos, so the realistic-only
    background and weather lists are offered when they were saved)."""
    update_scene_lists(panel)
    for key, combo in (("background", panel.background_combo), ("weather", panel.weather_combo),
                       ("time_of_day", panel.time_combo)):
        if settings.contains(key):
            combo.setCurrentText(str(settings.value(key)))
    if settings.contains("sky_effects"):
        on = set(str(settings.value("sky_effects") or "").split(","))
        for key, box in panel.sky_checks.items():
            box.setChecked(key in on)
    if settings.contains("ground"):
        panel.ground_check.setChecked(settings.value("ground", type=bool))
    if settings.contains("wx_intensity"):
        spec = U.WX_INTENSITY
        v = round(float(settings.value("wx_intensity")) / spec.scale)
        panel.wx_slider.setValue(max(spec.lo, min(spec.hi, v)))
    if settings.contains("ground_device"):
        dev = str(settings.value("ground_device"))
        if dev in U.GROUND_DEVICES:
            panel.device_combo.setCurrentIndex(U.GROUND_DEVICES.index(dev))
