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

    # Score needed to unlock the boss encounter
    BOSS_SCORE_THRESHOLD = 2000

    # How fast the camera trails Karen (0 = instant, 1 = never)
    _CAM_LAG  = 0.08
    # Where Karen is held on screen (left third)
    _CAM_FOCUS_X = SCREEN_W // 3

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen  = screen
        self.clock   = pygame.time.Clock()
        self._state  = GameState.PLAYING

        # ── CAMERA ────────────────────────────────────────────────────────
        # camera_x is the world-X that maps to the left edge of the screen.
        # Starts at 0 so the origin matches screen-space on frame 1.
        self.camera_x : float = 0.0

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

        # Spawn Slackers on all platforms at game start
        self._init_platform_slackers()

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
        self.spawner = EnemySpawner(self.enemies, self.tokens)
        self._init_platform_slackers()
        self._state  = GameState.PLAYING

    # ── camera ────────────────────────────────────────────────────────────

    def _update_camera(self) -> None:
        """
        Smoothly lag the camera toward Karen's position so that she sits
        at _CAM_FOCUS_X pixels from the left edge of the screen.

        camera_x is the world coordinate of the left screen edge.
        """
        target_cam = self.karen.pos.x - self._CAM_FOCUS_X
        # Lerp towards target (lag factor: smaller = faster catch-up)
        self.camera_x += (target_cam - self.camera_x) * (1.0 - self._CAM_LAG)
        # Never scroll left of world origin
        self.camera_x = max(0.0, self.camera_x)

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
        prev_tier = self.karen.tier
        self.karen.handle_input(keys, self.waves)
        self.karen.apply_gravity()
        self.karen.resolve_floor()
        self.karen.platform_collide(self.platforms)
        self.karen.update()

        # ── FIX 4: tier changed → reload frames ───────────────────────────
        if self.karen.tier != prev_tier:
            self.karen.reload_tier_frames()
            self._tier_flash     = 90
            self._tier_flash_val = self.karen.tier

        if self._tier_flash > 0:
            self._tier_flash -= 1

        # ── FIX 1: update camera after Karen moves ────────────────────────
        self._update_camera()

        # Update waves
        self.waves.update()

        # Spawner
        self.spawner.update()

        # Update enemies
        for enemy in list(self.enemies):
            enemy.update()

        # Update tokens
        for tok in list(self.tokens):
            tok.update()

        # Boss check
        if (not self._boss_spawned and
                self.karen.score >= self.BOSS_SCORE_THRESHOLD):
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
        # Clear the floor to give Karen space
        for enemy in list(self.enemies):
            if isinstance(enemy, SkaterEnemy):
                enemy.kill()

        self.notifications.add(
            "⚠  THE MANAGER ARRIVES  ⚠",
            SCREEN_W // 2, SCREEN_H // 3,
            NEON_PINK, font_size=34, duration=150,
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
                self.karen.take_damage(1)
                self.particles.emit_hit(
                    self.karen.rect.centerx, self.karen.rect.centery
                )
                break

    def _resolve_fireball_karen_collisions(self) -> None:
        if not self._boss_active or not self.boss:
            return
        if self.karen._iframe_timer > 0:
            return
        for fb in list(self.boss.fireballs):
            if fb.rect.colliderect(self.karen.rect):
                self.karen.take_damage(1)
                self.particles.emit_hit(
                    self.karen.rect.centerx, self.karen.rect.centery
                )
                fb.kill()
                break

    def _resolve_token_karen_collisions(self) -> None:
        prev_tier = self.karen.tier
        for tok in list(self.tokens):
            if tok.rect.colliderect(self.karen.rect):
                self.particles.emit_collect(
                    tok.rect.centerx, tok.rect.centery, tok.token_type
                )
                if tok.token_type == "bonus":
                    self.karen.collect_bonus()
                    self.notifications.add(
                        "+100 CREDITS",
                        self._world_to_screen(tok.rect.centerx),
                        tok.rect.top - 16,
                        NEON_CYAN, font_size=18, duration=50,
                    )
                elif tok.token_type == "level_up":
                    # ── FIX 4: increment tier AND reload frames ────────────
                    self.karen.collect_level_up()
                    self.karen.reload_tier_frames()
                    self.notifications.add(
                        "LEVEL UP TOKEN!",
                        self._world_to_screen(tok.rect.centerx),
                        tok.rect.top - 16,
                        NEON_YELLOW, font_size=20, duration=70,
                    )
                tok.kill()

        # Tier notification (catches first-time tier change from collect)
        if self.karen.tier != prev_tier:
            self.notifications.add(
                f"★  TIER {self.karen.tier} EVOLVED  ★",
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
