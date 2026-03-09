"""
platform.py — Rect-based platform surfaces.

Platforms serve as landing surfaces for the player and as spawn
points for SlackerEnemy instances.

FIX 3 — PROCEDURAL WORLD-WIDE PLATFORMS:
  Platforms are now generated procedurally across the full WORLD_W
  (6 × SCREEN_W), rather than being limited to the initial 1376-px
  window.  The generator places platforms with randomised x-gaps,
  y-heights, and widths.  The boss arena (last SCREEN_W) is kept
  clear of platforms so the fight area stays open.

  create_platforms() → list[Platform]
    Returns all platforms for the current run.  Call once at startup
    (or on restart) and store the result.
"""

import random
import pygame
from src.settings import (
    NEON_CYAN, NEON_PINK,
    PLATFORM_DEFS,
    WORLD_W, BOSS_TRIGGER_X,
    PLAT_SPACING_MIN, PLAT_SPACING_MAX,
    PLAT_Y_MIN, PLAT_Y_MAX,
    PLAT_W_MIN, PLAT_W_MAX, PLAT_H,
)


class Platform(pygame.sprite.Sprite):
    """
    A horizontal surface the player (and Slackers) can stand on.

    Attributes
    ----------
    rect           : pygame.Rect  — world-space collision rectangle
    slacker_spawned: bool — True once a Slacker has been placed here
    """

    # Visual style constants
    _SURFACE_COLOR  = (30,  30,  60 )
    _EDGE_COLOR     = NEON_CYAN
    _GLOW_COLOR     = (0, 180, 220, 80)
    _EDGE_THICKNESS = 3
    _GLOW_EXPAND    = 6

    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        super().__init__()

        # ── VISUAL SETUP ──────────────────────────────────────────────
        self.visual_w = w  # Save the FULL width for drawing
        self.visual_h = h
        
        # ── PHYSICS SETUP (The "Trim") ────────────────────────────────
        trim = 25 
        # The rect is now smaller than the visual width
        self.rect = pygame.Rect(x + trim, y, w - (trim * 2), h)
        
        self.slacker_spawned = False
        self.image = pygame.Surface((self.visual_w, self.visual_h), pygame.SRCALPHA)
        self._draw_surface() # Pass the full width to the draw helper

    def _draw_surface(self) -> None:
        # Use the visual variables, NOT the physics rect
        w, h = self.visual_w, self.visual_h
        
        self.image.fill(self._SURFACE_COLOR)
        
        # Draw the top edge
        pygame.draw.line(
            self.image, self._EDGE_COLOR,
            (0, 0), (w, 0), self._EDGE_THICKNESS,
        )
        
        # Draw the side neon pink accents
        pygame.draw.line(self.image, NEON_PINK, (0, 0),   (0, h),   1)
        pygame.draw.line(self.image, NEON_PINK, (w-1, 0), (w-1, h), 1) 


    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        """Draw platform with soft glow, translated by camera_x."""
        sx = self.rect.x - camera_x
        sy = self.rect.y

        # Cull if off screen
        if sx + self.rect.w < 0 or sx > surface.get_width():
            return

        gx = sx - self._GLOW_EXPAND
        gy = sy - 2
        gw = self.rect.w + self._GLOW_EXPAND * 2
        gh = self.rect.h + self._GLOW_EXPAND
        glow = pygame.Surface((gw, gh), pygame.SRCALPHA)
        glow.fill(self._GLOW_COLOR)
        surface.blit(glow, (gx, gy))
        surface.blit(self.image, (sx, sy))

    @property
    def top_y(self) -> int:
        return self.rect.top

    @property
    def spawn_x(self) -> int:
        return self.rect.centerx


# ─────────────────────────────────────────────────────────────────────────────
#  FACTORY  (procedural world-wide generation)
# ─────────────────────────────────────────────────────────────────────────────

def create_platforms(seed: int | None = None) -> list[Platform]:
    """
    Procedurally generate platforms spanning the full game world.

    Strategy
    ────────
    • Start with the 5 fixed "tutorial" platforms (first SCREEN_W).
    • Then walk rightward in random x-intervals, placing platforms
      at randomised heights and widths, until we approach BOSS_TRIGGER_X.
    • The boss arena (last SCREEN_W) is kept free of platforms.
    • Each platform is guaranteed to have a non-zero gap from the floor
      (PLAT_Y_MAX) and from the ceiling (PLAT_Y_MIN).

    Returns a list of Platform objects in left-to-right order.
    """
    rng = random.Random(seed)   # seeded for reproducibility if needed

    platforms: list[Platform] = []

    # ── 1. Fixed tutorial section (first screen) ─────────────────────────
    for x, y, w, h in PLATFORM_DEFS:
        platforms.append(Platform(x, y, w, h))

    # ── 2. Procedural section ─────────────────────────────────────────────
    # Cursor starts just past the last tutorial platform
    cursor_x = PLATFORM_DEFS[-1][0] + PLATFORM_DEFS[-1][2] + rng.randint(
        PLAT_SPACING_MIN, PLAT_SPACING_MAX
    )

    # Leave BOSS_ARENA clearance (last SCREEN_W is the boss arena)
    # Only leave a 100-px pre-boss buffer so the level feels complete until the end
    stop_x = BOSS_TRIGGER_X

    while cursor_x < stop_x:
        w = rng.randint(PLAT_W_MIN, PLAT_W_MAX)
        y = rng.randint(PLAT_Y_MIN, PLAT_Y_MAX)
        platforms.append(Platform(cursor_x, y, w, PLAT_H))
        gap = rng.randint(PLAT_SPACING_MIN, PLAT_SPACING_MAX)
        cursor_x += w + gap

    return platforms
