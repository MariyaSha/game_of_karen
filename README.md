# game_of_karen
a Pygame platformer featuring a legendary social hero on her quest to the manager

---

# Game of Karen — Refactored

A **2D side-scrolling platformer** set in a neon-tech retail environment, built with Python + Pygame.  
Refactored from the original `app.py` quickstart into a fully modular, Object-Oriented architecture.

---

## Quick Start

```bash
pip install pygame-ce
cd game_of_karen
python main.py
```

> **Requires Python 3.10+** and a display (X11 / macOS / Windows).  
> For headless testing: `SDL_VIDEODRIVER=offscreen SDL_AUDIODRIVER=dummy python main.py`

---

## Controls

| Key | Action |
|-----|--------|
| `A` / `←` | Move left |
| `D` / `→` | Move right |
| `SPACE` | Jump |
| `F` | Fire Sound Wave |
| `R` | Restart (Game Over / Victory) |
| `Q` | Quit |

---

## Architecture

```
game_of_karen/
├── main.py               # Entry point
├── assets/               # All PNG sprites (from MariyaSha/game_of_karen)
└── src/
    ├── settings.py       # All constants & tunable values
    ├── fonts.py          # Cross-platform font helper
    ├── asset_loader.py   # Centralised asset cache (load once, reuse)
    ├── platform.py       # Platform class (Rect-based, neon-lit)
    ├── karen.py          # Karen player class + SoundWave projectile
    ├── enemies.py        # Enemy hierarchy: Flyer, Skater, Slacker
    ├── boss.py           # BossManager + Fireball (two-phase state machine)
    ├── tokens.py         # BonusToken & LevelUpToken collectibles
    ├── spawner.py        # Timed enemy spawn system
    ├── hud.py            # HUD, ParticleSystem, NotificationSystem
    └── game_manager.py   # Central orchestrator & game loop
```

### Class Overview

| Class | Responsibility |
|-------|----------------|
| `Karen` | Player: Tiers 1-3, 5 hearts, walk/jump/fall/attack animations, SoundWave firing |
| `SoundWave` | Growing circular projectile (speed 9px/frame, expands to 90px radius) |
| `FlyerEnemy` | Jetpack enemy: constant leftward movement + sine-wave vertical oscillation |
| `SkaterEnemy` | Fast ground patrol: bounces off screen edges |
| `SlackerEnemy` | Static tank on platforms: 3 HP, health bar, drops bonus token |
| `BossManager` | Two-phase state machine (ATTACK: immune+fireballs / IDLE: vulnerable) |
| `Fireball` | Parabolic projectile launched from boss toward player position |
| `Platform` | Rect-based surface with neon-cyan edge glow; Slacker spawn point |
| `EnemySpawner` | Frame-timer spawning with escalating difficulty |
| `BonusToken` | +100 credits on collect |
| `LevelUpToken` | Triggers Karen Tier 1→2→3 evolution |
| `ParticleSystem` | Spark burst FX on hits and collections |
| `NotificationSystem` | Floating text messages (+credits, tier up, boss arrival) |
| `HUD` | Hearts, tier badge, score, boss bar, controls, game-over overlay |
| `GameManager` | Wires all systems; resolves all collisions; manages game states |

---

## Gameplay

### Karen's Tier System
- Collect **Level-Up Tokens** (★ icons) to evolve Karen
  - **3 tokens** → Tier 2 (yellow Sound Wave)
  - **6 tokens** → Tier 3 (pink Sound Wave)
- Each tier changes Karen's sprite and wave colour

### Enemy Types
| Enemy | Movement | Health | Drop |
|-------|----------|--------|------|
| Flyer | Sine-wave, left | 1 HP | Bonus token |
| Skater | Ground patrol, bounce | 1 HP | Level-Up token |
| Slacker | Static, on platforms | 3 HP | Bonus token |

### Boss Fight
Triggered at **2,000 credits**. The Store Manager has two phases:
- **ATTACK** (immune): Launches parabolic fireballs at Karen's position
- **IDLE** (vulnerable): Can be hit by Karen's Sound Wave

Hit the boss **10 times** during idle phase to win!

---

## Asset Credits
Original assets by **[MariyaSha](https://github.com/MariyaSha/game_of_karen)** — MIT License.
