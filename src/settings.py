"""
settings.py — Global constants and configuration for Game of Karen.
All tunable values live here so the rest of the codebase stays clean.
"""

# ─────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────
SCREEN_W        = 1376
SCREEN_H        = 768
FPS             = 60
TITLE           = "Game of Karen"

# ─────────────────────────────────────────────
#  PHYSICS
# ─────────────────────────────────────────────
GRAVITY         = 0.55          # pixels per frame²
TERM_VEL        = 18            # terminal fall velocity (px/frame)
FLOOR_Y         = 645           # y-coordinate of the visual floor (pixels)

# ─────────────────────────────────────────────
#  WORLD / LEVEL LAYOUT
# ─────────────────────────────────────────────
# The game world is wider than the screen. Karen scrolls rightward until she
# reaches the boss arena at WORLD_W - BOSS_ARENA_W.
#
#  ┌──────────────────────────────────────────────────────┐  ← WORLD_W
#  │  scrolling section (platforms + enemies)             │
#  │                               │  boss arena          │
#  └──────────────────────────────────────────────────────┘
#  0                        BOSS_TRIGGER_X         WORLD_W
#
# • WORLD_W          — total world width in pixels
# • BOSS_TRIGGER_X   — world-X at which the boss encounter begins
#   (camera locks here so Karen cannot scroll past the arena)
# • BOSS_ARENA_W     — width of the boss fight area (≈ 1 screen)

WORLD_W         = SCREEN_W * 6   # 8256 px total world
BOSS_ARENA_W    = SCREEN_W        # boss fight occupies one screen width
BOSS_TRIGGER_X  = WORLD_W - BOSS_ARENA_W   # camera locks at this world-X

# Time (in frames) the boss waits to appear AFTER Karen reaches the boss arena
BOSS_SPAWN_DELAY_FRAMES = 60 * 2   # 2 seconds after Karen enters the arena

# ─────────────────────────────────────────────
#  KAREN PLAYER
# ─────────────────────────────────────────────
KAREN_SPEED         = 5         # horizontal move speed (px/frame)
KAREN_JUMP_VEL      = -14       # initial jump velocity
KAREN_MAX_HEALTH    = 5         # hearts
KAREN_HEIGHT_PCT    = 0.15      # 15 % of screen height
KAREN_HEIGHT        = int(SCREEN_H * KAREN_HEIGHT_PCT)   # ~115 px
KAREN_SPAWN_X       = 120
KAREN_SPAWN_Y       = FLOOR_Y - KAREN_HEIGHT             # sits on floor
KAREN_IFRAMES       = 90        # invincibility frames after hit
KAREN_ANIM_SPEED    = 8         # frames per animation step

# Sound-wave projectile  (FIX 4 — karen1 base radius cut 50%)
# Base values are for Tier 1.  Tiers 2 & 3 scale up from these.
WAVE_SPEED          = 9
WAVE_INIT_R         = 6          # ← was 12, now 6  (−50%)
WAVE_MAX_R          = 45         # ← was 90, now 45 (−50%)
WAVE_GROW_RATE      = 1.25       # ← was 2.5, now 1.25 (−50%)

# Level-up thresholds  (accumulated token_level_up pickups)
TIER_THRESHOLDS     = {1: 0, 2: 1, 3: 2}   # at 1 → Tier 2; at 2 → Tier 3

# ─────────────────────────────────────────────
#  ENEMIES
# ─────────────────────────────────────────────
# Flyer (sine-wave jetpack)
FLYER_SPEED         = 3
FLYER_AMP           = 60        # sine amplitude (px)
FLYER_FREQ          = 0.04      # sine frequency (rad/frame)
FLYER_HEIGHT        = int(SCREEN_H * 0.11)
FLYER_Y_RANGE       = (120, 420)  # random spawn y-band

