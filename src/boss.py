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

Fireballs  (FIX 5)
──────────
  Spawn at the boss centre and arc toward the player with a horizontal
  velocity + downward gravity (parabolic trajectory).

  FIX 5 — LINGERING FIRE POOLS:
    When a Fireball hits FLOOR_Y it transitions to '_landed = True'.
    In that state it:
      • Stops all movement.
      • Renders as a flat, pulsing elliptical fire pool.
      • Remains a damage hitbox for FIRE_POOL_DURATION frames (90).
      • Then calls self.kill() and disappears.
"""

from __future__ import annotations
import math
import random
import pygame

from src.fonts import get_mono
from src.settings import (
    SCREEN_W, SCREEN_H, FLOOR_Y,
    WORLD_W, BOSS_TRIGGER_X,
    BOSS_HEIGHT, BOSS_SPAWN_X, BOSS_SPAWN_Y,
    BOSS_HEALTH, BOSS_IDLE_DURATION, BOSS_ATTACK_DURATION,
    BOSS_FIREBALL_SPEED, BOSS_FIREBALL_R, BOSS_FIREBALL_INTERVAL,
    BOSS_FIREBALL_GRAVITY,
    NEON_PINK, NEON_YELLOW, WHITE,
)
from src.asset_loader import assets

# Duration the fire pool lingers on the floor (frames)
FIRE_POOL_DURATION = 90


# ─────────────────────────────────────────────────────────────────────────────
#  FIREBALL PROJECTILE  (with FIX 5 fire-pool state)
# ─────────────────────────────────────────────────────────────────────────────

class Fireball(pygame.sprite.Sprite):
    """
    Parabolic fireball launched by the boss toward the player's position.

    States
    ──────
      flying  : normal parabolic travel
      landed  : flattened fire-pool hazard on the floor (FIX 5)
    """

    _COLOURS = [
        (255, 80,  0  ),   # orange core
        (255, 180, 0  ),   # yellow ring
        (255, 40,  40 ),   # red outer glow
    ]

    # Fire-pool visual constants
    _POOL_RX   = 38    # pool ellipse half-width
    _POOL_RY   = 10    # pool ellipse half-height
    _POOL_COLS = [
        (255, 60,  0,  160),   # outer orange
        (255, 140, 0,  200),   # mid yellow
        (255, 230, 0,  220),   # inner bright yellow
    ]

    def __init__(self, ox: int, oy: int, tx: int, ty: int) -> None:
        super().__init__()
        self.alive_flag = True

        # ── FIX 5: state flag ─────────────────────────────────────────────
        self._landed       = False
        self._pool_timer   = 0
        self._pool_pulse_t = 0.0

        # ── FIX 2: compute direction in world space and scale to BOSS_FIREBALL_SPEED
        # Use a minimum horizontal distance so fireballs always travel meaningfully
        dx   = tx - ox
        dy   = ty - oy
        dist = max(math.hypot(dx, dy), 1)
        # Normalise then apply speed — this gives the correct world-space vector
        self._vx = (dx / dist) * BOSS_FIREBALL_SPEED
        self._vy = (dy / dist) * BOSS_FIREBALL_SPEED * 0.5
        # Clamp _vy so fireballs don't go too steeply downward (they should arc)
        self._vy = max(self._vy, -BOSS_FIREBALL_SPEED * 0.3)
        self._x  = float(ox)
        self._y  = float(oy)

        r = BOSS_FIREBALL_R
        self.image = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        self.rect  = pygame.Rect(int(self._x) - r, int(self._y) - r, r * 2, r * 2)

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self._landed:
            self._update_pool()
        else:
            self._update_flying()

    def _update_flying(self) -> None:
        self._vy += BOSS_FIREBALL_GRAVITY
        self._x  += self._vx
        self._y  += self._vy

        r = BOSS_FIREBALL_R
        self.rect = pygame.Rect(
            int(self._x) - r, int(self._y) - r, r * 2, r * 2
        )

        # Off world left edge → kill (right edge checked by WORLD_W)
        if self._x < -(r + 200) or self._x > WORLD_W + r:
            self.alive_flag = False
            self.kill()
            return

        # ── FIX 5: touch floor → transition to fire-pool ─────────────────
        if self._y >= FLOOR_Y:
            self._y          = float(FLOOR_Y)
            self._vx         = 0.0
            self._vy         = 0.0
            self._landed     = True
            self._pool_timer = FIRE_POOL_DURATION
            # Resize the hit rect to match the pool footprint
            self.rect = pygame.Rect(
                int(self._x) - self._POOL_RX,
                int(self._y) - self._POOL_RY * 2,
                self._POOL_RX * 2,
                self._POOL_RY * 2,
            )

    def _update_pool(self) -> None:
        """FIX 5: fire pool lingers for FIRE_POOL_DURATION frames then dies."""
        self._pool_timer   -= 1
        self._pool_pulse_t += 0.12
        if self._pool_timer <= 0:
            self.alive_flag = False
            self.kill()

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        if self._landed:
            self._draw_pool(surface, camera_x)
        else:
            self._draw_flying(surface, camera_x)

    def _draw_flying(self, surface: pygame.Surface, camera_x: int) -> None:
        r  = BOSS_FIREBALL_R
        cx = int(self._x) - camera_x   # world → screen
        cy = int(self._y)
        # Skip if off screen (screen-space check)
        if cx + r * 2 < 0 or cx - r * 2 > SCREEN_W:
            return
        # Glow
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 80, 0, 60), (r * 2, r * 2), r * 2)
        surface.blit(glow, (cx - r * 2, cy - r * 2))
        # Layered rings
        for i, col in enumerate(reversed(self._COLOURS)):
            radius = max(r - i * (r // 3), 3)
            pygame.draw.circle(surface, col, (cx, cy), radius)
        pygame.draw.circle(surface, WHITE, (cx, cy), max(r // 4, 2))

    def _draw_pool(self, surface: pygame.Surface, camera_x: int) -> None:
        """FIX 5: draw a flat pulsing elliptical fire pool at floor level."""
        cx = int(self._x) - camera_x   # world → screen
        cy = int(self._y)

        # Skip if off screen (screen-space check)
        if cx + self._POOL_RX * 2 < 0 or cx - self._POOL_RX * 2 > SCREEN_W:
            return

        # Fade-out alpha based on remaining time
        fade_alpha = max(0, int(255 * (self._pool_timer / FIRE_POOL_DURATION)))
        # Pulse scale for the ellipse axes
        pulse      = 1.0 + 0.15 * math.sin(self._pool_pulse_t)
        rx = int(self._POOL_RX * pulse)
        ry = int(self._POOL_RY * pulse)

        # Draw layered transparent ellipses (outside-in)
        for i, (r, g, b, base_a) in enumerate(self._POOL_COLS):
            alpha = int(base_a * fade_alpha / 255)
            srx   = max(rx - i * 8, 4)
            sry   = max(ry - i * 2, 2)
            layer = pygame.Surface((srx * 2, sry * 4), pygame.SRCALPHA)
            pygame.draw.ellipse(layer, (r, g, b, alpha),
                                layer.get_rect())
            surface.blit(layer, (cx - srx, cy - sry * 3))

        # Bright core flicker
        flicker_a = int(220 * fade_alpha / 255)
        core_surf = pygame.Surface((rx, ry * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(core_surf, (255, 255, 180, flicker_a),
                            core_surf.get_rect())
        surface.blit(core_surf, (cx - rx // 2, cy - ry * 2))


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
      boss.draw(surface, camera_x)
      boss.fireballs  →  group containing active Fireball sprites
    """

    PHASE_ATTACK = "attack"
    PHASE_IDLE   = "idle"

    def __init__(self) -> None:
        self.phase        : str  = self.PHASE_IDLE
        self.health       : int  = BOSS_HEALTH
        self.alive        : bool = True
        self._phase_timer : int  = BOSS_IDLE_DURATION
        self._fb_timer    : int  = 0
        self.hit_flash    : int  = 0

        self._idle_img    = assets["boss_idle"]
        self._attack_img  = assets["boss_attack"]
        self.image        = self._idle_img
        w, h              = self.image.get_size()

        # World-space position on the right side of the initial view
        spawn_y   = FLOOR_Y - h
        self.rect = pygame.Rect(BOSS_SPAWN_X, spawn_y, w, h)

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
        self.image      = self._attack_img
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
        self._fb_timer    = 30

    # ── fireball ──────────────────────────────────────────────────────────

    def _launch_fireball(self, karen_rect: pygame.Rect) -> None:
        ox, oy = self.centre
        fb     = Fireball(ox, oy, karen_rect.centerx, karen_rect.centery)
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

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        if not self.alive:
            return

        # Draw all fireballs (flying + pools) with camera offset
        for fb in self.fireballs:
            fb.draw(surface, camera_x)

        # Boss sprite — translate world rect to screen
        screen_x = self.rect.x - camera_x
        img = self.image
        if self.hit_flash > 0:
            img = img.copy()
            img.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(img, (screen_x, self.rect.y))

        self._draw_phase_indicator(surface, camera_x)
        self._draw_health_bar(surface, camera_x)

    def _draw_phase_indicator(self, surface: pygame.Surface,
                               camera_x: int) -> None:
        cx   = self.rect.centerx - camera_x
        cy   = self.rect.top - 18
        col  = NEON_PINK if self.phase == self.PHASE_ATTACK else (0, 255, 120)
        label = "IMMUNE" if self.phase == self.PHASE_ATTACK else "VULNERABLE"
        font = get_mono(14, bold=True)
        txt  = font.render(label, True, col)
        surface.blit(txt, (cx - txt.get_width() // 2, cy - 10))

    def _draw_health_bar(self, surface: pygame.Surface,
                         camera_x: int) -> None:
        bar_w  = self.rect.width
        bar_h  = 10
        bx     = self.rect.x - camera_x
        by     = self.rect.top - 28
        pygame.draw.rect(surface, (40, 10, 10),   (bx, by, bar_w, bar_h))
        fill_w = int(bar_w * (self.health / BOSS_HEALTH))
        fill_c = NEON_PINK if self.phase == self.PHASE_ATTACK else (0, 220, 100)
        pygame.draw.rect(surface, fill_c,          (bx, by, fill_w, bar_h))
        pygame.draw.rect(surface, WHITE,            (bx, by, bar_w,  bar_h), 2)
