"""
tokens.py — Collectible tokens: Store Credits (bonus) and Level-Up tokens.

Both token types fall under gravity and must be collected by touching them.
BonusToken  → adds +100 score
LevelUpToken → triggers Karen's tier evolution
"""

from __future__ import annotations
import pygame
from src.settings import (
    SCREEN_W, SCREEN_H, FLOOR_Y,
    TOKEN_BONUS_SIZE, TOKEN_LEVELUP_SIZE,
    TOKEN_GRAVITY, TERM_VEL,
    NEON_CYAN, NEON_YELLOW, NEON_PINK,
)
from src.asset_loader import assets


# ─────────────────────────────────────────────────────────────────────────────
#  BASE TOKEN
# ─────────────────────────────────────────────────────────────────────────────

class Token(pygame.sprite.Sprite):
    """Abstract collectible with gravity physics."""

    _GLOW_ALPHA  = 60
    _PULSE_SPEED = 0.08
    _FLOAT_AMP   = 3         # px of hover oscillation

    def __init__(self, x: int, y: int, token_type: str) -> None:
        super().__init__()
        self.token_type = token_type   # "bonus" | "level_up"
        self._x         = float(x)
        self._y         = float(y)
        self._vy        : float = 0.0
        self._on_ground : bool  = False
        self._pulse_t   : float = 0.0

        self.image = assets[f"token_{token_type}"]
        self.rect  = self.image.get_rect(center=(x, y))

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        if not self._on_ground:
            # Fall
            self._vy  = min(self._vy + TOKEN_GRAVITY, TERM_VEL)
            self._y  += self._vy
            # Land on floor
            if self._y + self.rect.height >= FLOOR_Y:
                self._y        = FLOOR_Y - self.rect.height
                self._vy       = 0.0
                self._on_ground = True
        else:
            # Gentle hover once landed
            import math
            self._pulse_t += self._PULSE_SPEED
            self._y += math.sin(self._pulse_t) * self._FLOAT_AMP * 0.3

        self.rect.x = int(self._x)
        self.rect.y = int(self._y)

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        # Glow circle behind the token
        import math
        self._pulse_t += self._PULSE_SPEED
        pulse = 0.7 + 0.3 * math.sin(self._pulse_t)
        r     = int(self.rect.width * pulse)
        glow  = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self._glow_colour, self._GLOW_ALPHA),
                           (r, r), r)
        cx = self.rect.centerx
        cy = self.rect.centery
        surface.blit(glow, (cx - r, cy - r))
        surface.blit(self.image, self.rect.topleft)

    @property
    def _glow_colour(self) -> tuple[int, int, int]:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
#  BONUS TOKEN  (store credits +100)
# ─────────────────────────────────────────────────────────────────────────────

class BonusToken(Token):
    """Score-only collectible — cyan glow."""

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, "bonus")

    @property
    def _glow_colour(self) -> tuple[int, int, int]:
        return NEON_CYAN


# ─────────────────────────────────────────────────────────────────────────────
#  LEVEL-UP TOKEN  (triggers tier evolution)
# ─────────────────────────────────────────────────────────────────────────────

class LevelUpToken(Token):
    """Tier-evolution collectible — gold/pink glow."""

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, "level_up")

    @property
    def _glow_colour(self) -> tuple[int, int, int]:
        return NEON_YELLOW


# ─────────────────────────────────────────────────────────────────────────────
#  FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def make_token(token_type: str, x: int, y: int) -> Token:
    """Create the appropriate token at the given position."""
    if token_type == "bonus":
        return BonusToken(x, y)
    elif token_type == "level_up":
        return LevelUpToken(x, y)
    else:
        raise ValueError(f"Unknown token type: {token_type!r}")
