"""
boss.py — BossManager: two-phase state machine for the end-stage boss.

Phase Machine
─────────────
  ATTACK phase  (immune)
    • Launches parabolic fireballs at intervals.
    • Boss sprite: boss_attack.png
    • Duration: BOSS_ATTACK_DURATION frames, then switches to IDLE.

  IDLE phase  (vulnerable)
    • Boss stands still.
    • Boss sprite: boss_idle.png
    • Can be damaged by Karen's Sound Wave.
    • Duration: BOSS_IDLE_DURATION frames, then switches to ATTACK.

Fireballs
─────────
  Spawn at the boss centre and arc toward the player with a horizontal
  velocity + downward gravity (parabolic trajectory).
"""

from __future__ import annotations
import math
import random
import pygame

from src.fonts import get_mono
from src.settings import (
    SCREEN_W, SCREEN_H, FLOOR_Y,
    BOSS_HEIGHT, BOSS_SPAWN_X, BOSS_SPAWN_Y,
    BOSS_HEALTH, BOSS_IDLE_DURATION, BOSS_ATTACK_DURATION,
    BOSS_FIREBALL_SPEED, BOSS_FIREBALL_R, BOSS_FIREBALL_INTERVAL,
    BOSS_FIREBALL_GRAVITY,
    NEON_PINK, NEON_YELLOW, WHITE,
)
from src.asset_loader import assets


# ─────────────────────────────────────────────────────────────────────────────
#  FIREBALL PROJECTILE
# ─────────────────────────────────────────────────────────────────────────────

