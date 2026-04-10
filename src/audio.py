import os
import pygame

_AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "..", "audio")
_THEME_FILE = "theme_music_genspark"
_BOSS_FILE  = "boss_arrives"

class SoundManager:
    def __init__(self) -> None:
        self._enabled = pygame.mixer.get_init() is not None
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_files: dict[str, str] = {}

        if not self._enabled: return

        audio_dir = os.path.abspath(_AUDIO_DIR)
        for fname in os.listdir(audio_dir):
            if not fname.lower().endswith(".mp3"): continue
            key = os.path.splitext(fname)[0]
            path = os.path.join(audio_dir, fname)
            
            if key in [_THEME_FILE, _BOSS_FILE]:
                self._music_files[key] = path
            else:
                try:
                    # Load into memory once - no channel management needed
                    self._sfx[key] = pygame.mixer.Sound(path)
                except: pass

    def play_sfx(self, key: str) -> None:
        """Plays instantly. Pygame handles the parallel channels automatically."""
        if not self._enabled: return
        sound = self._sfx.get(key)
        if sound:
            sound.play()

    def play_theme(self) -> None: self._play_music_stream(_THEME_FILE)
    def play_boss_music(self) -> None: self._play_music_stream(_BOSS_FILE)

    def _play_music_stream(self, key: str) -> None:
        if not self._enabled or key not in self._music_files: return
        try:
            pygame.mixer.music.load(self._music_files[key])
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)
        except: pass

    def stop_theme(self) -> None:
        if self._enabled:
            pygame.mixer.music.stop()