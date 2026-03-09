"""
asset_loader.py — Centralised asset cache.
All images are loaded once and stored in a dict.
Call load_all(screen) before the game loop starts.
"""

import os
import pygame
from src.settings import (
    SCREEN_H, KAREN_HEIGHT, FLYER_HEIGHT, SKATER_HEIGHT,
    SLACKER_HEIGHT, BOSS_HEIGHT, TOKEN_BONUS_SIZE, TOKEN_LEVELUP_SIZE,
)

# Public dict: assets["key"] → pygame.Surface
assets: dict = {}

# ── helpers ──────────────────────────────────────────────────────────────────

def _load(path: str, alpha: bool = True) -> pygame.Surface:
    full = os.path.join("assets", path)
    img = pygame.image.load(full)
    return img.convert_alpha() if alpha else img.convert()


def _scale(surf: pygame.Surface, w: int, h: int) -> pygame.Surface:
    return pygame.transform.smoothscale(surf, (w, h))


def _sprite_hw(height: int, surf: pygame.Surface) -> tuple[int, int]:
    """Return (w, h) keeping aspect ratio given target height."""
    ow, oh = surf.get_size()
    ratio  = ow / oh
    return int(height * ratio), height


# ── main loader ──────────────────────────────────────────────────────────────

def load_all() -> None:
    """Load and scale every game asset into the global `assets` dict."""

    # Background
    bg_raw = _load("background.png", alpha=False)
    from src.settings import SCREEN_W, SCREEN_H
    assets["background"] = _scale(bg_raw, SCREEN_W, SCREEN_H)

    # ── Karen (3 tiers × 4 states × 2 directions) ─────────────────────────
    kh = KAREN_HEIGHT
    for tier in (1, 2, 3):
        for state in ("walk", "jump", "fall", "attack"):
            for direction in ("left", "right"):
                key  = f"karen{tier}_{state}_{direction}"
                raw  = _load(f"{key}.png")
                w, h = _sprite_hw(kh, raw)
                assets[key] = _scale(raw, w, h)

    # ── Enemies ───────────────────────────────────────────────────────────
    for side in ("left", "right"):
        # Flyer
        raw = _load(f"flyer_{side}.png")
        w, h = _sprite_hw(FLYER_HEIGHT, raw)
        assets[f"flyer_{side}"] = _scale(raw, w, h)

        # Skater
        raw = _load(f"skater_{side}.png")
        w, h = _sprite_hw(SKATER_HEIGHT, raw)
        assets[f"skater_{side}"] = _scale(raw, w, h)

        # Slacker
        raw = _load(f"slacker_{side}.png")
        w, h = _sprite_hw(SLACKER_HEIGHT, raw)
        assets[f"slacker_{side}"] = _scale(raw, w, h)

    # ── Boss ──────────────────────────────────────────────────────────────
    for state in ("idle", "attack"):
        raw = _load(f"boss_{state}.png")
        w, h = _sprite_hw(BOSS_HEIGHT, raw)
        assets[f"boss_{state}"] = _scale(raw, w, h)

    # ── Tokens ────────────────────────────────────────────────────────────
    raw = _load("token_bonus.png")
    assets["token_bonus"] = _scale(raw, TOKEN_BONUS_SIZE, TOKEN_BONUS_SIZE)

    raw = _load("token_level_up.png")
    assets["token_level_up"] = _scale(raw, TOKEN_LEVELUP_SIZE, TOKEN_LEVELUP_SIZE)
