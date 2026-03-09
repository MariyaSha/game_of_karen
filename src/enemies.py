"""
enemies.py — Enemy hierarchy for Game of Karen.

Base class
──────────
  Enemy  →  common physics, draw, hit detection, health

  FIX 6 — UNIVERSAL HEALTH BARS:
    The health-bar drawing logic has been moved from SlackerEnemy into the
    base Enemy class.  Every enemy now shows a small HP bar above their
    sprite as soon as they have taken at least one hit (health < max_health).
    The bar is hidden at full health to avoid clutter.

Subclasses
──────────
  FlyerEnemy   — jetpack enemy, moves left with sine-wave vertical oscillation
  SkaterEnemy  — fast ground patrol, bounces off screen edges
  SlackerEnemy — static tank on platforms; takes multiple hits to kill

Camera
──────
  All draw() methods accept an optional camera_x parameter so they can
  translate from world-space to screen-space correctly.
"""

from __future__ import annotations
import math
import random
import pygame
from src.settings import (
    SCREEN_W, SCREEN_H, FLOOR_Y, GRAVITY, TERM_VEL,
    WORLD_W, BOSS_TRIGGER_X,
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
        self.image        – current pygame.Surface
        self.rect         – pygame.Rect  (world-space)
        self._max_health  – the enemy's starting HP (set in __init__)
    and implement update().
    """

    # ── FIX 6: health-bar visual constants (shared) ───────────────────────
    _BAR_W   = 40
    _BAR_H   = 5
    _BAR_DY  = 6   # pixels above sprite top
    _BAR_FILL_COL  = (200, 40,  20)
    _BAR_EMPTY_COL = (40,  10,  10)
    _BAR_BORDER_COL = NEON_PINK

    def __init__(self, health: int = 1) -> None:
        super().__init__()
        self.health      : int  = health
        self._max_health : int  = health   # remember the original max for bar ratio
        self.alive       : bool = True
        self.hit_flash   : int  = 0
        self._drop_token : str  = ""

    # ── combat ────────────────────────────────────────────────────────────

    def take_hit(self, damage: int = 1) -> None:
        self.health   -= damage
        self.hit_flash = 10
        if self.health <= 0:
            self.alive = False
            self.kill()

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        """
        Draw the enemy sprite translated by camera_x.
        After the sprite, draw the universal health bar (FIX 6).
        """
        if not self.alive:
            return

        # Translate world rect to screen position
        screen_x = self.rect.x - camera_x
        screen_y = self.rect.y

        # Skip rendering if fully off screen
        if screen_x + self.rect.width < 0 or screen_x > SCREEN_W:
            return

        # Build the screen-space draw rect
        draw_rect = pygame.Rect(screen_x, screen_y,
                                self.rect.width, self.rect.height)

        img = self.image
        if self.hit_flash > 0:
            img = img.copy()
            img.fill((255, 255, 255, 160), special_flags=pygame.BLEND_RGBA_ADD)
            self.hit_flash -= 1
        surface.blit(img, draw_rect.topleft)

        # ── FIX 6: draw health bar for every enemy once they've been hit ──
        self._draw_health_bar(surface, draw_rect)

    # ── FIX 6: universal health bar ───────────────────────────────────────

    def _draw_health_bar(self, surface: pygame.Surface,
                         draw_rect: pygame.Rect) -> None:
        """
        Show a small health bar above the sprite only after the first hit
        (i.e. when health < _max_health).  Full-health enemies are clean.
        """
        if self.health >= self._max_health:
            return   # pristine — no bar needed

        bx = draw_rect.centerx - self._BAR_W // 2
        by = draw_rect.top - self._BAR_DY - self._BAR_H

        # Background (empty portion)
        pygame.draw.rect(surface, self._BAR_EMPTY_COL,
                         (bx, by, self._BAR_W, self._BAR_H))
        # Filled portion
        fill_w = max(0, int(self._BAR_W * (self.health / self._max_health)))
        pygame.draw.rect(surface, self._BAR_FILL_COL,
                         (bx, by, fill_w, self._BAR_H))
        # Border
        pygame.draw.rect(surface, self._BAR_BORDER_COL,
                         (bx, by, self._BAR_W, self._BAR_H), 1)

    # ── token drop ────────────────────────────────────────────────────────

    def get_drop(self) -> str:
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

        self._x      = float(spawn_x)
        self._y      = float(spawn_y)
        self._base_y = float(spawn_y)
        self._t      = random.uniform(0, math.tau)

        self.image = assets["flyer_left"]
        self.rect  = self.image.get_rect(
            topleft=(int(self._x), int(self._y))
        )

    def update(self) -> None:
        self._t  += FLYER_FREQ
        self._x  -= FLYER_SPEED
        self._y   = self._base_y + math.sin(self._t) * FLYER_AMP

        self.rect.x = int(self._x)
        self.rect.y = int(self._y)

        # De-spawn when fully off left edge (world-space)
        if self._x + self.rect.width < -200:
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
        self._speed = -SKATER_SPEED

        self._update_image()
        self._y = float(SKATER_Y - self.rect.height)
        self.rect.topleft = (int(self._x), int(self._y))

    def _update_image(self) -> None:
        side = "right" if self._speed > 0 else "left"
        self.image = assets[f"skater_{side}"]
        w, h       = self.image.get_size()
        self.rect  = pygame.Rect(int(self._x), 0, w, h)

    def update(self) -> None:
        self._x += self._speed

        # Bounce off world edges (not just SCREEN_W)
        if self._x <= 0:
            self._x     = 0
            self._speed = abs(self._speed)
            self._update_image()
        elif self._x + self.rect.width >= BOSS_TRIGGER_X:
            # Don't let skaters enter the boss arena
            self._x     = float(BOSS_TRIGGER_X - self.rect.width)
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
    - Health bar is handled by the base Enemy class (FIX 6).
    """

    def __init__(self, platform_x: int, platform_y: int) -> None:
        super().__init__(health=SLACKER_HEALTH)
        self._drop_token = "level_up"   # Slackers also grant tier-up tokens

        self.image = assets["slacker_right"]
        w, h       = self.image.get_size()
        self._x    = float(platform_x - w // 2)
        self._y    = float(platform_y - h)
        self.rect  = pygame.Rect(int(self._x), int(self._y), w, h)

    def update(self) -> None:
        pass   # static — no movement


# ─────────────────────────────────────────────────────────────────────────────
#  SPAWN HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def spawn_flyer() -> FlyerEnemy:
    # Spawn just off-screen to the right of Karen's current viewport
    # (camera scroll means SCREEN_W is correct as the spawn-ahead margin)
    sx = random.randint(SCREEN_W, SCREEN_W + 300)
    sy = random.randint(*FLYER_Y_RANGE)
    return FlyerEnemy(sx, sy)


def spawn_skater() -> SkaterEnemy:
    sx = random.randint(SCREEN_W, SCREEN_W + 400)
    return SkaterEnemy(sx)


def spawn_slacker(platform) -> SlackerEnemy:
    return SlackerEnemy(platform.spawn_x, platform.top_y)
