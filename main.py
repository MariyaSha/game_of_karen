"""
main.py — Entry point for Game of Karen.

Run from the project root:
    python main.py

Controls
────────
    A / ← : Move left
    D / → : Move right
    SPACE : Jump
    F     : Fire Sound Wave
    R     : Restart (Game Over / Victory screen)
    Q     : Quit
"""

import os
import sys

# ── AUDIO ENVIRONMENT SETUP ───────────────────────────────────────────────────
# These MUST be set before pygame (and therefore SDL) is imported.
# SDL reads these env vars when the audio subsystem initialises; setting them
# any later has no effect.
#
# PULSE_LATENCY_MSEC: tells PulseAudio to use a 5 ms hardware buffer instead
#   of its default (~100 ms). This is the single biggest source of perceived
#   audio lag on Linux desktop systems.
#
# SDL_AUDIODRIVER: prefer 'pulseaudio' so SDL doesn't fall back to a
#   higher-latency driver on machines that have both available.
#   setdefault is used so the caller can still override from the shell.
os.environ.setdefault('SDL_AUDIODRIVER', 'pulseaudio')
os.environ['PULSE_LATENCY_MSEC'] = '5'

# Allow running from any directory by ensuring the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from src.settings     import SCREEN_W, SCREEN_H, FPS, TITLE
from src.asset_loader import load_all
from src.game_manager import GameManager


def main() -> None:
    # pre_init must be called before pygame.init().
    # buffer=512 at 44100 Hz → ~11.6 ms of mixer latency.
    # This is the smallest power-of-two that stays stable on PulseAudio;
    # going lower risks buffer underruns and audio dropouts.
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.font.init()
    pygame.mixer.set_num_channels(16)   # 16 simultaneous SFX channels

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)

    load_all()

    gm = GameManager(screen)
    gm.run()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
