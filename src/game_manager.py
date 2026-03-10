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
from src.karen          import Karen, SoundWave
from src.enemies        import (FlyerEnemy, SkaterEnemy, SlackerEnemy,
                                spawn_slacker)
from src.boss           import BossManager
from src.platform       import Platform, create_platforms
from src.tokens         import Token, make_token
from src.spawner        import EnemySpawner
from src.hud            import HUD, ParticleSystem, NotificationSystem
from src.audio          import SoundManager

class GameState:
    PLAYING   = "playing"
    GAME_OVER = "game_over"
    VICTORY   = "victory"
    BOSS_INTRO= "boss_intro"

class GameManager:
    _CAM_LAG  = 0.08
    _CAM_FOCUS_X = SCREEN_W // 3
    _CAM_MAX  = float(BOSS_TRIGGER_X)

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen  = screen
        self.clock   = pygame.time.Clock()
        self._state  = GameState.PLAYING
        
        # ── AUDIO INITIALIZATION ──────────────────────────────────────────
        self.audio = SoundManager()
        self.audio.play_theme() # Starts "theme_music_infected_vibes"

        self.camera_x : float = 0.0
        self._boss_frame_timer: int = BOSS_SPAWN_DELAY_FRAMES
        self._karen_reached_arena: bool = False
        self._approaching_warned_far  : bool = False
        self._approaching_warned_near : bool = False

        self.hud          = HUD()
        self.particles    = ParticleSystem()
        self.notifications= NotificationSystem()

        self.waves    = pygame.sprite.Group()
        self.enemies  = pygame.sprite.Group()
        self.tokens   = pygame.sprite.Group()

        self.platforms : list[Platform] = create_platforms()
        self.karen     = Karen()
        self.boss      : BossManager | None = None
        self._boss_active  = False
        self._boss_spawned = False

        self._tier_flash  : int = 0
        self._tier_flash_val: int = 0
        self.spawner = EnemySpawner(self.enemies, self.tokens)
        self._init_platform_slackers()
        self._boss_countdown_shown: bool = False

    def _init_platform_slackers(self) -> None:
        for i, plat in enumerate(self.platforms):
            if i == 0 or i % 2 != 1:
                continue 
            if not plat.slacker_spawned:
                slacker = spawn_slacker(plat)
                self.enemies.add(slacker)
                plat.slacker_spawned = True

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS)
            running = self._handle_events()
            self._update()
            self._draw()

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
        
        # ── RESTART AUDIO ───────────────────────────────────────────────
        self.audio.stop_theme()
        self.audio.play_theme()

    def _update_camera(self) -> None:
        target_cam = self.karen.pos.x - self._CAM_FOCUS_X
        self.camera_x += (target_cam - self.camera_x) * (1.0 - self._CAM_LAG)
        self.camera_x = max(0.0, min(self.camera_x, WORLD_W - SCREEN_W))

    def _world_to_screen(self, world_x: float) -> int:
        return int(world_x - self.camera_x)

    def _update(self) -> None:
        if self._state == GameState.PLAYING:
            self._update_playing()

    def _update_playing(self) -> None:
        keys = pygame.key.get_pressed()

        # ── JUMP SFX ─────────────────────────────────────────────────────
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.karen.on_ground:
            # Note: Karen class handles 'jumps_left', so this only fires on ground
            self.audio.play_sfx("karen_jump")

        # ── ATTACK SFX ───────────────────────────────────────────────────
        if keys[pygame.K_f] and self.karen.can_attack():
            self.audio.play_sfx("karen_attack_soundwave")

        self.karen.handle_input(keys, self.waves)
        self._clamp_karen_to_world()
        self.karen.apply_gravity()
        self.karen.resolve_floor()
        self.karen.platform_collide(self.platforms)
        self.karen.update()

        if self._tier_flash > 0:
            self._tier_flash -= 1

        self._update_camera()
        self.waves.update()
        self.spawner.update(self.camera_x)

        for enemy in list(self.enemies):
            enemy.update()

        for tok in list(self.tokens):
            tok.update(self.karen.rect)

        # ── BOSS LOGIC ───────────────────────────────────────────────────
        if not self._boss_spawned:
            karen_x = self.karen.pos.x
            if not self._approaching_warned_far and karen_x >= BOSS_TRIGGER_X - SCREEN_W * 2:
                self._approaching_warned_far = True
                self.notifications.add("\u26A0 APPROACHING MANAGER \u26A0", SCREEN_W // 2, SCREEN_H // 3, NEON_YELLOW, font_size=26, duration=150)
            
            if not self._approaching_warned_near and karen_x >= BOSS_TRIGGER_X - SCREEN_W // 2:
                self._approaching_warned_near = True
                self.notifications.add("\u26a0 THE MANAGER IS WAITING \u26a0", SCREEN_W // 2, SCREEN_H // 3, NEON_PINK, font_size=30, duration=180)

            if not self._karen_reached_arena and self.karen.pos.x >= BOSS_TRIGGER_X - 600:
                self._karen_reached_arena = True

            if self._karen_reached_arena:
                self._boss_frame_timer -= 1
                if self._boss_frame_timer == 180 and not self._boss_countdown_shown:
                    self._boss_countdown_shown = True
                    # ── STOP THEME FOR BOSS TENSION ─────────────────────
                    self.audio.stop_theme() 
                    self.notifications.add("\u26a0 THE MANAGER ARRIVED \u26a0", SCREEN_W // 2, SCREEN_H // 3, NEON_YELLOW, font_size=34, duration=180)
                if self._boss_frame_timer <= 0:
                    self._spawn_boss()

        if self._boss_active and self.boss:
            self.boss.update(self.karen.rect)

        self._resolve_wave_enemy_collisions()
        self._resolve_wave_boss_collisions()
        self._resolve_enemy_karen_collisions()
        self._resolve_fireball_karen_collisions()
        self._resolve_token_karen_collisions()

        self.particles.update()
        self.notifications.update()

        # ── END STATES ───────────────────────────────────────────────────
        if not self.karen.alive:
            self._state = GameState.GAME_OVER
            self.audio.stop_theme()
            self.audio.play_sfx("karen_defeat_gameover")

        if self._boss_active and self.boss and not self.boss.alive:
            self._state = GameState.VICTORY
            self.audio.stop_theme()
            self.audio.play_sfx("karen_victory_success")

    def _spawn_boss(self) -> None:
        # ── BOSS MUSIC TRIGGER ──────────────────────────────────────────
        # Theme is already stopped in the countdown above.
        self.audio.play_boss_music() 

        self.boss          = BossManager()
        self._boss_active  = True
        self._boss_spawned = True
        for enemy in list(self.enemies):
            if not isinstance(enemy, SlackerEnemy):
                enemy.kill()

        arena_entrance = float(BOSS_TRIGGER_X + 80)
        if self.karen.pos.x < arena_entrance:
            self.karen.pos.x = arena_entrance

    def _clamp_karen_to_world(self) -> None:
        if not self._boss_spawned:
            self.karen.pos.x = max(0.0, self.karen.pos.x)
        else:
            karen_w = self.karen.rect.width
            self.karen.pos.x = max(0.0, min(self.karen.pos.x, float(WORLD_W - karen_w)))

    def _resolve_wave_enemy_collisions(self) -> None:
        """
        Restores the token drop logic: 
        Enemies now physically drop Tier-up/Bonus tokens upon death.
        """
        for wave in list(self.waves):
            for enemy in list(self.enemies):
                if wave.rect.colliderect(enemy.rect):
                    # 1. Apply Damage
                    enemy.take_hit(1)
                    self.particles.emit_hit(enemy.rect.centerx, enemy.rect.centery)
                    self.audio.play_sfx("enemy_hit") 
                    
                    # 2. Death & Loot Audit
                    if not enemy.alive:
                        # Get the specific drop type from the enemy class
                        drop = enemy.get_drop()
                        
                        # Physically spawn the token into the world
                        EnemySpawner.drop_token(
                            self.tokens, 
                            drop, 
                            enemy.rect.centerx, 
                            enemy.rect.top
                        )
                        
                        # Economy: Immediate score feedback
                        score_gain = 50 if drop == "bonus" else 150
                        self.karen.score += score_gain
                        
                        # Visual feedback for the score gain
                        self.notifications.add(
                            f"+{score_gain}",
                            self._world_to_screen(enemy.rect.centerx),
                            enemy.rect.top - 20,
                            NEON_CYAN, font_size=18, duration=50
                        )
                    
                    # 3. Clean up the projectile
                    wave.kill()
                    break

    def _resolve_wave_boss_collisions(self) -> None:
        if not self._boss_active or not self.boss: return
        for wave in list(self.waves):
            if (self.boss.is_vulnerable and wave.rect.colliderect(self.boss.rect)):
                self.boss.take_hit(1)
                # THIS is where the boss-specific feedback belongs
                self.particles.emit_boss_hit(self.boss.rect.centerx, self.boss.rect.centery)
                self.audio.play_sfx("boss_hit") 
                wave.kill()

    def _resolve_enemy_karen_collisions(self) -> None:
        if self.karen._iframe_timer > 0: return
        karen_hurtbox = self.karen.rect.inflate(-self.karen.rect.width * 0.7, -self.karen.rect.height * 0.7)
        for enemy in self.enemies:
            if enemy.rect.colliderect(karen_hurtbox):
                prev_tier = self.karen.tier
                self.audio.play_sfx("karen_got_hit_karen_is_damaged")
                self.karen.take_damage(1)
                self._check_tier_regression(prev_tier)
                break

    def _resolve_fireball_karen_collisions(self) -> None:
        if not self._boss_active or not self.boss: return
        if self.karen._iframe_timer > 0: return
        karen_hurtbox = self.karen.rect.inflate(-self.karen.rect.width * 0.25, -self.karen.rect.height * 0.25)
        for fb in list(self.boss.fireballs):
            if fb.rect.colliderect(karen_hurtbox):
                prev_tier = self.karen.tier
                self.karen.take_damage(1)
                self._check_tier_regression(prev_tier)
                fb.kill()
                break

    def _check_tier_regression(self, prev_tier: int) -> None:
        if prev_tier > 1 and self.karen.tier == 1:
            self._tier_flash     = 120
            self._tier_flash_val = 1

    def _resolve_token_karen_collisions(self) -> None:
        prev_tier = self.karen.tier
        k_rect    = self.karen.rect

        for tok in list(self.tokens):
            hit = tok.rect.colliderect(k_rect)
            if not hit:
                dx = abs(tok._x + tok.image.get_width()  // 2 - k_rect.centerx)
                dy = abs(tok._y + tok.image.get_height() // 2 - k_rect.centery)
                hit = (dx < 80 and dy < 70)

            if hit:
                if tok.token_type == "level_up" and self.karen.tier >= 3:
                    continue 

                self.particles.emit_collect(self._world_to_screen(int(tok._x)), int(tok._y), tok.token_type)
                
                if tok.token_type == "bonus":
                    self.audio.play_sfx("token_bonus_store_credit")
                    self.karen.collect_bonus()
                    tok.kill()
                elif tok.token_type == "level_up":
                    # ── TOKEN SPECIFIC SFX ───────────────────────────────
                    self.audio.play_sfx("token_levelup") 
                    old_tier = self.karen.tier
                    self.karen.collect_level_up()
                    self.karen.reload_tier_frames()
                    if self.karen.tier != old_tier:
                        self._tier_flash     = 120
                        self._tier_flash_val = self.karen.tier
                    tok.kill()

        if self.karen.tier != prev_tier:
            self.notifications.add(f"\u2605 TIER {self.karen.tier} EVOLVED \u2605", SCREEN_W // 2, SCREEN_H // 2 - 60, NEON_PINK, font_size=36, duration=150)

    def _draw(self) -> None:
        cam   = int(self.camera_x)
        bg    = assets["background"]
        bg_w  = bg.get_width()
        offset = -(cam % bg_w)
        x = offset
        while x < SCREEN_W:
            self.screen.blit(bg, (x, 0))
            x += bg_w

        for plat in self.platforms: plat.draw(self.screen, cam)
        for tok in self.tokens: tok.draw(self.screen, cam)
        for enemy in self.enemies: enemy.draw(self.screen, cam)
        if self._boss_active and self.boss: self.boss.draw(self.screen, cam)
        for wave in self.waves: wave.draw(self.screen, cam)
        self.karen.draw(self.screen, cam)
        self.particles.draw(self.screen)
        self.notifications.draw(self.screen)

        if self._tier_flash > 0:
            self.hud.draw_tier_up(self.screen, self._tier_flash_val)

        boss_hp  = self.boss.health if self.boss else 0
        from src.settings import BOSS_HEALTH
        self.hud.draw(self.screen, health=self.karen.health, tier=self.karen.tier, score=self.karen.score, level_up_count=self.karen.level_up_count, boss_health=boss_hp, boss_max=BOSS_HEALTH, boss_active=self._boss_active, boss_phase=self.boss.phase if self.boss else "idle")

        if self._state == GameState.GAME_OVER: self.hud.draw_game_over(self.screen)
        elif self._state == GameState.VICTORY: self.hud.draw_victory(self.screen)
        pygame.display.flip()