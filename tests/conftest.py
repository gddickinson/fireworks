"""Shared test setup: the desktop main window's QSettings go to a temporary INI file in every test, so no test can
read or write the user's real settings (macOS plist / registry). No-op where PyQt6 is not installed (CI web tests)."""
import pytest


@pytest.fixture(autouse=True)
def _temporary_qsettings(tmp_path, monkeypatch):
    try:
        from PyQt6.QtCore import QSettings
        from gui import main_window
    except ImportError:
        yield
        return
    ini = str(tmp_path / "settings.ini")
    monkeypatch.setattr(main_window, "QSettings", lambda *a: QSettings(ini, QSettings.Format.IniFormat))
    yield
