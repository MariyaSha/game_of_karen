"""
audio.py — SoundManager for Game of Karen.

Dynamically loads every .mp3 from the audio/ directory.
- theme_music_infected_vibes.mp3  → streamed via pygame.mixer.music (looped).
- All other .mp3 files            → loaded as pygame.mixer.Sound objects.

Usage
─────
    from src.audio import SoundManager
    sm = SoundManager()
    sm.play_theme()
    sm.play_sfx("karen_jump")
    sm.play_sfx("token_levelup")
"""

from __future__ import annotations
import os
import pygame


_AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "..", "audio")
_MUSIC_FILE = "theme_music_infected_vibes"


class SoundManager:
    """Loads and plays all game audio."""

    def __init__(self) -> None:
        # Ensure the mixer is initialised (safe to call multiple times).
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_path: str | None = None
        self._enabled: bool = True

        audio_dir = os.path.abspath(_AUDIO_DIR)
        if not os.path.isdir(audio_dir):
            # Audio directory missing — run silently.
            self._enabled = False
            return

        for fname in os.listdir(audio_dir):
            if not fname.lower().endswith(".mp3"):
                continue
            key  = os.path.splitext(fname)[0]          # filename without extension
            path = os.path.join(audio_dir, fname)
            if key == _MUSIC_FILE:
                self._music_path = path
            else:
                try:
                    self._sfx[key] = pygame.mixer.Sound(path)
                except pygame.error:
                    pass  # skip unloadable files silently

    # ── public API ────────────────────────────────────────────────────────

    def play_theme(self) -> None:
        """Start the background music on an infinite loop."""
        if not self._enabled or self._music_path is None:
            return
        try:
            pygame.mixer.music.load(self._music_path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)          # -1 = loop forever
        except pygame.error:
            pass

    def play_sfx(self, key: str) -> None:
        """Play a one-shot sound effect by its filename stem (no extension)."""
        if not self._enabled:
            return
        sound = self._sfx.get(key)
        if sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    def stop_theme(self) -> None:
        """Stop background music (e.g. on game-over / victory)."""
        if not self._enabled:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
