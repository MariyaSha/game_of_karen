"""
spawner.py — Controls enemy and token spawn timing/positioning.

Spawn logic
───────────
• Spawn events fire on randomised frame-count intervals.
• Enemies spawn ahead of Karen in world space (camera_x + SCREEN_W + margin).
• Spawning stops when Karen reaches the boss arena (camera_x >= BOSS_TRIGGER_X).

Slackers are spawned once per Platform at game start (GameManager).
"""

from __future__ import annotations
import random
import pygame

from src.settings import (
    SCREEN_W, SPAWN_INTERVALS,
    WORLD_W, BOSS_TRIGGER_X,
    FLYER_Y_RANGE,
)
from src.enemies  import FlyerEnemy, SkaterEnemy
from src.tokens   import Token, make_token


class EnemySpawner:
    """
    Manages timed spawning of Flyer and Skater enemies.

    Usage
    ─────
      spawner = EnemySpawner(enemy_group, token_group)
      # each frame (pass current camera_x):
      spawner.update(camera_x)
    """

    _SCROLL_SPEED_EQUIV = 5

    def __init__(
        self,
        enemy_group  : pygame.sprite.Group,
        token_group  : pygame.sprite.Group,
    ) -> None:
        self._enemies = enemy_group
        self._tokens  = token_group

        self._frame_count   = 0
        self._difficulty    = 1.0

        self._flyer_timer   = self._next_flyer_interval()
        self._skater_timer  = self._next_skater_interval()

    # ── interval helpers ─────────────────────────────────────────────────

    def _next_flyer_interval(self) -> int:
        lo, hi = SPAWN_INTERVALS[0]
        px     = random.randint(lo, hi)
        return max(int(px / self._SCROLL_SPEED_EQUIV / self._difficulty), 40)

    def _next_skater_interval(self) -> int:
        lo, hi = SPAWN_INTERVALS[1]
        px     = random.randint(lo, hi)
        return max(int(px / self._SCROLL_SPEED_EQUIV / self._difficulty), 60)

    # ── update ────────────────────────────────────────────────────────────

    def update(self, camera_x: float = 0.0) -> None:
        """
        Tick the spawner for one frame.

        Parameters
        ----------
        camera_x : current world-X of the left screen edge.
                   Enemies spawn at camera_x + SCREEN_W + random margin.
                   Spawning stops near the boss arena.
        """
        self._frame_count += 1

        # Ramp up difficulty every 30 seconds
        if self._frame_count % 1800 == 0:
            self._difficulty = min(self._difficulty * 1.25, 3.0)

        # Stop spawning in the boss arena
        if camera_x >= BOSS_TRIGGER_X - SCREEN_W:
            return

        # Spawn-ahead X = right edge of current viewport + margin
        spawn_ahead = int(camera_x) + SCREEN_W

        # Flyer timer
        self._flyer_timer -= 1
        if self._flyer_timer <= 0:
            sx = spawn_ahead + random.randint(50, 300)
            sy = random.randint(*FLYER_Y_RANGE)
            self._enemies.add(FlyerEnemy(sx, sy))
            self._flyer_timer = self._next_flyer_interval()

        # Skater timer
        self._skater_timer -= 1
        if self._skater_timer <= 0:
            sx = spawn_ahead + random.randint(50, 400)
            self._enemies.add(SkaterEnemy(sx))
            self._skater_timer = self._next_skater_interval()

    # ── token drop (called by game manager on enemy death) ────────────────

    @staticmethod
    def drop_token(token_group: pygame.sprite.Group,
                   token_type : str,
                   cx         : int,
                   cy         : int) -> None:
        """Spawn a token at the given world position and add it to the group."""
        if token_type in ("bonus", "level_up"):
            tok = make_token(token_type, cx, cy)
            token_group.add(tok)
