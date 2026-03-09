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

class SoundWave(pygame.sprite.Sprite):
    """
    Growing circular projectile emitted by Karen.
    Starts small and expands outward while moving horizontally.
    """

    def __init__(self, x: int, y: int, direction: int, tier: int) -> None:
        """
        Parameters
        ----------
        x, y      : spawn position (centre of Karen)
        direction : +1 = right, -1 = left
        tier      : Karen's current tier (affects colour intensity)
        """
        super().__init__()
        self.x         = float(x)
        self.y         = float(y)
        self.direction = direction
        self.radius    = float(WAVE_INIT_R)
        self.alive_flag = True

        # Tier colour mapping
        colours = {1: NEON_CYAN, 2: NEON_YELLOW, 3: NEON_PINK}
        self.colour = colours.get(tier, NEON_CYAN)

        # Pygame sprite rect (updated each frame)
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect  = pygame.Rect(int(self.x), int(self.y), 1, 1)

    # ── update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        self.x      += WAVE_SPEED * self.direction
        self.radius  = min(self.radius + WAVE_GROW_RATE, WAVE_MAX_R)

        # Keep rect in sync for collision detection
        r = int(self.radius)
        self.rect = pygame.Rect(
            int(self.x) - r, int(self.y) - r, r * 2, r * 2
        )

        # Kill if off-screen
        if self.x < -WAVE_MAX_R or self.x > SCREEN_W + WAVE_MAX_R:
            self.alive_flag = False
            self.kill()

    # ── draw ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        r    = int(self.radius)
        cx   = int(self.x)
        cy   = int(self.y)
        # Outer glow (semi-transparent)
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.colour, 50), (r * 2, r * 2), r * 2)
        surface.blit(glow, (cx - r * 2, cy - r * 2))
        # Main circle
        pygame.draw.circle(surface, self.colour, (cx, cy), r, 3)
        # Inner bright ring
        if r > 10:
            pygame.draw.circle(surface, WHITE, (cx, cy), max(r - 6, 4), 1)


# ─────────────────────────────────────────────────────────────────────────────
#  KAREN PLAYER
# ─────────────────────────────────────────────────────────────────────────────

