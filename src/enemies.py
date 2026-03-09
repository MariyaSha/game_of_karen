"""
enemies.py — Enemy hierarchy for Game of Karen.

Base class
──────────
  Enemy  →  common physics, draw, hit detection, health

Subclasses
──────────
  FlyerEnemy   — jetpack enemy, moves left with sine-wave vertical oscillation
  SkaterEnemy  — fast ground patrol, bounces off screen edges
  SlackerEnemy — static tank on platforms; takes multiple hits to kill
"""

from __future__ import annotations
import math
import random
import pygame
from src.settings import (
    SCREEN_W, SCREEN_H, FLOOR_Y, GRAVITY, TERM_VEL,
    FLYER_SPEED, FLYER_AMP, FLYER_FREQ, FLYER_HEIGHT, FLYER_Y_RANGE,
    SKATER_SPEED, SKATER_HEIGHT, SKATER_Y,
    SLACKER_HEIGHT, SLACKER_HEALTH,
    NEON_CYAN, NEON_PINK, NEON_YELLOW, WHITE,
)
from src.asset_loader import assets


# ─────────────────────────────────────────────────────────────────────────────
#  BASE ENEMY
# ─────────────────────────────────────────────────────────────────────────────

class Enemy(pygame.sprite.Sprite):
    """
    Abstract base for all enemies.

    Subclasses must set:
        self.image   – current pygame.Surface
        self.rect    – pygame.Rect
    and implement `update()`.
    """

    def __init__(self, health: int = 1) -> None:
        super().__init__()
        self.health      : int  = health
        self.alive       : bool = True
        self.hit_flash   : int  = 0    # frames of white-flash after hit
        self._drop_token : str  = ""   # "bonus" | "level_up" | ""

    # ── combat ────────────────────────────────────────────────────────────

    def take_hit(self, damage: int = 1) -> None:
        self.health   -= damage
        self.hit_flash = 10
        if self.health <= 0:
            self.alive = False
            self.kill()

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        img = self.image
        if self.hit_flash > 0:
            img = img.copy()
            img.fill((255, 255, 255, 160), special_flags=pygame.BLEND_RGBA_ADD)
            self.hit_flash -= 1
        surface.blit(img, self.rect.topleft)

    # ── token drop ────────────────────────────────────────────────────────

    def get_drop(self) -> str:
        """Return the token type this enemy drops on death."""
        return self._drop_token


# ─────────────────────────────────────────────────────────────────────────────
#  FLYER ENEMY
# ─────────────────────────────────────────────────────────────────────────────

class FlyerEnemy(Enemy):
    """
    Jetpack enemy that flies across the screen.
    - Moves left at constant horizontal speed.
    - Oscillates vertically via a sine function.
    - Spawns at a random y-height within FLYER_Y_RANGE.
    - Drops a bonus token on death.
    """

    def __init__(self, spawn_x: int, spawn_y: int) -> None:
        super().__init__(health=1)
        self._drop_token = "bonus"

        self._x       = float(spawn_x)
        self._y       = float(spawn_y)
        self._base_y  = float(spawn_y)
        self._t       = random.uniform(0, math.tau)   # phase offset

        # Randomly face the direction of movement (left)
        self.image = assets["flyer_left"]
        self.rect  = self.image.get_rect(
            topleft=(int(self._x), int(self._y))
        )

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        self._t  += FLYER_FREQ
        self._x  -= FLYER_SPEED
        self._y   = self._base_y + math.sin(self._t) * FLYER_AMP

        self.rect.x = int(self._x)
        self.rect.y = int(self._y)

        # De-spawn when fully off left edge
        if self._x + self.rect.width < 0:
            self.alive = False
            self.kill()


# ─────────────────────────────────────────────────────────────────────────────
#  SKATER ENEMY
# ─────────────────────────────────────────────────────────────────────────────

