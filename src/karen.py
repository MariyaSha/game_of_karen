"""
karen.py — Player character class.

Karen has three Tiers (cosmetic + stat upgrades), 5 hearts of health,
full directional animations, a jump with gravity, and can fire a
growing Sound-Wave projectile.

Fixes applied
─────────────
  FIX 2 — Air-walking: apply_gravity() resets on_ground = False every frame;
           platform_collide() / resolve_floor() are the *only* paths that set
           it back to True, correctly detecting edge walk-off.
  FIX 3 — Tier scaling: SoundWave uses the `tier` parameter to scale its
           initial radius, max radius, growth rate, and travel speed.
  FIX 4 — Tier reload: reload_tier_frames() forces _get_frame() to pull the
           correct tier sprite from the asset cache after a tier change.
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

# ── FIX 4: per-tier scaling tables (base = Tier 1, 50% smaller than original)
# WAVE_INIT_R=6, WAVE_MAX_R=45, WAVE_GROW_RATE=1.25 in settings (already -50%)
# Tier 1 uses those base values exactly.
# Tier 2 = 1.5× base  → init 9, max 67.5, grow 1.875
# Tier 3 = 2.2× base  → init 13.2, max 99, grow 2.75  (Full Karen Mode)
_WAVE_TIER_PARAMS: dict[int, tuple[float, float, float, float]] = {
    1: (WAVE_INIT_R,        WAVE_MAX_R,        WAVE_GROW_RATE,        WAVE_SPEED       ),
    2: (WAVE_INIT_R * 1.5,  WAVE_MAX_R * 1.5,  WAVE_GROW_RATE * 1.5,  WAVE_SPEED * 1.1),
    3: (WAVE_INIT_R * 2.2,  WAVE_MAX_R * 2.2,  WAVE_GROW_RATE * 2.2,  WAVE_SPEED * 1.3),
}


class SoundWave(pygame.sprite.Sprite):
    """
    Growing circular projectile emitted by Karen.
    Tier 1 → smallest and slowest.
    Tier 2 → medium (base values from settings).
    Tier 3 → largest and fastest (Full Karen Mode).
    """

    def __init__(self, x: int, y: int, direction: int, tier: int) -> None:
        """
        Parameters
        ----------
        x, y      : spawn position (centre of Karen) in WORLD space
        direction : +1 = right, -1 = left
        tier      : Karen's current tier — controls size and speed scaling
        """
        super().__init__()

        # ── FIX 3: pull tier-specific parameters ─────────────────────────
        init_r, max_r, grow, speed = _WAVE_TIER_PARAMS.get(
            tier, _WAVE_TIER_PARAMS[1]
        )
        self._max_r   = max_r
        self._grow    = grow
        self._speed   = speed
        self._tier    = tier          # store tier for update logic
        # Tier 1/2: wave vanishes immediately when max radius is reached (no linger)
        self._linger  = 0

        self.x         = float(x)
        self.y         = float(y)
        self.direction = direction
        self.radius    = float(init_r)
        self.alive_flag = True

        # Tier colour mapping
        colours = {1: NEON_CYAN, 2: NEON_YELLOW, 3: NEON_PINK}
        self.colour = colours.get(tier, NEON_CYAN)

        # Pygame sprite rect (updated each frame, world-space)
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect  = pygame.Rect(int(self.x), int(self.y), 1, 1)

    # ── update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        self.radius = min(self.radius + self._grow, self._max_r)

        # Tier 1 and 2: stop translating once radius reaches maximum.
        # Tier 3 keeps moving across the whole screen (full power).
        if self._tier < 3:
            if self.radius >= self._max_r:
                # Wave has fully expanded — stop moving, keep hitbox in place
                pass
            else:
                self.x += self._speed * self.direction
        else:
            # Tier 3: always travel forward
            self.x += self._speed * self.direction

        # Keep rect in sync (world-space) for collision detection
        r = int(self.radius)
        self.rect = pygame.Rect(
            int(self.x) - r, int(self.y) - r, r * 2, r * 2
        )

        # Kill if off world bounds (tier 3 travels; tier 1/2 die when max reached
        # and then fade — we kill them after a short linger for visual effect)
        if self._tier < 3:
            # For tier 1/2: kill once radius is maxed AND we've lingered a bit
            if self.radius >= self._max_r:
                self._linger -= 1
                if self._linger <= 0:
                    self.alive_flag = False
                    self.kill()
        else:
            if self.x < -(self._max_r + 100) or self.x > WORLD_W + self._max_r:
                self.alive_flag = False
                self.kill()

    # ── draw ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        r    = int(self.radius)
        # Convert world-space centre to screen-space
        cx   = int(self.x) - camera_x
        cy   = int(self.y)

        # Skip if completely off screen
        if cx + r < 0 or cx - r > SCREEN_W:
            return

        # Outer glow (semi-transparent)
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.colour, 50), (r * 2, r * 2), r * 2)
        surface.blit(glow, (cx - r * 2, cy - r * 2))
        # Main ring
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
      walk  → ground movement (also covers idle frame)
      jump  → rising phase (vel_y < 0)
      fall  → falling phase (vel_y ≥ 0, not on ground)
      attack → fire wave (can move simultaneously)

    Tier system
    ───────────
      Tier 1 → 2 → 3 triggered by accumulated token_level_up pickups.
      Tier change forces reload_tier_frames() to swap sprites immediately.
    """

    _STATES = ("walk", "jump", "fall", "attack")

    def __init__(self) -> None:
        super().__init__()

        # ── position / physics (WORLD space) ────────────────────────────
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
        self.level_up_count  : int = 0

        # ── animation ────────────────────────────────────────────────────
        self._anim_timer : int = 0
        self._anim_frame : int = 0

        # ── invincibility ─────────────────────────────────────────────────
        self._iframe_timer : int = 0

        # ── attack cooldown ───────────────────────────────────────────────
        self._attack_timer    : int  = 0
        self._attack_duration : int  = 30

        # ── sprite image / rect (world-space rect) ───────────────────────
        self.image = self._get_frame()
        self.rect  = self.image.get_rect(topleft=(int(self.pos.x), int(self.pos.y)))

    # ── asset helpers ─────────────────────────────────────────────────────

    def _dir_str(self) -> str:
        return "right" if self.facing >= 0 else "left"

    def _get_frame(self) -> pygame.Surface:
        key = f"karen{self.tier}_{self.state}_{self._dir_str()}"
        return assets.get(key, assets["karen1_walk_right"])

    # ── FIX 4: reload tier sprites after evolution ────────────────────────

    def reload_tier_frames(self) -> None:
        """
        Force the sprite image to refresh from the asset cache for the
        new tier.  Called immediately after self.tier is incremented so
        the correct tier sprite shows on the very next frame.
        """
        self.image = self._get_frame()
        # Preserve rect position but update size in case the sprite changed
        new_rect = self.image.get_rect(topleft=self.rect.topleft)
        self.rect = new_rect

    # ── input & movement ──────────────────────────────────────────────────

    def handle_input(self, keys: pygame.key.ScancodeWrapper,
                     waves: pygame.sprite.Group) -> None:
        """Process keyboard input, update velocity, and fire waves."""

        moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.pos.x  -= KAREN_SPEED
            self.facing  = -1
            moving       = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.pos.x  += KAREN_SPEED
            self.facing  = 1
            moving       = True

        # Clamp to world left edge (right is unbounded — the camera scrolls)
        self.pos.x = max(0, self.pos.x)

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
            self.state = "walk"

    # ── physics ───────────────────────────────────────────────────────────

    def apply_gravity(self) -> None:
        """
        Apply gravity every frame.

        FIX 2 — Air-walking:
          We reset on_ground = False here unconditionally at the START of
          every physics tick.  The only code paths that can set it back to
          True are platform_collide() and resolve_floor(), which run *after*
          this method.  This means that if Karen walks off a platform edge,
          on_ground is False before either landing-check runs, so she will
          correctly start falling.
        """
        self.on_ground = False          # ← FIX 2: reset before landing checks
        self.vel_y = min(self.vel_y + GRAVITY, TERM_VEL)
        self.pos.y += self.vel_y

    def land_on(self, surface_y: int) -> None:
        """Snap Karen to a surface and reset vertical velocity."""
        self.pos.y     = surface_y - self.rect.height
        self.vel_y     = 0.0
        self.on_ground = True           # set back to True here — never elsewhere

    def resolve_floor(self) -> None:
        """Hard floor boundary — sets on_ground if Karen hits the floor."""
        floor_surface = FLOOR_Y - self.rect.height
        if self.pos.y >= floor_surface:
            self.land_on(FLOOR_Y)

    # ── collision helpers ─────────────────────────────────────────────────

    def platform_collide(self, platforms: list) -> None:
        """
        Check and resolve downward collision with platforms.

        We use the position from BEFORE this frame's gravity displacement
        (prev_y = pos.y - vel_y) to determine whether Karen was above the
        platform in the last frame, preventing tunnelling.
        """
        if self.vel_y < 0:
            return   # rising — skip platform snap

        # pos.y already includes this frame's displacement
        prev_y = self.pos.y - self.vel_y
        for plat in platforms:
            above_last_frame = (prev_y + self.rect.height) <= (plat.rect.top + 4)
            feet_y           = self.pos.y + self.rect.height

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
            return
        # ── Tier regression: any hit while tier > 1 demotes back to tier 1 ──
        if self.tier > 1:
            self.demote_tier()

    def demote_tier(self) -> None:
        """
        Immediately drop Karen back to Tier 1 and reset her level-up counter.
        Called automatically by take_damage() when tier > 1.
        The caller (GameManager) should fire the regression notification.
        """
        self.tier           = 1
        self.level_up_count = 0
        self.reload_tier_frames()

    def collect_bonus(self) -> None:
        self.score += 100

    def collect_level_up(self) -> None:
        self.level_up_count += 1
        self.score          += 500
        # Tier upgrade thresholds
        if self.tier == 1 and self.level_up_count >= TIER_THRESHOLDS[2]:
            self.tier = 2
        elif self.tier == 2 and self.level_up_count >= TIER_THRESHOLDS[3]:
            self.tier = 3
        # reload_tier_frames() is called externally by GameManager after this

    # ── update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        # Timers
        if self._iframe_timer > 0: self._iframe_timer -= 1
        if self._attack_timer > 0: self._attack_timer -= 1

        # Sync world-space rect
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # Refresh animation frame
        self.image = self._get_frame()

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera_x: int = 0) -> None:
        """Draw Karen at world pos translated by camera."""
        # Blink every 6 frames when invincible
        if self._iframe_timer > 0 and (self._iframe_timer // 6) % 2 == 0:
            return
        screen_x = int(self.pos.x) - camera_x
        surface.blit(self.image, (screen_x, int(self.pos.y)))

    # ── HUD helpers ───────────────────────────────────────────────────────

    def draw_hud(self, surface: pygame.Surface) -> None:
        self._draw_hearts(surface)
        self._draw_tier(surface)
        self._draw_score(surface)

    def _draw_hearts(self, surface: pygame.Surface) -> None:
        hx, hy = 20, 14
        for i in range(KAREN_MAX_HEALTH):
            colour = (220, 30, 60) if i < self.health else (60, 20, 30)
            cx = hx + i * 34
            pygame.draw.circle(surface, colour, (cx + 7,  hy + 7), 7)
            pygame.draw.circle(surface, colour, (cx + 20, hy + 7), 7)
            points = [(cx, hy + 10), (cx + 13, hy + 26), (cx + 27, hy + 10)]
            pygame.draw.polygon(surface, colour, points)
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
