"""
tokens.py — Collectible tokens: Store Credits (bonus) and Level-Up tokens.

Both token types fall under gravity and must be collected by touching them.
BonusToken   → adds +100 score          (cyan glow)
LevelUpToken → triggers tier evolution  (gold glow)

Fixes applied
─────────────
  FIX TOKEN-COLLECT A — Magnet pull
    Once a token lands and is within TOKEN_MAGNET_RADIUS world-pixels of
    Karen, it slides horizontally toward her at TOKEN_MAGNET_SPEED px/frame.
    This ensures tokens dropped from enemies near Karen are auto-collected.

  FIX TOKEN-COLLECT B — Level-up token leftward drift
    While a LevelUpToken is still falling (airborne), it drifts leftward at
    TOKEN_LEVELUP_DRIFT px/frame so it moves toward Karen's starting area
    rather than staying pinned at the kill position.

  FIX TOKEN-COLLECT C — Expanded collection hitbox
    The token's collision rect used for karen detection is inflated by
    TOKEN_COLLECT_PAD pixels so Karen does not need pixel-perfect overlap.
"""

from __future__ import annotations
import math
import pygame
from src.settings import (
    SCREEN_W, SCREEN_H, FLOOR_Y,
    TOKEN_BONUS_SIZE, TOKEN_LEVELUP_SIZE,
    TOKEN_GRAVITY, TERM_VEL,
    TOKEN_MAGNET_RADIUS, TOKEN_MAGNET_SPEED,
    TOKEN_LEVELUP_DRIFT,
    NEON_CYAN, NEON_YELLOW, NEON_PINK,
)
from src.asset_loader import assets

# Extra padding (px) on each side for collision detection
TOKEN_COLLECT_PAD = 20


# ─────────────────────────────────────────────────────────────────────────────
#  BASE TOKEN
# ─────────────────────────────────────────────────────────────────────────────

class Token(pygame.sprite.Sprite):
    """
    Abstract collectible with gravity physics.

    World-space coordinates are stored in self._x / self._y.
    self.rect is kept in sync for collision detection.

    Karen's world rect is passed into update() so the magnet
    and drift behaviours can react to her position each frame.
    """

    _GLOW_ALPHA  = 60
    _PULSE_SPEED = 0.08
    _FLOAT_AMP   = 3         # px of hover oscillation

    def __init__(self, x: int, y: int, token_type: str) -> None:
        super().__init__()
        self.token_type = token_type   # "bonus" | "level_up"
        self._x         = float(x)
        self._y         = float(y)
        self._vx        : float = 0.0   # ← horizontal velocity (for drift/magnet)
        self._vy        : float = 0.0
        self._on_ground : bool  = False
        self._pulse_t   : float = 0.0

        self.image = assets[f"token_{token_type}"]
        # Use an inflated rect for easier collision detection
        base = self.image.get_rect(center=(x, y))
        self.rect = base.inflate(TOKEN_COLLECT_PAD * 2, TOKEN_COLLECT_PAD * 2)

    # ── update ────────────────────────────────────────────────────────────

    def update(self, karen_rect: pygame.Rect | None = None) -> None:
        """
        Parameters
        ----------
        karen_rect : Karen's current world-space rect, used for magnet logic.
                     May be None when called without Karen context (tests).
        """
        if not self._on_ground:
            # Apply gravity (and any initial drift)
            self._vy  = min(self._vy + TOKEN_GRAVITY, TERM_VEL)
            self._x  += self._vx
            self._y  += self._vy
            # Land on floor
            if self._y + self.image.get_height() >= FLOOR_Y:
                self._y        = FLOOR_Y - self.image.get_height()
                self._vy       = 0.0
                self._vx       = 0.0   # stop drift once grounded
                self._on_ground = True
        else:
            # Gentle hover once landed
            self._pulse_t += self._PULSE_SPEED
            self._y += math.sin(self._pulse_t) * self._FLOAT_AMP * 0.3

            # ── FIX TOKEN-COLLECT A: magnet pull when Karen is close ──────
            if karen_rect is not None:
                dx = karen_rect.centerx - (self._x + self.image.get_width() // 2)
                dist = abs(dx)
                if dist < TOKEN_MAGNET_RADIUS and dist > 2:
                    pull = TOKEN_MAGNET_SPEED * (1.0 - dist / TOKEN_MAGNET_RADIUS)
                    pull = max(pull, 1.0)
                    self._x += pull if dx > 0 else -pull

        # Sync world-space rect
        self.rect.x = int(self._x) - TOKEN_COLLECT_PAD
        self.rect.y = int(self._y) - TOKEN_COLLECT_PAD

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        """Draw token with glow, translated by camera_x."""
        self._pulse_t += self._PULSE_SPEED
        pulse = 0.7 + 0.3 * math.sin(self._pulse_t)
        r     = int(self.image.get_width() * pulse * 0.5)
        # Convert world-space centre to screen-space
        cx = int(self._x + self.image.get_width()  // 2) - camera_x
        cy = int(self._y + self.image.get_height() // 2)
        # Skip if off screen
        if cx + r < 0 or cx - r > SCREEN_W:
            return
        if r > 0:
            glow  = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*self._glow_colour, self._GLOW_ALPHA),
                               (r, r), r)
            surface.blit(glow, (cx - r, cy - r))
        surface.blit(self.image, (cx - self.image.get_width()  // 2,
                                  cy - self.image.get_height() // 2))

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
    """
    Tier-evolution collectible — gold/pink glow.

    FIX TOKEN-COLLECT B: drifts leftward while airborne so it moves toward
    Karen's area instead of staying pinned at the kill location.
    """

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, "level_up")
        # ── FIX TOKEN-COLLECT B: initial leftward drift ──────────────────
        self._vx = TOKEN_LEVELUP_DRIFT   # negative = move left

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
