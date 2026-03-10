"""
audio.py — SoundManager for Game of Karen.
"""
from __future__ import annotations
import os
import pygame

_AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "..", "audio")
_THEME_FILE = "theme_music_infected_vibes"
_BOSS_FILE  = "boss_arrives" # The key for your boss music file

class SoundManager:
    """Loads and plays all game audio with strict channel management."""

    def __init__(self) -> None:
        self._enabled = pygame.mixer.get_init() is not None
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_files: dict[str, str] = {}

        if not self._enabled:
            return

        audio_dir = os.path.abspath(_AUDIO_DIR)
        for fname in os.listdir(audio_dir):
            if not fname.lower().endswith(".mp3"):
                continue
            key = os.path.splitext(fname)[0]
            path = os.path.join(audio_dir, fname)
            
            if key == _THEME_FILE or key == _BOSS_FILE:
                self._music_files[key] = path
            else:
                try:
                    self._sfx[key] = pygame.mixer.Sound(path)
                except:
                    pass

    def play_sfx(self, key: str) -> None:
        """Finds an available channel or kicks out an old sound to play a new one."""
        if not self._enabled: return
        sound = self._sfx.get(key)
        if sound:
            # ── CHANNEL REUSE AUDIT ──────────────────────────────────
            # fade_ms=50 prevents 'popping' when a sound is cut off
            # .play() returns the channel used; find_channel(True) forces reuse
            chan = pygame.mixer.find_channel(True)
            if chan:
                chan.play(sound, fade_ms=50)
            # ─────────────────────────────────────────────────────────

    def play_theme(self) -> None:
        self._play_music_stream(_THEME_FILE)

    def play_boss_music(self) -> None:
        self._play_music_stream(_BOSS_FILE)

    def _play_music_stream(self, key: str) -> None:
        if not self._enabled or key not in self._music_files:
            return
        try:
            pygame.mixer.music.fadeout(500) # Smooth transition
            pygame.mixer.music.load(self._music_files[key])
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)
        except:
            pass

    def stop_theme(self) -> None:
        """Fixes the AttributeError and clears all buffers."""
        if self._enabled:
            pygame.mixer.music.stop()
            pygame.mixer.stop() # Physically kills all SFX channels