"""
audio.py — SoundManager for Game of Karen.

Dynamically loads every .mp3 from the audio/ directory.
- theme_music_infected_vibes.mp3  → streamed via pygame.mixer.music (looped).
- boss_arrives.mp3                → streamed via pygame.mixer.music (one-shot).
- All other .mp3 files            → loaded as pygame.mixer.Sound objects.

Latency design
──────────────
The two biggest sources of perceived audio lag in Pygame are:

  1. fade_ms > 0 on Sound.play()
       A fade_ms=50 ramp makes the first ~25 ms nearly silent, which the
       brain registers as a ~50 ms delay.  All SFX use fade_ms=0 (default).

  2. Dedicated channels for player-action SFX
       Jump and attack sounds are directly triggered by the player; they
       must never be stolen by ambient hit/token sounds.  Channels 0 and 1
       are reserved exclusively for these two sounds via set_reserved(2).
       All other SFX use Sound.play() which lets SDL pick the best free
       channel from the general pool (channels 2-15) non-destructively.

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
_THEME_FILE = "theme_music_infected_vibes"
_BOSS_FILE  = "boss_arrives"

# Channels permanently reserved for time-critical player-action sounds.
# pygame.mixer.set_reserved(2) prevents SDL from auto-assigning channels
# 0 and 1 to random sounds.
_CH_JUMP   = 0   # reserved for karen_jump
_CH_ATTACK = 1   # reserved for karen_attack_soundwave


class SoundManager:
    """Loads and plays all game audio with minimal latency."""

    def __init__(self) -> None:
        # Ensure the mixer is initialised (safe to call multiple times).
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_files: dict[str, str] = {}
        self._enabled: bool = True

        audio_dir = os.path.abspath(_AUDIO_DIR)
        if not os.path.isdir(audio_dir):
            # Audio directory missing — run silently.
            self._enabled = False
            return

        # Reserve channels 0 and 1 so SDL never hands them to random sounds.
        pygame.mixer.set_reserved(2)

        # Pre-bind Channel objects for the two player-action sounds so we
        # never pay the lookup cost inside the hot game loop.
        self._ch_jump   = pygame.mixer.Channel(_CH_JUMP)
        self._ch_attack = pygame.mixer.Channel(_CH_ATTACK)

        for fname in os.listdir(audio_dir):
            if not fname.lower().endswith(".mp3"):
                continue
            key  = os.path.splitext(fname)[0]   # filename without extension
            path = os.path.join(audio_dir, fname)

            if key in (_THEME_FILE, _BOSS_FILE):
                # Music files are streamed, not buffered as Sound objects.
                self._music_files[key] = path
            else:
                try:
                    self._sfx[key] = pygame.mixer.Sound(path)
                except pygame.error:
                    pass   # skip unloadable files silently

    # ── SFX playback ─────────────────────────────────────────────────────────

    def play_sfx(self, key: str) -> None:
        """
        Play a one-shot sound effect with zero fade-in.

        Jump and attack use their dedicated reserved channels so they can
        never be pre-empted by ambient sounds.  All other SFX use
        Sound.play() which lets SDL choose the best available channel from
        the general pool (channels 2-15) without forcibly stopping anything.
        """
        if not self._enabled:
            return
        sound = self._sfx.get(key)
        if sound is None:
            return

        if key == "karen_jump":
            # Stop any previous jump sound before replaying (prevents overlap).
            self._ch_jump.stop()
            self._ch_jump.play(sound)
        elif key == "karen_attack_soundwave":
            self._ch_attack.stop()
            self._ch_attack.play(sound)
        else:
            # Direct play — no fade, no forced channel steal.
            sound.play()

    # ── Music streaming ───────────────────────────────────────────────────────

    def play_theme(self) -> None:
        """Start the background music on an infinite loop."""
        self._play_music_stream(_THEME_FILE, loop=True)

    def play_boss_music(self) -> None:
        """Play the boss arrival sting (one-shot, then silence)."""
        self._play_music_stream(_BOSS_FILE, loop=False)

    def _play_music_stream(self, key: str, loop: bool = True) -> None:
        if not self._enabled or key not in self._music_files:
            return
        try:
            pygame.mixer.music.fadeout(500)
            pygame.mixer.music.load(self._music_files[key])
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1 if loop else 0)
        except pygame.error:
            pass

    def stop_theme(self) -> None:
        """Stop background music and all SFX channels immediately."""
        if not self._enabled:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()   # clears all SFX channel buffers
        except pygame.error:
            pass
