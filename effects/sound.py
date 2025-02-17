# effects/sound.py
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl
import os

class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.load_sounds()

    def load_sounds(self):
        """Load sound effects"""
        sound_files = {
            'launch': 'launch.wav',
            'explosion': 'explosion.wav',
            'crackle': 'crackle.wav'
        }

        sound_dir = os.path.join(os.path.dirname(__file__), 'assets', 'sounds')

        for name, filename in sound_files.items():
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(os.path.join(sound_dir, filename)))
            effect.setVolume(0.5)
            self.sounds[name] = effect

    def play_launch(self):
        """Play launch sound"""
        if 'launch' in self.sounds:
            self.sounds['launch'].play()

    def play_explosion(self):
        """Play explosion sound"""
        if 'explosion' in self.sounds:
            self.sounds['explosion'].play()

    def play_crackle(self):
        """Play crackle sound"""
        if 'crackle' in self.sounds:
            self.sounds['crackle'].play()

    def set_volume(self, volume: float):
        """Set volume for all sounds (0.0 to 1.0)"""
        for effect in self.sounds.values():
            effect.setVolume(volume)

    def mute(self, muted: bool = True):
        """Mute/unmute all sounds"""
        for effect in self.sounds.values():
            effect.setMuted(muted)
