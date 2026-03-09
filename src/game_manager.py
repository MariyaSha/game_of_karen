"""
game_manager.py — Central orchestrator for Game of Karen.

Owns the game loop, wires all subsystems together, and manages the
high-level game-state machine:

  PLAYING  →  GAME_OVER
           →  BOSS_INTRO  →  PLAYING (with boss)
           →  VICTORY

Responsibilities
────────────────
  • Tick all subsystems in correct order each frame.
  • Resolve collision detections (wave ↔ enemy, wave ↔ boss,
    enemy ↔ karen, fireball ↔ karen, token ↔ karen).
  • Spawn Slackers on platforms at startup.
  • Trigger boss entrance after score threshold.
  • Pass data to HUD for rendering.
  • Drive a dynamic camera (self.camera_x) that follows Karen,
    with seamlessly tiling background scrolling.
"""

from __future__ import annotations
import random
import pygame

from src.settings import (
    SCREEN_W, SCREEN_H, FPS, TITLE,
    FLOOR_Y, PLATFORM_DEFS,
    WORLD_W, BOSS_TRIGGER_X, BOSS_SPAWN_DELAY_FRAMES, BOSS_SPAWN_X,
    NEON_CYAN, NEON_PINK, NEON_YELLOW, WHITE,
)
from src.asset_loader  import assets, load_all
from src.karen         import Karen, SoundWave
from src.enemies       import (FlyerEnemy, SkaterEnemy, SlackerEnemy,
                                spawn_slacker)
from src.boss          import BossManager
from src.platform      import Platform, create_platforms
from src.tokens        import Token, make_token
from src.spawner       import EnemySpawner
from src.hud           import HUD, ParticleSystem, NotificationSystem


# ─────────────────────────────────────────────────────────────────────────────
#  GAME STATES
# ─────────────────────────────────────────────────────────────────────────────

class GameState:
    PLAYING   = "playing"
    GAME_OVER = "game_over"
    VICTORY   = "victory"
    BOSS_INTRO= "boss_intro"


