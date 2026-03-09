"""
spawner.py — Controls enemy and token spawn timing/positioning.

Spawn logic
───────────
• Spawn events fire on randomised X-distance intervals (simulating
  horizontal scrolling rhythm without actual map scrolling).
• A lightweight timer-based system replaces scroll distance with
  real-time frame counters to keep the code self-contained.

Intervals (from settings.SPAWN_INTERVALS):
  Short interval (800-1500 px equiv.)  → Flyers
  Long  interval (1800-2500 px equiv.) → Skaters

Slackers are spawned once per Platform at game start (handled by
GameManager, not this spawner).
"""

from __future__ import annotations
import random
import pygame

from src.settings import SCREEN_W, SPAWN_INTERVALS
from src.enemies  import FlyerEnemy, SkaterEnemy, spawn_flyer, spawn_skater
from src.tokens   import Token, make_token


class EnemySpawner:
    """
    Manages timed spawning of Flyer and Skater enemies.

    Usage
    ─────
      spawner = EnemySpawner(enemy_group)
      # each frame:
      spawner.update()
    """

    # Frames-per-second conversion factor (60 fps baseline)
    # The SPAWN_INTERVALS values represent pixels at ~5px/frame scroll speed,
    # so we convert: frames = px / speed.  Speed ≈ 5 px/frame.
    _SCROLL_SPEED_EQUIV = 5

    def __init__(
        self,
        enemy_group  : pygame.sprite.Group,
        token_group  : pygame.sprite.Group,
    ) -> None:
        self._enemies = enemy_group
        self._tokens  = token_group

        # Escalation: after N seconds, intervals shrink
        self._frame_count   = 0
        self._difficulty    = 1.0     # multiplier; increases over time

        # Separate timers for each enemy type (must come after _difficulty init)
        self._flyer_timer   = self._next_flyer_interval()
        self._skater_timer  = self._next_skater_interval()

    # ── interval helpers ─────────────────────────────────────────────────

    def _next_flyer_interval(self) -> int:
        lo, hi = SPAWN_INTERVALS[0]
        px     = random.randint(lo, hi)
        frames = int(px / self._SCROLL_SPEED_EQUIV / self._difficulty)
        return max(frames, 40)

    def _next_skater_interval(self) -> int:
        lo, hi = SPAWN_INTERVALS[1]
        px     = random.randint(lo, hi)
        frames = int(px / self._SCROLL_SPEED_EQUIV / self._difficulty)
        return max(frames, 60)

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        self._frame_count  += 1

        # Ramp up difficulty every 30 seconds
        if self._frame_count % 1800 == 0:
            self._difficulty = min(self._difficulty * 1.25, 3.0)

        # Flyer timer
        self._flyer_timer  -= 1
        if self._flyer_timer <= 0:
            flyer = spawn_flyer()
            self._enemies.add(flyer)
            self._flyer_timer = self._next_flyer_interval()

        # Skater timer
        self._skater_timer -= 1
        if self._skater_timer <= 0:
            skater = spawn_skater()
            self._enemies.add(skater)
            self._skater_timer = self._next_skater_interval()

    # ── token drop (called by game manager on enemy death) ────────────────

    @staticmethod
    def drop_token(token_group: pygame.sprite.Group,
                   token_type : str,
                   cx         : int,
                   cy         : int) -> None:
        """Spawn a token at the given position and add it to the group."""
        if token_type in ("bonus", "level_up"):
            tok = make_token(token_type, cx, cy)
            token_group.add(tok)
