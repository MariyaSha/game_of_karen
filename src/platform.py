"""
platform.py — Rect-based platform surfaces.
Platforms serve as landing surfaces for the player and as exclusive spawn
points for SlackerEnemy instances.
"""

import pygame
from src.settings import NEON_CYAN, NEON_PINK, PLATFORM_DEFS


class Platform(pygame.sprite.Sprite):
    """
    A horizontal surface the player (and Slackers) can stand on.

    Attributes
    ----------
    rect : pygame.Rect  — collision rectangle
    slacker_spawned : bool — True once a Slacker has been placed here
    """

    # Visual style constants
    _SURFACE_COLOR  = (30,  30,  60 )   # dark-indigo fill
    _EDGE_COLOR     = NEON_CYAN
    _GLOW_COLOR     = (0, 180, 220, 80) # semi-transparent glow layer
    _EDGE_THICKNESS = 3
    _GLOW_EXPAND    = 6                 # px expanded for the glow rect

    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        super().__init__()

        self.rect            = pygame.Rect(x, y, w, h)
        self.slacker_spawned = False

        # Pre-render the platform surface (done once for performance)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self._draw_surface()

    # ── private ──────────────────────────────────────────────────────────

    def _draw_surface(self) -> None:
        w, h = self.rect.w, self.rect.h

        # Solid fill
        self.image.fill(self._SURFACE_COLOR)

        # Top-edge neon line
        pygame.draw.line(
            self.image, self._EDGE_COLOR,
            (0, 0), (w, 0),
            self._EDGE_THICKNESS,
        )
        # Side accent lines
        pygame.draw.line(
            self.image, NEON_PINK,
            (0, 0), (0, h), 1,
        )
        pygame.draw.line(
            self.image, NEON_PINK,
            (w - 1, 0), (w - 1, h), 1,
        )

    # ── public ───────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        """Draw platform with a soft glow halo beneath it."""
        gx = self.rect.x - self._GLOW_EXPAND
        gy = self.rect.y - 2
        gw = self.rect.w + self._GLOW_EXPAND * 2
        gh = self.rect.h + self._GLOW_EXPAND

        glow = pygame.Surface((gw, gh), pygame.SRCALPHA)
        glow.fill(self._GLOW_COLOR)
        surface.blit(glow, (gx, gy))
        surface.blit(self.image, self.rect.topleft)

    @property
    def top_y(self) -> int:
        """Convenience: y-coordinate of the platform surface."""
        return self.rect.top

    @property
    def spawn_x(self) -> int:
        """Centre x for spawning a Slacker on this platform."""
        return self.rect.centerx


# ── factory ──────────────────────────────────────────────────────────────────

def create_platforms() -> list[Platform]:
    """Instantiate all platforms from PLATFORM_DEFS in settings."""
    return [Platform(*d) for d in PLATFORM_DEFS]