# ─────────────────────────────────────────────────────────────────────────────
#  GAME MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class GameManager:

    # How fast the camera trails Karen (0 = instant, 1 = never)
    _CAM_LAG  = 0.08
    # Where Karen is held on screen (left third)
    _CAM_FOCUS_X = SCREEN_W // 3
    # Maximum camera_x before the boss arena wall (hard right boundary)
    # Camera cannot scroll past BOSS_TRIGGER_X so Karen stays in the arena.
    _CAM_MAX  = float(BOSS_TRIGGER_X)

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen  = screen
        self.clock   = pygame.time.Clock()
        self._state  = GameState.PLAYING

        # ── CAMERA ────────────────────────────────────────────────────────
        self.camera_x : float = 0.0

        # ── BOSS SPAWN TIMER ──────────────────────────────────────────────
        # Boss spawns ONLY after Karen reaches the boss arena (camera_x >= _CAM_MAX).
        # Once she arrives, we give a short delay (BOSS_SPAWN_DELAY_FRAMES after arrival)
        # before the boss appears, so she can see the arena first.
        self._boss_frame_timer: int = BOSS_SPAWN_DELAY_FRAMES  # counts down after arrival
        self._karen_reached_arena: bool = False   # True once camera reaches _CAM_MAX
        # Proximity-warning zones (world-X thresholds, counting from right edge)
        self._approaching_warned_far  : bool = False  # shown at ~2 screens away
        self._approaching_warned_near : bool = False  # shown at ~1 screen away

        # ── subsystems ────────────────────────────────────────────────────
        self.hud          = HUD()
        self.particles    = ParticleSystem()
        self.notifications= NotificationSystem()

        # ── sprite groups ─────────────────────────────────────────────────
        self.waves    = pygame.sprite.Group()   # SoundWave projectiles
        self.enemies  = pygame.sprite.Group()   # all active enemies
        self.tokens   = pygame.sprite.Group()   # collectible tokens

        # ── world objects ─────────────────────────────────────────────────
        self.platforms : list[Platform] = create_platforms()
        self.karen     = Karen()
        self.boss      : BossManager | None = None
        self._boss_active  = False
        self._boss_spawned = False

        # Tier-up flash timer
        self._tier_flash  : int = 0
        self._tier_flash_val: int = 0

        # ── enemy spawner ─────────────────────────────────────────────────
        self.spawner = EnemySpawner(self.enemies, self.tokens)

        # Spawn Slackers on platforms at startup
        self._init_platform_slackers()

        # ── HUD progress: show time-to-boss countdown ─────────────────────
        self._boss_countdown_shown: bool = False

    # ── initialisation ────────────────────────────────────────────────────

    def _init_platform_slackers(self) -> None:
        for plat in self.platforms:
            if not plat.slacker_spawned:
                slacker = spawn_slacker(plat)
                self.enemies.add(slacker)
                plat.slacker_spawned = True

    # ── main game loop ────────────────────────────────────────────────────

    def run(self) -> None:
        """Block until the user quits."""
        running = True
        while running:
            dt = self.clock.tick(FPS)
            running = self._handle_events()
            self._update()
            self._draw()

    # ── event handling ────────────────────────────────────────────────────

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return False
                if event.key == pygame.K_r:
                    self._restart()
        return True

    def _restart(self) -> None:
        """Full game reset."""
        self.waves.empty()
        self.enemies.empty()
        self.tokens.empty()
        self.particles   = ParticleSystem()
        self.notifications = NotificationSystem()
        self.platforms   = create_platforms()
        self.karen       = Karen()
        self.boss        = None
        self._boss_active  = False
        self._boss_spawned = False
        self._tier_flash   = 0
        self.camera_x      = 0.0
        self._boss_frame_timer = BOSS_SPAWN_DELAY_FRAMES
        self._boss_countdown_shown = False
        self._karen_reached_arena  = False
        self._approaching_warned_far  = False
        self._approaching_warned_near = False
        self.spawner = EnemySpawner(self.enemies, self.tokens)
        self._init_platform_slackers()
        self._state  = GameState.PLAYING

    # ── camera ────────────────────────────────────────────────────────────

    def _update_camera(self) -> None:
        """
        Smoothly lag the camera toward Karen, clamped to world bounds.

        Hard right limit = BOSS_TRIGGER_X (boss arena left edge).
        This prevents Karen from scrolling the camera past the boss arena,
        so the boss is always visible within the final screen.
        """
        target_cam = self.karen.pos.x - self._CAM_FOCUS_X
        self.camera_x += (target_cam - self.camera_x) * (1.0 - self._CAM_LAG)
        # Clamp: never left of origin, never right past boss arena
        self.camera_x = max(0.0, min(self.camera_x, self._CAM_MAX))

    def _world_to_screen(self, world_x: float) -> int:
        """Convert a world-X coordinate to screen-X."""
        return int(world_x - self.camera_x)

    # ── update ────────────────────────────────────────────────────────────

    def _update(self) -> None:
        if self._state == GameState.PLAYING:
            self._update_playing()
        # GAME_OVER / VICTORY: no physics, just wait for key

    def _update_playing(self) -> None:
        keys = pygame.key.get_pressed()

        # Karen input + movement
        self.karen.handle_input(keys, self.waves)
        self._clamp_karen_to_world()   # enforce world boundaries
        self.karen.apply_gravity()
        self.karen.resolve_floor()
        self.karen.platform_collide(self.platforms)
        self.karen.update()

        # Decrement tier-flash overlay timer each frame
        if self._tier_flash > 0:
            self._tier_flash -= 1

        # ── FIX 1: update camera after Karen moves ────────────────────────
        self._update_camera()

        # Update waves
        self.waves.update()

        # Spawner — pass camera_x so enemies spawn ahead of Karen in world space
        self.spawner.update(self.camera_x)

        # Update enemies
        for enemy in list(self.enemies):
            enemy.update()

        # Update tokens — pass Karen's world rect for magnet logic
        for tok in list(self.tokens):
            tok.update(self.karen.rect)

        # ── Boss proximity warnings (before Karen reaches the arena) ──────
        if not self._boss_spawned:
            karen_x = self.karen.pos.x
            # Far warning: ~2 screens before the boss trigger
            if not self._approaching_warned_far and karen_x >= BOSS_TRIGGER_X - SCREEN_W * 2:
                self._approaching_warned_far = True
                self.notifications.add(
                    "\U0001f4a1  APPROACHING MANAGER  \U0001f4a1",
                    SCREEN_W // 2, SCREEN_H // 3,
                    NEON_YELLOW, font_size=26, duration=150,
                )
            # Near warning: ~half screen before the boss trigger
            if not self._approaching_warned_near and karen_x >= BOSS_TRIGGER_X - SCREEN_W // 2:
                self._approaching_warned_near = True
                self.notifications.add(
                    "\u26a0  THE MANAGER IS WAITING  \u26a0",
                    SCREEN_W // 2, SCREEN_H // 3,
                    NEON_PINK, font_size=30, duration=180,
                )

            # Once the camera is locked at the boss arena, start the arrival countdown
            if not self._karen_reached_arena and self.camera_x >= self._CAM_MAX - 5:
                self._karen_reached_arena = True

            if self._karen_reached_arena:
                self._boss_frame_timer -= 1
                # 3-second warning just before boss appears
                if self._boss_frame_timer == 180 and not self._boss_countdown_shown:
                    self._boss_countdown_shown = True
                    self.notifications.add(
                        "\u26a0  THE MANAGER ARRIVES  \u26a0",
                        SCREEN_W // 2, SCREEN_H // 3,
                        NEON_YELLOW, font_size=34, duration=180,
                    )
                if self._boss_frame_timer <= 0:
                    self._spawn_boss()

        if self._boss_active and self.boss:
            self.boss.update(self.karen.rect)

        # Collisions
        self._resolve_wave_enemy_collisions()
        self._resolve_wave_boss_collisions()
        self._resolve_enemy_karen_collisions()
        self._resolve_fireball_karen_collisions()
        self._resolve_token_karen_collisions()

        # Particles / notifications
        self.particles.update()
        self.notifications.update()

        # Check end conditions
        if not self.karen.alive:
            self._state = GameState.GAME_OVER

        if self._boss_active and self.boss and not self.boss.alive:
            self._state = GameState.VICTORY

    # ── boss spawn ────────────────────────────────────────────────────────

    def _spawn_boss(self) -> None:
        self.boss          = BossManager()
        self._boss_active  = True
        self._boss_spawned = True
        # Clear non-boss enemies so the arena is clear
        for enemy in list(self.enemies):
            if not isinstance(enemy, SlackerEnemy):
                enemy.kill()

        # Karen is already inside the arena (camera locked here).
        # Ensure she is at the arena entrance so she faces the boss.
        arena_entrance = float(BOSS_TRIGGER_X + 80)
        if self.karen.pos.x < arena_entrance:
            self.karen.pos.x = arena_entrance

        self.notifications.add(
            "\u26a0  THE MANAGER ARRIVES  \u26a0",
            SCREEN_W // 2, SCREEN_H // 3,
            NEON_PINK, font_size=34, duration=150,
        )

    # ── Karen world-X clamp (arena wall after boss spawns) ────────────────

    def _clamp_karen_to_world(self) -> None:
        """
        Before boss: Karen can walk freely up to WORLD_W.
        After boss spawns: Karen is locked inside the boss arena
          (BOSS_TRIGGER_X  ≤  Karen.pos.x  ≤  WORLD_W - karen_w).
        """
        if not self._boss_spawned:
            # Prevent walking off left edge only
            self.karen.pos.x = max(0.0, self.karen.pos.x)
        else:
            karen_w = self.karen.rect.width
            self.karen.pos.x = max(
                float(BOSS_TRIGGER_X),
                min(self.karen.pos.x, float(WORLD_W - karen_w))
            )

    # ── collision resolution ──────────────────────────────────────────────

    def _resolve_wave_enemy_collisions(self) -> None:
        for wave in list(self.waves):
            for enemy in list(self.enemies):
                if wave.rect.colliderect(enemy.rect):
                    enemy.take_hit(1)
                    self.particles.emit_hit(
                        enemy.rect.centerx, enemy.rect.centery
                    )
                    # Token drop on death
                    if not enemy.alive:
                        drop = enemy.get_drop()
                        EnemySpawner.drop_token(
                            self.tokens, drop,
                            enemy.rect.centerx, enemy.rect.top
                        )
                        score_gain = 50 if drop == "bonus" else 150
                        self.karen.score += score_gain
                        self.notifications.add(
                            f"+{score_gain}",
                            self._world_to_screen(enemy.rect.centerx),
                            enemy.rect.top - 20,
                            NEON_CYAN, font_size=18, duration=50
                        )
                    wave.kill()
                    break

    def _resolve_wave_boss_collisions(self) -> None:
        if not self._boss_active or not self.boss:
            return
        for wave in list(self.waves):
            if (self.boss.is_vulnerable and
                    wave.rect.colliderect(self.boss.rect)):
                self.boss.take_hit(1)
                self.particles.emit_boss_hit(
                    self.boss.rect.centerx, self.boss.rect.centery
                )
                self.notifications.add(
                    "CRITICAL HIT!",
                    self._world_to_screen(self.boss.rect.centerx),
                    self.boss.rect.top - 30,
                    NEON_YELLOW, font_size=22, duration=60,
                )
                wave.kill()

    def _resolve_enemy_karen_collisions(self) -> None:
        if self.karen._iframe_timer > 0:
            return
        for enemy in self.enemies:
            if enemy.rect.colliderect(self.karen.rect):
                prev_tier = self.karen.tier
                self.karen.take_damage(1)
                self.particles.emit_hit(
                    self.karen.rect.centerx, self.karen.rect.centery
                )
                self._check_tier_regression(prev_tier)
                break

    def _resolve_fireball_karen_collisions(self) -> None:
        if not self._boss_active or not self.boss:
            return
        if self.karen._iframe_timer > 0:
            return
        for fb in list(self.boss.fireballs):
            if fb.rect.colliderect(self.karen.rect):
                prev_tier = self.karen.tier
                self.karen.take_damage(1)
                self.particles.emit_hit(
                    self.karen.rect.centerx, self.karen.rect.centery
                )
                self._check_tier_regression(prev_tier)
                fb.kill()
                break

    def _check_tier_regression(self, prev_tier: int) -> None:
        """If Karen's tier dropped back to 1 this frame, fire a regression notification."""
        if prev_tier > 1 and self.karen.tier == 1:
            self._tier_flash     = 120
            self._tier_flash_val = 1
            self.notifications.add(
                "⚠  TIER LOST — COLLECT TOKENS AGAIN  ⚠",
                SCREEN_W // 2, SCREEN_H // 2 - 80,
                NEON_PINK, font_size=28, duration=150,
            )

    def _resolve_token_karen_collisions(self) -> None:
        """
        Collect tokens whose inflated world-space rect overlaps Karen's rect.

        Tokens now carry an expanded rect (TOKEN_COLLECT_PAD inflated on each
        side) so the collection window is generously wide.
        Also catches any token that is within 80 px horizontally of Karen
        and on the same Y-band (belt-level safety net).
        """
        prev_tier = self.karen.tier
        k_rect    = self.karen.rect   # world-space

        for tok in list(self.tokens):
            # Primary check: rect overlap (uses inflated token rect)
            hit = tok.rect.colliderect(k_rect)

            # Safety-net: close horizontal approach even without rect overlap
            if not hit:
                dx   = abs(tok._x + tok.image.get_width()  // 2 - k_rect.centerx)
                dy   = abs(tok._y + tok.image.get_height() // 2 - k_rect.centery)
                hit  = (dx < 80 and dy < 70)

            if hit:
                self.particles.emit_collect(
                    self._world_to_screen(int(tok._x)), int(tok._y), tok.token_type
                )
                if tok.token_type == "bonus":
                    self.karen.collect_bonus()
                    self.notifications.add(
                        "+100 CREDITS",
                        self._world_to_screen(int(tok._x)),
                        int(tok._y) - 16,
                        NEON_CYAN, font_size=18, duration=50,
                    )
                elif tok.token_type == "level_up":
                    old_tier = self.karen.tier
                    self.karen.collect_level_up()      # increments count + may set tier
                    self.karen.reload_tier_frames()    # swap sprite immediately
                    self.notifications.add(
                        f"LEVEL UP TOKEN! ({self.karen.level_up_count})",
                        self._world_to_screen(int(tok._x)),
                        int(tok._y) - 16,
                        NEON_YELLOW, font_size=20, duration=70,
                    )
                    # Immediate tier-flash when tier actually changed
                    if self.karen.tier != old_tier:
                        self._tier_flash     = 120
                        self._tier_flash_val = self.karen.tier
                tok.kill()

        # Tier notification (catches any tier change this frame)
        if self.karen.tier != prev_tier:
            self.notifications.add(
                f"\u2605  TIER {self.karen.tier} EVOLVED  \u2605",
                SCREEN_W // 2, SCREEN_H // 2 - 60,
                NEON_PINK, font_size=36, duration=150,
            )

    # ── draw ──────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        cam   = int(self.camera_x)
        bg    = assets["background"]
        bg_w  = bg.get_width()   # scaled background width (= SCREEN_W)

        # ── FIX 1: tiling background wrap ─────────────────────────────────
        # offset is the x-position of the first tile's left edge on screen.
        # Using modulo ensures it wraps seamlessly.
        offset = -(cam % bg_w)
        # Draw enough tiles to cover SCREEN_W even when offset is negative
        x = offset
        while x < SCREEN_W:
            self.screen.blit(bg, (x, 0))
            x += bg_w

        # ── FIX 1: all world objects drawn with camera offset ──────────────

        # Platforms
        for plat in self.platforms:
            plat.draw(self.screen, cam)

        # Tokens
        for tok in self.tokens:
            tok.draw(self.screen, cam)

        # Enemies
        for enemy in self.enemies:
            enemy.draw(self.screen, cam)

        # Boss + fireballs
        if self._boss_active and self.boss:
            self.boss.draw(self.screen, cam)

        # Sound waves (world-space rect, camera-translated for draw)
        for wave in self.waves:
            wave.draw(self.screen, cam)

        # Karen (always drawn at screen-space pos = world_x - cam)
        self.karen.draw(self.screen, cam)

        # Particles (screen-space already)
        self.particles.draw(self.screen)

        # Notifications (screen-space already)
        self.notifications.draw(self.screen)

        # Tier-up flash overlay
        if self._tier_flash > 0:
            self.hud.draw_tier_up(self.screen, self._tier_flash_val)

        # HUD
        boss_hp  = self.boss.health if self.boss else 0
        from src.settings import BOSS_HEALTH
        self.hud.draw(
            self.screen,
            health          = self.karen.health,
            tier            = self.karen.tier,
            score           = self.karen.score,
            level_up_count  = self.karen.level_up_count,
            boss_health     = boss_hp,
            boss_max        = BOSS_HEALTH,
            boss_active     = self._boss_active,
            boss_phase      = self.boss.phase if self.boss else "idle",
        )

        # End-state overlays
        if self._state == GameState.GAME_OVER:
            self.hud.draw_game_over(self.screen)
        elif self._state == GameState.VICTORY:
            self.hud.draw_victory(self.screen)

        pygame.display.flip()
