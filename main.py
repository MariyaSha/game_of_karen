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
os.environ['SDL_AUDIODRIVER'] = 'pulseaudio' 
# Force PulseAudio to stop being 'helpful' with buffering
os.environ['PULSE_LATENCY_MSEC'] = "30" 

import sys
import pygame
# ... rest of your code

# Allow running from any directory by ensuring the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from src.settings     import SCREEN_W, SCREEN_H, FPS, TITLE
from src.asset_loader import load_all
from src.game_manager import GameManager

def main() -> None:
    # 1. Strict WSL-friendly pre_init (44.1kHz and small 512 buffer)
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    
    # 2. Increase channels so parallel sounds never "crash" or cut off
    pygame.mixer.set_num_channels(64) 

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)

    load_all()

    gm = GameManager(screen)
    gm.run()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
