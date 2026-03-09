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

# Sound-wave projectile
WAVE_SPEED          = 9
WAVE_INIT_R         = 12
WAVE_MAX_R          = 90
WAVE_GROW_RATE      = 2.5

# Level-up thresholds  (accumulated token_level_up pickups)
TIER_THRESHOLDS     = {1: 0, 2: 3, 3: 6}   # at 3 level-ups → Tier 2 etc.

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
BOSS_SPAWN_X        = SCREEN_W - 220
BOSS_SPAWN_Y        = FLOOR_Y
BOSS_HEALTH         = 10
BOSS_IDLE_DURATION  = 240       # frames boss stays idle/vulnerable
BOSS_ATTACK_DURATION= 300       # frames boss attacks (immune)
BOSS_FIREBALL_SPEED = 7
BOSS_FIREBALL_R     = 18
BOSS_FIREBALL_INTERVAL = 90     # frames between fireball launches
BOSS_FIREBALL_GRAVITY   = 0.30

# ─────────────────────────────────────────────
#  PLATFORMS  (x, y, w, h)
# ─────────────────────────────────────────────
PLATFORM_DEFS = [
    (160,  490, 200, 18),
    (420,  390, 200, 18),
    (700,  460, 200, 18),
    (920,  340, 200, 18),
    (1150, 430, 200, 18),
]

# ─────────────────────────────────────────────
#  TOKENS / ECONOMY
# ─────────────────────────────────────────────
TOKEN_BONUS_SIZE    = 36
TOKEN_LEVELUP_SIZE  = 48
TOKEN_SPEED         = 0         # tokens fall with gravity
TOKEN_GRAVITY       = 0.4

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
