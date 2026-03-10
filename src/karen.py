"""
karen.py — Player character class.

Karen has three Tiers (cosmetic + stat upgrades), 5 hearts of health,
full directional animations, a jump with gravity, and can fire a
growing Sound-Wave projectile.
"""

from __future__ import annotations
import pygame
from src.fonts import get_mono
from src.settings import (
    SCREEN_W, SCREEN_H, FLOOR_Y,
    WORLD_W,
    KAREN_SPEED, KAREN_JUMP_VEL, KAREN_MAX_HEALTH,
    KAREN_IFRAMES, KAREN_ANIM_SPEED,
    KAREN_HEIGHT, KAREN_SPAWN_X, KAREN_SPAWN_Y,
    GRAVITY, TERM_VEL,
    WAVE_SPEED, WAVE_INIT_R, WAVE_MAX_R, WAVE_GROW_RATE,
    TIER_THRESHOLDS,
    NEON_CYAN, NEON_PINK, NEON_YELLOW, WHITE,
)
from src.asset_loader import assets


# ─────────────────────────────────────────────────────────────────────────────
#  SOUND WAVE PROJECTILE
# ─────────────────────────────────────────────────────────────────────────────

_WAVE_TIER_PARAMS: dict[int, tuple[float, float, float, float]] = {
    1: (WAVE_INIT_R,        WAVE_MAX_R,        WAVE_GROW_RATE,        WAVE_SPEED       ),
    2: (WAVE_INIT_R * 1.5,  WAVE_MAX_R * 1.5,  WAVE_GROW_RATE * 1.5,  WAVE_SPEED * 1.1),
    3: (WAVE_INIT_R * 2.2,  WAVE_MAX_R * 2.2,  WAVE_GROW_RATE * 2.2,  WAVE_SPEED * 1.3),
}


class SoundWave(pygame.sprite.Sprite):
    """
    Growing circular projectile emitted by Karen.
    """

    def __init__(self, x: int, y: int, direction: int, tier: int) -> None:
        super().__init__()

        init_r, max_r, grow, speed = _WAVE_TIER_PARAMS.get(
            tier, _WAVE_TIER_PARAMS[1]
        )
        self._max_r   = max_r
        self._grow    = grow
        self._speed   = speed
        self._tier    = tier 
        self._linger  = 0

        self.x         = float(x)
        self.y         = float(y)
        self.direction = direction
        self.radius    = float(init_r)
        self.alive_flag = True

        colours = {1: NEON_CYAN, 2: NEON_YELLOW, 3: NEON_PINK}
        self.colour = colours.get(tier, NEON_CYAN)

        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect  = pygame.Rect(int(self.x), int(self.y), 1, 1)

    def update(self) -> None:
        # AUDIT FIX: Removed the non-existent _attack_timer check that caused crashes
        self.radius = min(self.radius + self._grow, self._max_r)

        if self._tier < 3:
            if self.radius < self._max_r:
                self.x += self._speed * self.direction
        else:
            self.x += self._speed * self.direction

        r = int(self.radius)
        self.rect = pygame.Rect(
            int(self.x) - r, int(self.y) - r, r * 2, r * 2
        )

        if self._tier < 3:
            if self.radius >= self._max_r:
                self._linger -= 1
                if self._linger <= 0:
                    self.alive_flag = False
                    self.kill()
        else:
            if self.x < -(self._max_r + 100) or self.x > WORLD_W + self._max_r:
                self.alive_flag = False
                self.kill()

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        r    = int(self.radius)
        cx   = int(self.x) - camera_x
        cy   = int(self.y)

        if cx + r < 0 or cx - r > SCREEN_W:
            return

        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.colour, 50), (r * 2, r * 2), r * 2)
        surface.blit(glow, (cx - r * 2, cy - r * 2))
        pygame.draw.circle(surface, self.colour, (cx, cy), r, 3)
        if r > 10:
            pygame.draw.circle(surface, WHITE, (cx, cy), max(r - 6, 4), 1)


# ─────────────────────────────────────────────────────────────────────────────
#  KAREN PLAYER
# ─────────────────────────────────────────────────────────────────────────────

