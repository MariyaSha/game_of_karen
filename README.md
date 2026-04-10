# Game Of Karen
a Pygame platformer featuring a legendary social hero on her quest to the manager

## Video Tutorial
Want to see how it's made? Follow the complete development process in this comprehensive video guide:
<br>
<br>
<a href="https://youtu.be/fI9Z1-SPfaI" target="_blank">
<img width="600" height="1080" alt="Game of Karen Thumbnail Image Featuring Mariya Sha" src="https://github.com/user-attachments/assets/b4905731-f31c-447c-be92-115eea92f428" />
</a>
<br>
*Click the image above to watch the tutorial.*

## Quick Start

1. install dependencies in WSL:
```bash
sudo apt update
sudo apt install libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-ttf-2.0-0 libsdl2-2.0-0
```

2. craate environemnt:
```bash
conda create -n karen_env python=3.12
conda activate karen_env
```
3. insatll pygame:
```bash
pip install pygame
```

4. clone and run game:
```bash
git clone https://github.com/MariyaSha/game_of_karen.git
cd game_of_karen
python main.py
```

## Screenshots

<img width="900" alt="Game of Karen Screenshot 1" src="https://github.com/user-attachments/assets/84002056-83cd-4d8d-9e56-6c27fc87b6cf" />
<br>
<img width="900" alt="Game of Karen Screenshot 2" src="https://github.com/user-attachments/assets/1ab10a78-92ec-4a4f-8a59-846ac2d427bc" />

## Current Issues - Awaiting Fix!
Audio buffer gets overwhelmed and doesn't play game theme music properly. The theme initializes in the correct speed and quality, but immediatley slows down and quality degrades. When restarting the game - theme restarts at lower speed and lower quanity from the get go.

### Solutions That Didn't Work:
- compressing theme song to .WAV
- compressing theme song to .OGG
- increasing buffer to 1024, 2048, 4096, 8192
- changing frequency to 48000

If you have a solution - please send a fix 🙏

## Controls

| Key | Action |
|-----|--------|
| `A` / `←` | Move left |
| `D` / `→` | Move right |
| `SPACE` | Jump |
| `F` | Fire Sound Wave |
| `R` | Restart (Game Over / Victory) |
| `Q` | Quit |

## Architecture

```
game_of_karen/
├── main.py               # Entry point
├── assets/               # All PNG sprites (from MariyaSha/game_of_karen)
└── src/
    ├── audio.py          # Centralised SoundManager & SFX triggers
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
| `SoundManager` | Audio Engine: Manages music channels, and pre-loads SFX |

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

## Gameplay

### Boss Fight: The Manager
The final encounter is triggered when Karen reaches the **end of the world map** (the Arena). Once the Manager arrives, the fight enters a two-phase state machine:

- **ATTACK Phase (Immune):** The Manager is invulnerable and launches parabolic fireballs targeted at Karen’s current position.
- **IDLE Phase (Vulnerable):** The Manager stops firing and becomes susceptible to damage. Use this window to land hits with your **Sound Waves**.

**Objective:** Land **10 hits** during the IDLE phase to secure a victory and speak to the Manager!

## Asset Credits
Original assets by Genspark AI + **[MariyaSha](https://github.com/MariyaSha/game_of_karen)** — MIT License.