class Fireball(pygame.sprite.Sprite):
    """
    Parabolic fireball launched by the boss toward the player's position.
    """

    _COLOURS = [
        (255, 80,  0  ),   # orange core
        (255, 180, 0  ),   # yellow ring
        (255, 40,  40 ),   # red outer glow
    ]

    def __init__(self, ox: int, oy: int, tx: int, ty: int) -> None:
        """
        Parameters
        ----------
        ox, oy : fireball origin (boss centre)
        tx, ty : target position (player centre at time of launch)
        """
        super().__init__()
        self.alive_flag = True

        dx     = tx - ox
        dy     = ty - oy
        dist   = max(math.hypot(dx, dy), 1)
        # Normalise and scale to fireball speed
        self._vx = (dx / dist) * BOSS_FIREBALL_SPEED
        self._vy = (dy / dist) * BOSS_FIREBALL_SPEED * 0.6  # flatter arc
        self._x  = float(ox)
        self._y  = float(oy)

        r = BOSS_FIREBALL_R
        self.image = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        self.rect  = pygame.Rect(int(self._x) - r, int(self._y) - r, r * 2, r * 2)

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        self._vy += BOSS_FIREBALL_GRAVITY
        self._x  += self._vx
        self._y  += self._vy

        r          = BOSS_FIREBALL_R
        self.rect  = pygame.Rect(
            int(self._x) - r, int(self._y) - r, r * 2, r * 2
        )

        # Kill when off-screen or below floor
        if (self._x < -r or self._x > SCREEN_W + r or
                self._y > FLOOR_Y + r):
            self.alive_flag = False
            self.kill()

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        cx, cy = int(self._x), int(self._y)
        r = BOSS_FIREBALL_R
        # Glow
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 80, 0, 60), (r * 2, r * 2), r * 2)
        surface.blit(glow, (cx - r * 2, cy - r * 2))
        # Rings from outside to inside
        for i, col in enumerate(reversed(self._COLOURS)):
            radius = max(r - i * (r // 3), 3)
            pygame.draw.circle(surface, col, (cx, cy), radius)
        # Bright centre
        pygame.draw.circle(surface, WHITE, (cx, cy), max(r // 4, 2))


# ─────────────────────────────────────────────────────────────────────────────
#  BOSS MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class BossManager:
    """
    Orchestrates the boss character's two-phase state machine.

    Usage
    ─────
      boss = BossManager()
      # each frame:
      boss.update(karen_rect)
      boss.draw(surface)
      boss.fireballs  →  group containing active Fireball sprites
    """

    PHASE_ATTACK = "attack"
    PHASE_IDLE   = "idle"

    def __init__(self) -> None:
        # ── state ─────────────────────────────────────────────────────────
        self.phase       : str  = self.PHASE_IDLE
        self.health      : int  = BOSS_HEALTH
        self.alive       : bool = True
        self._phase_timer: int  = BOSS_IDLE_DURATION
        self._fb_timer   : int  = 0
        self.hit_flash   : int  = 0

        # ── sprite ────────────────────────────────────────────────────────
        self._idle_img   = assets["boss_idle"]
        self._attack_img = assets["boss_attack"]
        self.image       = self._idle_img
        w, h             = self.image.get_size()

        # Boss sits on the floor, right side of screen
        spawn_y  = FLOOR_Y - h
        self.rect = pygame.Rect(BOSS_SPAWN_X, spawn_y, w, h)

        # ── projectiles ────────────────────────────────────────────────────
        self.fireballs = pygame.sprite.Group()

    # ── public helpers ────────────────────────────────────────────────────

    @property
    def is_vulnerable(self) -> bool:
        return self.phase == self.PHASE_IDLE

    @property
    def centre(self) -> tuple[int, int]:
        return self.rect.centerx, self.rect.centery

    # ── update ────────────────────────────────────────────────────────────

    def update(self, karen_rect: pygame.Rect) -> None:
        if not self.alive:
            return

        self._phase_timer -= 1

        if self.phase == self.PHASE_IDLE:
            self._update_idle()
        else:
            self._update_attack(karen_rect)

        self.fireballs.update()

        if self.hit_flash > 0:
            self.hit_flash -= 1

    def _update_idle(self) -> None:
        self.image = self._idle_img
        if self._phase_timer <= 0:
            self._switch_to_attack()

    def _update_attack(self, karen_rect: pygame.Rect) -> None:
        self.image  = self._attack_img
        self._fb_timer -= 1

        if self._fb_timer <= 0:
            self._launch_fireball(karen_rect)
            self._fb_timer = BOSS_FIREBALL_INTERVAL

        if self._phase_timer <= 0:
            self._switch_to_idle()

    # ── phase transitions ─────────────────────────────────────────────────

    def _switch_to_idle(self) -> None:
        self.phase        = self.PHASE_IDLE
        self._phase_timer = BOSS_IDLE_DURATION

    def _switch_to_attack(self) -> None:
        self.phase        = self.PHASE_ATTACK
        self._phase_timer = BOSS_ATTACK_DURATION
        self._fb_timer    = 30  # short delay before first fireball

    # ── fireball ──────────────────────────────────────────────────────────

    def _launch_fireball(self, karen_rect: pygame.Rect) -> None:
        ox, oy = self.centre
        tx     = karen_rect.centerx
        ty     = karen_rect.centery
        fb     = Fireball(ox, oy, tx, ty)
        self.fireballs.add(fb)

    # ── damage ────────────────────────────────────────────────────────────

    def take_hit(self, damage: int = 1) -> None:
        if not self.is_vulnerable:
            return
        self.health    -= damage
        self.hit_flash  = 12
        if self.health <= 0:
            self.alive = False
            self.fireballs.empty()

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return

        # Draw fireballs
        for fb in self.fireballs:
            fb.draw(surface)

        # Boss sprite with optional hit-flash overlay
        img = self.image
        if self.hit_flash > 0:
            img = img.copy()
            img.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(img, self.rect.topleft)

        # Phase indicator glow ring above boss
        self._draw_phase_indicator(surface)
        self._draw_health_bar(surface)

    def _draw_phase_indicator(self, surface: pygame.Surface) -> None:
        cx   = self.rect.centerx
        cy   = self.rect.top - 18
        col  = NEON_PINK if self.phase == self.PHASE_ATTACK else (0, 255, 120)
        label = "IMMUNE" if self.phase == self.PHASE_ATTACK else "VULNERABLE"
        font = get_mono(14, bold=True)
        txt  = font.render(label, True, col)
        surface.blit(txt, (cx - txt.get_width() // 2, cy - 10))

    def _draw_health_bar(self, surface: pygame.Surface) -> None:
        bar_w = self.rect.width
        bar_h = 10
        bx    = self.rect.x
        by    = self.rect.top - 28
        # Background
        pygame.draw.rect(surface, (40, 10, 10), (bx, by, bar_w, bar_h))
        # Fill
        fill_w = int(bar_w * (self.health / BOSS_HEALTH))
        fill_c = NEON_PINK if self.phase == self.PHASE_ATTACK else (0, 220, 100)
        pygame.draw.rect(surface, fill_c, (bx, by, fill_w, bar_h))
        # Border
        pygame.draw.rect(surface, WHITE, (bx, by, bar_w, bar_h), 2)