class Karen(pygame.sprite.Sprite):
    """
    The player character.
    """

    _STATES = ("walk", "jump", "fall", "attack")

    def __init__(self) -> None:
        super().__init__()

        self.pos        = pygame.math.Vector2(KAREN_SPAWN_X, KAREN_SPAWN_Y)
        self.vel_y      : float = 0.0
        self.on_ground  : bool  = False
        self.facing     : int   = 1 
        self.jumps_left : int   = 2
        self._jump_held : bool  = False

        self.state      : str   = "walk"
        self.tier       : int   = 1
        self.health     : int   = KAREN_MAX_HEALTH
        self.alive      : bool  = True

        self.score            : int = 0
        self.level_up_count   : int = 0

        self._anim_timer : int = 0
        self._anim_frame : int = 0
        self._iframe_timer : int = 0

        self._attack_timer    : int  = 0
        self._attack_duration : int  = 30

        self.image = self._get_frame()
        self.rect  = self.image.get_rect(topleft=(int(self.pos.x), int(self.pos.y)))

    def _dir_str(self) -> str:
        return "right" if self.facing >= 0 else "left"

    def can_attack(self) -> bool:
        return self._attack_timer <= 0

    def _get_frame(self) -> pygame.Surface:
        key = f"karen{self.tier}_{self.state}_{self._dir_str()}"
        return assets.get(key, assets["karen1_walk_right"])

    def reload_tier_frames(self) -> None:
        self.image = self._get_frame()
        new_rect = self.image.get_rect(topleft=self.rect.topleft)
        self.rect = new_rect

    def handle_input(self, keys: pygame.key.ScancodeWrapper,
                     waves: pygame.sprite.Group) -> None:
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.pos.x  -= KAREN_SPEED
            self.facing  = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.pos.x  += KAREN_SPEED
            self.facing  = 1

        self.pos.x = max(0, self.pos.x)

        jump_key = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        if jump_key and not self._jump_held:
            if self.jumps_left > 0:
                self.vel_y = KAREN_JUMP_VEL
                self.on_ground = False
                self.jumps_left -= 1
        self._jump_held = jump_key

        if keys[pygame.K_f] and self.can_attack():
            self._attack_timer = self._attack_duration
            cx = int(self.pos.x + self.rect.width  // 2)
            cy = int(self.pos.y + self.rect.height // 2)
            wave = SoundWave(cx, cy, self.facing, self.tier)
            waves.add(wave)

        if self._attack_timer > 0:
            self.state = "attack"
        elif not self.on_ground:
            self.state = "jump" if self.vel_y < 0 else "fall"
        else:
            self.state = "walk"

    def apply_gravity(self) -> None:
        self.on_ground = False 
        self.vel_y = min(self.vel_y + GRAVITY, TERM_VEL)
        self.pos.y += self.vel_y

    def land_on(self, surface_y: int) -> None:
        self.pos.y     = surface_y - self.rect.height
        self.vel_y     = 0.0
        self.on_ground = True 
        self.jumps_left = 2
        
    def resolve_floor(self) -> None:
        floor_surface = FLOOR_Y - self.rect.height
        if self.pos.y >= floor_surface:
            self.land_on(FLOOR_Y)

    def platform_collide(self, platforms: list) -> None:
        if self.vel_y < 0:
            return 

        prev_y = self.pos.y - self.vel_y
        for plat in platforms:
            above_last_frame = (prev_y + self.rect.height) <= (plat.rect.top + 4)
            feet_y           = self.pos.y + self.rect.height

            if above_last_frame and feet_y >= plat.rect.top:
                if (self.pos.x + self.rect.width > plat.rect.left and
                        self.pos.x < plat.rect.right):
                    self.land_on(plat.rect.top)
                    break

    def take_damage(self, amount: int = 1) -> None:
        if self._iframe_timer > 0:
            return
        self.health       -= amount
        self._iframe_timer = KAREN_IFRAMES
        if self.health <= 0:
            self.alive = False
            return
        if self.tier > 1:
            self.demote_tier()

    def demote_tier(self) -> None:
        self.tier           = 1
        self.level_up_count = 0
        self.reload_tier_frames()

    def collect_bonus(self) -> None:
        self.score += 100

    def collect_level_up(self) -> None:
        self.level_up_count += 1
        self.score          += 500
        if self.tier == 1 and self.level_up_count >= TIER_THRESHOLDS[2]:
            self.tier = 2
        elif self.tier == 2 and self.level_up_count >= TIER_THRESHOLDS[3]:
            self.tier = 3

    def update(self) -> None:
        if self._iframe_timer > 0: self._iframe_timer -= 1
        if self._attack_timer > 0: self._attack_timer -= 1

        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)
        self.image = self._get_frame()

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        if self._iframe_timer > 0 and (self._iframe_timer // 6) % 2 == 0:
            return
        screen_x = int(self.pos.x) - camera_x
        visual_sink = int(self.rect.height * 0.12) 
        surface.blit(self.image, (screen_x, int(self.pos.y) + visual_sink))