"""The effects package must not depend on QtMultimedia (the unused sound manager was removed)."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestEffectsPackage(unittest.TestCase):

    def test_imports_without_qtmultimedia(self):
        code = ("import sys; sys.modules['PyQt6.QtMultimedia'] = None; sys.path.insert(0, %r); "
                "import effects; assert not hasattr(effects, 'SoundManager')" % ROOT)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_sound_module(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "effects", "sound.py")))


if __name__ == "__main__":
    unittest.main()