class SkaterEnemy(Enemy):
    """
    Fast ground patroller.
    - Spawns on the floor, moving left.
    - Bounces off both screen edges.
    - Drops a level-up token on death.
    """

    def __init__(self, spawn_x: int) -> None:
        super().__init__(health=1)
        self._drop_token = "level_up"

        self._x     = float(spawn_x)
        self._speed = -SKATER_SPEED    # start moving left

        self._update_image()
        floor_y = SKATER_Y - self.rect.height
        self._y  = float(floor_y)
        self.rect.topleft = (int(self._x), int(self._y))

    # ── helpers ───────────────────────────────────────────────────────────

    def _update_image(self) -> None:
        side = "right" if self._speed > 0 else "left"
        self.image = assets[f"skater_{side}"]
        w, h = self.image.get_size()
        self.rect  = pygame.Rect(int(self._x), 0, w, h)

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        self._x += self._speed

        # Bounce off edges
        if self._x <= 0:
            self._x     = 0
            self._speed = abs(self._speed)
            self._update_image()
        elif self._x + self.rect.width >= SCREEN_W:
            self._x     = SCREEN_W - self.rect.width
            self._speed = -abs(self._speed)
            self._update_image()

        self.rect.x = int(self._x)
        self.rect.y = int(SKATER_Y - self.rect.height)


# ─────────────────────────────────────────────────────────────────────────────
#  SLACKER ENEMY
# ─────────────────────────────────────────────────────────────────────────────

class SlackerEnemy(Enemy):
    """
    Static tank enemy that spawns exclusively on platforms.
    - Never moves horizontally.
    - Takes SLACKER_HEALTH hits to kill.
    - Drops a bonus token on death.
    - Health bar drawn above the sprite.
    """

    _BAR_W  = 40
    _BAR_H  = 6
    _BAR_DY = 8    # pixels above sprite top

    def __init__(self, platform_x: int, platform_y: int) -> None:
        super().__init__(health=SLACKER_HEALTH)
        self._drop_token = "bonus"

        self.image = assets["slacker_right"]
        w, h       = self.image.get_size()
        # Centre horizontally on the platform, sit on top
        self._x    = float(platform_x - w // 2)
        self._y    = float(platform_y - h)
        self.rect  = pygame.Rect(int(self._x), int(self._y), w, h)

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        # Static — no movement needed
        pass

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        if not self.alive:
            return
        self._draw_health_bar(surface)

    def _draw_health_bar(self, surface: pygame.Surface) -> None:
        bx = self.rect.centerx - self._BAR_W // 2
        by = self.rect.top - self._BAR_DY - self._BAR_H
        # Background
        pygame.draw.rect(surface, (40, 10, 10),
                         (bx, by, self._BAR_W, self._BAR_H))
        # Fill
        fill_w = int(self._BAR_W * (self.health / SLACKER_HEALTH))
        pygame.draw.rect(surface, (200, 40, 20),
                         (bx, by, fill_w, self._BAR_H))
        # Border
        pygame.draw.rect(surface, NEON_PINK,
                         (bx, by, self._BAR_W, self._BAR_H), 1)


# ─────────────────────────────────────────────────────────────────────────────
#  SPAWN HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def spawn_flyer() -> FlyerEnemy:
    """Create a FlyerEnemy at a random right-side x, random y in band."""
    sx = random.randint(SCREEN_W, SCREEN_W + 200)
    sy = random.randint(*FLYER_Y_RANGE)
    return FlyerEnemy(sx, sy)


def spawn_skater() -> SkaterEnemy:
    """Create a SkaterEnemy at a random right-side x, on the floor."""
    sx = random.randint(SCREEN_W, SCREEN_W + 300)
    return SkaterEnemy(sx)


def spawn_slacker(platform) -> SlackerEnemy:
    """Create a SlackerEnemy on the given Platform."""
    return SlackerEnemy(platform.spawn_x, platform.top_y)