# Skater (fast ground patrol)
SKATER_SPEED        = 5
SKATER_HEIGHT       = int(SCREEN_H * 0.11)
SKATER_Y            = FLOOR_Y   # feet on floor

# Slacker (static platform tank)
SLACKER_HEIGHT      = int(SCREEN_H * 0.12)
SLACKER_HEALTH      = 3         # takes 3 hits to kill

# Spawn-X intervals
SPAWN_INTERVALS     = [(800, 1500), (1800, 2500)]

# ─────────────────────────────────────────────
#  BOSS
# ─────────────────────────────────────────────
BOSS_HEIGHT         = int(SCREEN_H * 0.30)
# Boss spawns at the far-right arena, centred horizontally within it
BOSS_SPAWN_X        = WORLD_W - BOSS_ARENA_W + SCREEN_W // 2
BOSS_SPAWN_Y        = FLOOR_Y
BOSS_HEALTH         = 10
BOSS_IDLE_DURATION  = 240       # frames boss stays idle/vulnerable
BOSS_ATTACK_DURATION= 300       # frames boss attacks (immune)
BOSS_FIREBALL_SPEED = 14        # ← was 7, doubled for range/difficulty
BOSS_FIREBALL_R     = 18
BOSS_FIREBALL_INTERVAL = 70     # ← was 90, fire more often
BOSS_FIREBALL_GRAVITY   = 0.20  # ← less gravity so balls travel further

# ─────────────────────────────────────────────
#  PLATFORMS  (procedurally generated — see platform.py)
# ─────────────────────────────────────────────
# Static fallback for first screen (also used for tests / non-procedural code)
PLATFORM_DEFS = [
    (160,  490, 200, 18),
    (420,  390, 200, 18),
    (700,  460, 200, 18),
    (920,  340, 200, 18),
    (1150, 430, 200, 18),
]

# Procedural platform generation parameters
PLAT_SPACING_MIN    = 180       # min horizontal gap between platforms
PLAT_SPACING_MAX    = 320       # max horizontal gap (reduced for consistency)
PLAT_Y_MIN          = 300       # highest a platform can be (px from top)
PLAT_Y_MAX          = 520       # lowest a platform can be (near floor)
PLAT_W_MIN          = 180       # min platform width
PLAT_W_MAX          = 280       # max platform width
PLAT_H              = 18        # platform thickness

# ─────────────────────────────────────────────
#  TOKENS / ECONOMY
# ─────────────────────────────────────────────
TOKEN_BONUS_SIZE    = 36
TOKEN_LEVELUP_SIZE  = 48
TOKEN_SPEED         = 0         # tokens fall with gravity
TOKEN_GRAVITY       = 0.4
# Token magnet: radius (world-px) within which tokens slide toward Karen
TOKEN_MAGNET_RADIUS = 180       # pixels
TOKEN_MAGNET_SPEED  = 4         # px/frame toward Karen when in range
# Level-up token drift: tokens move left slowly so they meet Karen
TOKEN_LEVELUP_DRIFT = -1.5      # px/frame leftward drift while airborne

# ─────────────────────────────────────────────
#  COLOURS  (neon-tech palette)
# ─────────────────────────────────────────────
NEON_CYAN    = (0,   255, 240)
NEON_PINK    = (255, 0,   160)
NEON_YELLOW  = (255, 220, 0  )
NEON_GREEN   = (0,   255, 100)
DARK_BG      = (10,  8,   30 )
WHITE        = (255, 255, 255)
RED          = (220, 40,  40 )
GOLD         = (255, 200, 0  )
TRANSPARENT  = (0,   0,   0,  0)

# ─────────────────────────────────────────────
#  Z-ORDER (draw priority)
# ─────────────────────────────────────────────
Z_BG         = 0
Z_PLATFORM   = 1
Z_TOKENS     = 2
Z_ENEMIES    = 3
Z_PLAYER     = 4
Z_PROJECTILE = 5
Z_HUD        = 6
