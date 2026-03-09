"""
hud.py — Heads-Up Display and visual feedback (particles, notifications).

Components
──────────
  HUD           — draws all persistent UI elements (score, hearts, tier,
                  boss health bar, instructions).
  Particle      — short-lived coloured spark used for hit/collect FX.
  ParticleSystem — manages a pool of Particle instances.
  Notification   — brief floating text message (level-up, boss kill, etc.)
"""

from __future__ import annotations
import math
import random
import pygame

from src.fonts import get_mono
from src.settings import (
    SCREEN_W, SCREEN_H,
    NEON_CYAN, NEON_PINK, NEON_YELLOW, NEON_GREEN,
    DARK_BG, WHITE, GOLD,
    KAREN_MAX_HEALTH, TIER_THRESHOLDS,
)


# ─────────────────────────────────────────────────────────────────────────────
#  PARTICLE
# ─────────────────────────────────────────────────────────────────────────────

class Particle:
    """A single coloured spark that fades and moves outward."""

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "colour", "radius")

    def __init__(self, x: float, y: float, colour: tuple,
                 speed: float = 4.0, life: int = 30) -> None:
        angle       = random.uniform(0, math.tau)
        s           = random.uniform(speed * 0.4, speed)
        self.x      = x
        self.y      = y
        self.vx     = math.cos(angle) * s
        self.vy     = math.sin(angle) * s - random.uniform(0, 2)
        self.life    = life
        self.max_life = life
        self.colour  = colour
        self.radius  = random.randint(2, 5)

    def update(self) -> bool:
        """Return True while still alive."""
        self.x    += self.vx
        self.y    += self.vy
        self.vy   += 0.12    # slight gravity
        self.life -= 1
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha  = int(255 * (self.life / self.max_life))
        r      = max(int(self.radius * (self.life / self.max_life)), 1)
        col    = (*self.colour, alpha)
        surf   = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, col, (r, r), r)
        surface.blit(surf, (int(self.x) - r, int(self.y) - r))


# ─────────────────────────────────────────────────────────────────────────────
#  PARTICLE SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class ParticleSystem:
    """Manages a list of Particle objects."""

    def __init__(self) -> None:
        self._particles: list[Particle] = []

    def emit(self, x: float, y: float, colour: tuple,
             count: int = 12, speed: float = 4.0, life: int = 35) -> None:
        for _ in range(count):
            self._particles.append(Particle(x, y, colour, speed, life))

    def update(self) -> None:
        self._particles = [p for p in self._particles if p.update()]

    def draw(self, surface: pygame.Surface) -> None:
        for p in self._particles:
            p.draw(surface)

    def emit_hit(self, x: float, y: float) -> None:
        self.emit(x, y, NEON_PINK,   count=14, speed=5)

    def emit_collect(self, x: float, y: float, token_type: str) -> None:
        col = NEON_CYAN if token_type == "bonus" else NEON_YELLOW
        self.emit(x, y, col, count=20, speed=6, life=45)

    def emit_boss_hit(self, x: float, y: float) -> None:
        self.emit(x, y, NEON_YELLOW, count=18, speed=7, life=40)
        self.emit(x, y, WHITE,       count=8,  speed=9, life=20)


# ─────────────────────────────────────────────────────────────────────────────
#  FLOATING NOTIFICATION
# ─────────────────────────────────────────────────────────────────────────────