class Karen(pygame.sprite.Sprite):
    """
    The player character.

    State machine
    ─────────────
      idle / walk  → ground movement
      jump         → rising phase
      fall         → falling phase
      attack       → fire wave (can move simultaneously)

    Tier system
    ───────────
      Tier 1 → 2 → 3 triggered by accumulated token_level_up pickups.
    """

    # Animation state names that map to sprite keys
    _STATES = ("walk", "jump", "fall", "attack")

    def __init__(self) -> None:
        super().__init__()

        # ── position / physics ───────────────────────────────────────────
        self.pos        = pygame.math.Vector2(KAREN_SPAWN_X, KAREN_SPAWN_Y)
        self.vel_y      : float = 0.0
        self.on_ground  : bool  = False
        self.facing     : int   = 1          # +1 right, -1 left

        # ── state ────────────────────────────────────────────────────────
        self.state      : str   = "walk"
        self.tier       : int   = 1
        self.health     : int   = KAREN_MAX_HEALTH
        self.alive      : bool  = True

        # ── economy ──────────────────────────────────────────────────────
        self.score           : int = 0
        self.level_up_count  : int = 0   # accumulated token_level_up pickups

        # ── animation ────────────────────────────────────────────────────
        self._anim_timer : int = 0
        self._anim_frame : int = 0       # only 1 frame per state currently

        # ── invincibility ─────────────────────────────────────────────────
        self._iframe_timer : int = 0

        # ── attack cooldown ───────────────────────────────────────────────
        self._attack_timer    : int  = 0
        self._attack_duration : int  = 30  # frames attack sprite shows

        # ── sprite image / rect ──────────────────────────────────────────
        self.image = self._get_frame()
        self.rect  = self.image.get_rect(topleft=(int(self.pos.x), int(self.pos.y)))

    # ── asset helpers ─────────────────────────────────────────────────────

    def _dir_str(self) -> str:
        return "right" if self.facing >= 0 else "left"

    def _get_frame(self) -> pygame.Surface:
        key = f"karen{self.tier}_{self.state}_{self._dir_str()}"
        return assets.get(key, assets["karen1_walk_right"])

    # ── input & movement ──────────────────────────────────────────────────

    def handle_input(self, keys: pygame.key.ScancodeWrapper,
                     waves: pygame.sprite.Group) -> None:
        """Process keyboard input, update velocity, and fire waves."""

        # Horizontal movement
        moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.pos.x  -= KAREN_SPEED
            self.facing  = -1
            moving       = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.pos.x  += KAREN_SPEED
            self.facing  = 1
            moving       = True

        # Clamp to screen edges
        self.pos.x = max(0, min(self.pos.x, SCREEN_W - self.rect.width))

        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y     = KAREN_JUMP_VEL
            self.on_ground = False

        # Attack (F key) — spawn wave if not on cooldown
        if keys[pygame.K_f] and self._attack_timer == 0:
            self._attack_timer = self._attack_duration
            cx = int(self.pos.x + self.rect.width  // 2)
            cy = int(self.pos.y + self.rect.height // 2)
            wave = SoundWave(cx, cy, self.facing, self.tier)
            waves.add(wave)

        # Determine animation state
        if self._attack_timer > 0:
            self.state = "attack"
        elif not self.on_ground:
            self.state = "jump" if self.vel_y < 0 else "fall"
        else:
            self.state = "walk" if moving else "walk"  # idle = walk frame

    # ── physics ───────────────────────────────────────────────────────────

    def apply_gravity(self) -> None:
        if not self.on_ground:
            self.vel_y = min(self.vel_y + GRAVITY, TERM_VEL)
        self.pos.y += self.vel_y

    def land_on(self, surface_y: int) -> None:
        """Snap Karen to a surface and reset vertical velocity."""
        self.pos.y    = surface_y - self.rect.height
        self.vel_y    = 0.0
        self.on_ground = True

    def resolve_floor(self) -> None:
        """Hard floor boundary."""
        floor_surface = FLOOR_Y - self.rect.height
        if self.pos.y >= floor_surface:
            self.land_on(FLOOR_Y)

    # ── collision helpers ─────────────────────────────────────────────────

    def platform_collide(self, platforms: list) -> None:
        """Check and resolve downward collision with platforms."""
        if self.vel_y < 0:
            return   # rising — skip platform snap

        prev_y = self.pos.y - self.vel_y
        for plat in platforms:
            # Only land if Karen was above the platform last frame
            above_last_frame = (prev_y + self.rect.height) <= (plat.rect.top + 4)
            feet_y = self.pos.y + self.rect.height

            if above_last_frame and feet_y >= plat.rect.top:
                if (self.pos.x + self.rect.width > plat.rect.left and
                        self.pos.x < plat.rect.right):
                    self.land_on(plat.rect.top)
                    break

    # ── damage & tier ─────────────────────────────────────────────────────

    def take_damage(self, amount: int = 1) -> None:
        if self._iframe_timer > 0:
            return
        self.health       -= amount
        self._iframe_timer = KAREN_IFRAMES
        if self.health <= 0:
            self.alive = False

    def collect_bonus(self) -> None:
        self.score += 100

    def collect_level_up(self) -> None:
        self.level_up_count += 1
        self.score          += 500
        # Tier upgrade
        if self.tier == 1 and self.level_up_count >= TIER_THRESHOLDS[2]:
            self.tier = 2
        elif self.tier == 2 and self.level_up_count >= TIER_THRESHOLDS[3]:
            self.tier = 3

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        # Timers
        if self._iframe_timer  > 0: self._iframe_timer  -= 1
        if self._attack_timer  > 0: self._attack_timer  -= 1

        # Sync rect
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # Refresh image
        self.image = self._get_frame()

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        # Blink every 6 frames when invincible
        if self._iframe_timer > 0 and (self._iframe_timer // 6) % 2 == 0:
            return
        surface.blit(self.image, self.rect.topleft)

    # ── HUD helpers ───────────────────────────────────────────────────────

    def draw_hud(self, surface: pygame.Surface) -> None:
        """Draw health hearts, tier badge and score."""
        self._draw_hearts(surface)
        self._draw_tier(surface)
        self._draw_score(surface)

    def _draw_hearts(self, surface: pygame.Surface) -> None:
        hx, hy = 20, 14
        for i in range(KAREN_MAX_HEALTH):
            colour = (220, 30, 60) if i < self.health else (60, 20, 30)
            cx = hx + i * 34
            # Heart shape via two circles + polygon
            pygame.draw.circle(surface, colour, (cx + 7,  hy + 7), 7)
            pygame.draw.circle(surface, colour, (cx + 20, hy + 7), 7)
            points = [(cx, hy + 10), (cx + 13, hy + 26), (cx + 27, hy + 10)]
            pygame.draw.polygon(surface, colour, points)
            # White sheen
            pygame.draw.circle(surface, (255, 180, 200), (cx + 8, hy + 5), 2)

    def _draw_tier(self, surface: pygame.Surface) -> None:
        colours = {1: NEON_CYAN, 2: NEON_YELLOW, 3: NEON_PINK}
        col  = colours[self.tier]
        font = get_mono(20, bold=True)
        txt  = font.render(f"TIER {self.tier}", True, col)
        surface.blit(txt, (20, 54))

    def _draw_score(self, surface: pygame.Surface) -> None:
        font = get_mono(22, bold=True)
        txt  = font.render(f"CREDITS  {self.score:>6}", True, NEON_CYAN)
        surface.blit(txt, (20, 80))
