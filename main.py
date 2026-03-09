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

# Allow running from any directory by ensuring the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Use software renderer for headless / server environments
os.environ.setdefault("SDL_VIDEODRIVER", "x11")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("DISPLAY", ":99")

import pygame
from src.settings     import SCREEN_W, SCREEN_H, FPS, TITLE
from src.asset_loader import load_all
from src.game_manager import GameManager


def main() -> None:
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)

    # Load all assets into the global cache
    load_all()

    # Hand control to the game manager
    gm = GameManager(screen)
    gm.run()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