class Notification:
    """Floating text that drifts upward and fades out."""

    def __init__(self, text: str, x: int, y: int,
                 colour: tuple = NEON_CYAN,
                 font_size: int = 26,
                 duration: int = 90) -> None:
        self._text     = text
        self._x        = float(x)
        self._y        = float(y)
        self._colour   = colour
        self._duration = duration
        self._age      = 0
        self._font     = get_mono(font_size, bold=True)

    def update(self) -> bool:
        self._age  += 1
        self._y    -= 0.8   # drift upward
        return self._age < self._duration

    def draw(self, surface: pygame.Surface) -> None:
        alpha = max(0, 255 - int(255 * (self._age / self._duration)))
        txt   = self._font.render(self._text, True, self._colour)
        txt.set_alpha(alpha)
        surface.blit(txt, (int(self._x) - txt.get_width() // 2, int(self._y)))


class NotificationSystem:
    """Manages floating notifications."""

    def __init__(self) -> None:
        self._notes: list[Notification] = []

    def add(self, text: str, x: int, y: int,
            colour: tuple = NEON_CYAN, font_size: int = 26,
            duration: int = 90) -> None:
        self._notes.append(Notification(text, x, y, colour, font_size, duration))

    def update(self) -> None:
        self._notes = [n for n in self._notes if n.update()]

    def draw(self, surface: pygame.Surface) -> None:
        for n in self._notes:
            n.draw(surface)


# ─────────────────────────────────────────────────────────────────────────────
#  HUD
# ─────────────────────────────────────────────────────────────────────────────

class HUD:
    """
    Renders all persistent UI elements:
      • Health hearts (top-left)
      • Tier badge + level-up count (top-left under hearts)
      • Score (top-left under tier)
      • Mini boss health bar (top-right, when boss is active)
      • Controls reminder (bottom strip)
      • Game-Over / Victory overlay
    """

    _HEART_FULL  = (220, 30,  60 )
    _HEART_EMPTY = (50,  15,  20 )
    _HEART_SIZE  = 28
    _HEART_GAP   = 10

    def __init__(self) -> None:
        self._font_sm  = get_mono(16, bold=True)
        self._font_md  = get_mono(22, bold=True)
        self._font_lg  = get_mono(54, bold=True)
        self._font_xl  = get_mono(80, bold=True)

    # ── main draw ────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface,
             health: int, tier: int, score: int,
             level_up_count: int,
             boss_health: int, boss_max: int,
             boss_active: bool, boss_phase: str) -> None:

        self._draw_panel(surface)
        self._draw_hearts(surface, health)
        self._draw_tier(surface, tier, level_up_count)
        self._draw_score(surface, score)
        if boss_active:
            self._draw_boss_hud(surface, boss_health, boss_max, boss_phase)
        self._draw_controls_hint(surface)

    # ── panel backdrop ────────────────────────────────────────────────────

    def _draw_panel(self, surface: pygame.Surface) -> None:
        panel = pygame.Surface((300, 126), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        pygame.draw.rect(panel, NEON_CYAN, panel.get_rect(), 1)
        surface.blit(panel, (8, 8))

    # ── hearts ────────────────────────────────────────────────────────────

    def _draw_hearts(self, surface: pygame.Surface, health: int) -> None:
        hs = self._HEART_SIZE
        for i in range(KAREN_MAX_HEALTH):
            col = self._HEART_FULL if i < health else self._HEART_EMPTY
            cx  = 22 + i * (hs + self._HEART_GAP)
            cy  = 22
            # Two circles + triangle = heart
            pygame.draw.circle(surface, col, (cx + hs // 4,      cy),     hs // 4)
            pygame.draw.circle(surface, col, (cx + 3 * hs // 4,  cy),     hs // 4)
            points = [
                (cx,           cy + hs // 4),
                (cx + hs // 2, cy + hs * 3 // 4),
                (cx + hs,      cy + hs // 4),
            ]
            pygame.draw.polygon(surface, col, points)
            # Sheen
            pygame.draw.circle(surface, (255, 160, 180),
                               (cx + hs // 3, cy - 2), 3)

    # ── tier badge ────────────────────────────────────────────────────────

    def _draw_tier(self, surface: pygame.Surface,
                   tier: int, level_up_count: int) -> None:
        tier_cols = {1: NEON_CYAN, 2: NEON_YELLOW, 3: NEON_PINK}
        col       = tier_cols.get(tier, NEON_CYAN)
        stars     = "\u2605" * tier + "\u2606" * (3 - tier)
        txt       = self._font_md.render(f"TIER {tier}  {stars}", True, col)
        surface.blit(txt, (16, 58))
        # Progress bar toward next tier
        if tier < 3:
            next_thresh = TIER_THRESHOLDS.get(tier + 1, 99)
            prog_txt = self._font_sm.render(
                f"LVL-UP: {level_up_count}/{next_thresh}  [kill skaters]",
                True, col
            )
            surface.blit(prog_txt, (16, 83))

    # ── score ─────────────────────────────────────────────────────────────

    def _draw_score(self, surface: pygame.Surface, score: int) -> None:
        txt = self._font_sm.render(
            f"CREDITS  {score:>7,}", True, NEON_CYAN
        )
        surface.blit(txt, (16, 101))

    # ── boss HUD ──────────────────────────────────────────────────────────

    def _draw_boss_hud(self, surface: pygame.Surface,
                       health: int, max_hp: int, phase: str) -> None:
        bw   = 280
        bh   = 18
        bx   = SCREEN_W - bw - 14
        by   = 14
        fill = int(bw * (max(health, 0) / max_hp))

        # Label
        label_col  = NEON_PINK if phase == "attack" else NEON_GREEN
        phase_txt  = "ATTACK PHASE" if phase == "attack" else "IDLE — VULNERABLE"
        lbl        = self._font_sm.render(f"BOSS  {phase_txt}", True, label_col)
        surface.blit(lbl, (bx, by - 18))

        # Bar
        pygame.draw.rect(surface, (40, 10, 10), (bx, by, bw, bh))
        pygame.draw.rect(surface, label_col,    (bx, by, fill, bh))
        pygame.draw.rect(surface, WHITE,        (bx, by, bw, bh), 2)

    # ── controls hint ─────────────────────────────────────────────────────

    def _draw_controls_hint(self, surface: pygame.Surface) -> None:
        hint_surf = pygame.Surface((SCREEN_W, 24), pygame.SRCALPHA)
        hint_surf.fill((0, 0, 0, 80))
        surface.blit(hint_surf, (0, SCREEN_H - 24))
        txt = self._font_sm.render(
            "  A/D or ←/→ : MOVE     SPACE : JUMP     F : SOUND WAVE",
            True, (140, 140, 180)
        )
        surface.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, SCREEN_H - 22))

    # ── overlays ──────────────────────────────────────────────────────────

    def draw_game_over(self, surface: pygame.Surface) -> None:
        self._draw_overlay(surface, "GAME OVER", NEON_PINK,
                           "Press R to Restart or Q to Quit")

    def draw_victory(self, surface: pygame.Surface) -> None:
        self._draw_overlay(surface, "VICTORY!", NEON_YELLOW,
                           "Karen has conquered the retail floor!  Press R or Q")

    def _draw_overlay(self, surface: pygame.Surface,
                      title: str, colour: tuple, sub: str) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        title_txt = self._font_xl.render(title, True, colour)
        sub_txt   = self._font_md.render(sub,   True, WHITE)
        cx        = SCREEN_W // 2
        cy        = SCREEN_H // 2
        surface.blit(title_txt, (cx - title_txt.get_width() // 2, cy - 80))
        surface.blit(sub_txt,   (cx - sub_txt.get_width()   // 2, cy + 30))

    def draw_tier_up(self, surface: pygame.Surface, tier: int) -> None:
        """Full-screen brief flash for tier upgrade."""
        colours = {2: NEON_YELLOW, 3: NEON_PINK}
        col    = colours.get(tier, NEON_CYAN)
        flash  = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        flash.fill((*col, 30))
        surface.blit(flash, (0, 0))
        txt = self._font_lg.render(f"TIER {tier} UNLOCKED!", True, col)
        surface.blit(txt,
                     (SCREEN_W // 2 - txt.get_width() // 2,
                      SCREEN_H // 2 - txt.get_height() // 2))
