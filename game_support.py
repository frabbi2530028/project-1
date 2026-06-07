# ===== Merged from game_config.py =====
import arcade
import math
from pathlib import Path

# ─────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────

SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE  = "Space Shooter: Neon Drift"

BG_COLOR = (6, 9, 24)

CLASSIC_SPACE_THEMES = [
    {
        "key": "saturn",
        "label": "SATURN",
        "bg": (5, 8, 24),
        "planet": (226, 177, 105),
        "glow": (255, 205, 125),
        "nebula1": (72, 84, 165),
        "nebula2": (160, 96, 180),
        "star": (218, 230, 255),
        "x": 0.82,
        "y": 0.30,
        "r": 92,
        "rings": True,
    },
    {
        "key": "mars",
        "label": "MARS",
        "bg": (20, 7, 13),
        "planet": (214, 93, 48),
        "glow": (255, 110, 62),
        "nebula1": (170, 58, 42),
        "nebula2": (90, 42, 82),
        "star": (255, 214, 185),
        "x": 0.17,
        "y": 0.74,
        "r": 72,
        "rings": False,
    },
    {
        "key": "uranus",
        "label": "URANUS",
        "bg": (4, 18, 28),
        "planet": (128, 225, 218),
        "glow": (125, 245, 235),
        "nebula1": (42, 160, 170),
        "nebula2": (80, 96, 190),
        "star": (202, 255, 246),
        "x": 0.78,
        "y": 0.72,
        "r": 78,
        "rings": True,
    },
    {
        "key": "neptune",
        "label": "NEPTUNE",
        "bg": (3, 8, 31),
        "planet": (56, 105, 230),
        "glow": (68, 150, 255),
        "nebula1": (36, 72, 180),
        "nebula2": (76, 36, 155),
        "star": (190, 218, 255),
        "x": 0.20,
        "y": 0.28,
        "r": 84,
        "rings": False,
    },
    {
        "key": "venus",
        "label": "VENUS",
        "bg": (25, 14, 10),
        "planet": (236, 185, 105),
        "glow": (255, 206, 122),
        "nebula1": (184, 104, 60),
        "nebula2": (100, 76, 140),
        "star": (255, 232, 190),
        "x": 0.72,
        "y": 0.36,
        "r": 82,
        "rings": False,
    },
    {
        "key": "sun",
        "label": "SUN",
        "bg": (26, 7, 3),
        "planet": (255, 190, 52),
        "glow": (255, 96, 32),
        "nebula1": (220, 68, 25),
        "nebula2": (255, 152, 45),
        "star": (255, 236, 170),
        "x": 0.88,
        "y": 0.72,
        "r": 118,
        "rings": False,
    },
]

PLAYER_SPEED        = 320
ENEMY_SPEED         = 125
BOSS_SPEED          = 82

PLAYER_HEALTH       = 100
ENEMY_HEALTH        = 30
BOSS_HEALTH         = 220

BULLET_SPEED        = 660
ENEMY_BULLET_SPEED  = 430
POWERUP_FALL_SPEED  = 105
POWERUP_SCREEN_LIFE = 4.0   # seconds before an uncollected powerup fades out
POWERUP_DURATION    = 6.0   # seconds the active effect lasts (was 10)

NORMAL_FIRE_RATE    = 0.22
AUTO_FIRE_RATE      = 0.075

POWERUP_DURATION    = 6.0   # seconds the active effect lasts
DROP_CHANCE         = 40

STAR_COUNT          = 145
MAX_PARTICLES       = 700
CONTACT_DAMAGE      = 14
CONTACT_DAMAGE_COOLDOWN = 0.35

MAX_POWERUP_STORAGE = 10
AUTO_SHIELD_HEALTH_RATIO  = 0.50

POWERUP_KEYS = {
    arcade.key.KEY_1: "speed",
    arcade.key.KEY_2: "shield",
    arcade.key.KEY_3: "triple",
    arcade.key.KEY_5: "elec360",   # Reaper special
    arcade.key.NUM_1: "speed",
    arcade.key.NUM_2: "shield",
    arcade.key.NUM_3: "triple",
    arcade.key.NUM_5: "elec360",
    arcade.key.B: "breach",        # Maze-mode wall breaker
}

# ─────────────────────────────────────────────────────
#  CURRENCY
# ─────────────────────────────────────────────────────

COIN_VALUE_ENEMY    = 5
COIN_VALUE_SHOOTING = 8
COIN_VALUE_BOSS     = 35
COIN_MAGNET_RANGE   = 130   # px — auto-collect radius when Coiadd n Magnet is purchased
SAVE_FILE = Path(__file__).resolve().parent / "neon_drift_save.json"

# ─────────────────────────────────────────────────────
#  SHOP
# ─────────────────────────────────────────────────────

STATE_SHOP = "shop"

SHOP_ITEMS = [
    {
        "id":    "armor",
        "name":  "ARMOR PLATING",
        "desc":  "+25 Max HP per tier",
        "cost":  [60, 90, 130],
        "max":   3,
        "color": (255, 90, 90),
        "icon":  "HP+",
    },
    {
        "id":    "engine",
        "name":  "ENGINE TUNER",
        "desc":  "+12% Speed per tier",
        "cost":  [80, 130],
        "max":   2,
        "color": (255, 220, 40),
        "icon":  "SPD",
    },
    {
        "id":    "lucky",
        "name":  "LUCKY CRATE",
        "desc":  "+15% Powerup drops",
        "cost":  [90, 140],
        "max":   2,
        "color": (100, 220, 100),
        "icon":  "LCK",
    },
    {
        "id":    "magnet",
        "name":  "COIN MAGNET",
        "desc":  "Auto-collect nearby coins",
        "cost":  [110],
        "max":   1,
        "color": (255, 210, 30),
        "icon":  "MAG",
    },
    {
        "id":    "starter_shield",
        "name":  "STARTER SHIELD",
        "desc":  "Begin each run with 1 Shield",
        "cost":  [100],
        "max":   1,
        "color": (55, 215, 255),
        "icon":  "SHD",
    },
    {
        "id":    "double_coins",
        "name":  "COIN DOUBLER",
        "desc":  "Earn 50% more coins per kill",
        "cost":  [150],
        "max":   1,
        "color": (255, 185, 50),
        "icon":  "x2C",
    },
]

# ─────────────────────────────────────────────────────
#  DIFFICULTY PRESETS
# ─────────────────────────────────────────────────────

DIFFICULTY_PRESETS = {
    "easy": {
        "label":               "EASY",
        "color":               (55, 220, 100),
        # enemies
        "enemy_speed_mult":    0.62,      # much slower
        "enemy_fire_rate":     2.4,       # seconds between shots (higher = rarer)
        "spawn_interval_mult": 2.0,       # spawn timer multiplier (higher = fewer spawns)
        "max_regular_enemies": 7,         # hard cap of basic+shooting on screen
        # boss
        "boss_health_mult":    0.75,
        "boss_speed_mult":     0.70,
        "boss_normal_rate":    2.2,       # seconds between regular boss shots
        "boss_special_rate":   6.5,       # seconds between spread attacks
        "boss_spread_count":   3,         # bullets in spread
        "boss_spread_speed":   1.0,       # multiplier on bullet speed
    },
    "medium": {
        "label":               "MEDIUM",
        "color":               (255, 205, 40),
        "enemy_speed_mult":    1.0,
        "enemy_fire_rate":     1.1,
        "spawn_interval_mult": 1.0,
        "max_regular_enemies": 16,
        "boss_health_mult":    1.0,
        "boss_speed_mult":     1.0,
        "boss_normal_rate":    1.45,
        "boss_special_rate":   4.8,
        "boss_spread_count":   5,
        "boss_spread_speed":   1.0,
    },
    "hard": {
        "label":               "HARD",
        "color":               (255, 55, 55),
        "enemy_speed_mult":    1.48,      # extra speed boost
        "enemy_fire_rate":     0.50,      # fires very fast
        "spawn_interval_mult": 0.60,      # spawns flood in
        "max_regular_enemies": 999,       # no cap
        "boss_health_mult":    1.90,      # much more health
        "boss_speed_mult":     1.38,      # extra boss speed boost
        "boss_normal_rate":    0.72,      # rapid regular shots
        "boss_special_rate":   2.6,       # frequent spreads
        "boss_spread_count":   5,         # exactly 5 bullets per spread (as requested)
        "boss_spread_speed":   1.25,      # faster spread bullets
    },
}

DIFFICULTY_ORDER = ["easy", "medium", "hard"]

# ─────────────────────────────────────────────────────
#  GAME STATES
# ─────────────────────────────────────────────────────

STATE_MENU        = "menu"
STATE_PLAYING     = "playing"
STATE_PAUSED      = "paused"
STATE_GAMEOVER    = "gameover"
STATE_LEVEL_SELECT = "level_select"
STATE_LEVEL_CLEAR  = "level_clear"
STATE_MODE_SELECT  = "mode_select"

# ─────────────────────────────────────────────────────
#  MAZE MODE CONSTANTS
# ─────────────────────────────────────────────────────

MAZE_CELL_SIZE    = 240         # pixels per cell
MAZE_WALL_THICK   = 60          # wall line thickness
MAZE_BASE_COLS    = 29          # starting grid width  — larger than screen
MAZE_BASE_ROWS    = 21          # starting grid height — larger than screen
MAZE_MAX_LEVELS   = 10          # visible maze floors
MAZE_LEGACY_FLOORS = (1, 5, 10, 15, 20, 25, 30, 35, 40, 50)
MAZE_KEYS_REQUIRED = 3          # keys needed to unlock the floor exit
MAZE_ENEMIES_PER_KEY = 30       # initial maze enemies clustered around each key
MAZE_ENEMY_COUNT_PER_FLOOR = 20 # extra starting enemies added per visible floor
MAZE_KEY_RELOCATE_TIME = 85.0   # seconds before uncollected keys jump elsewhere
MAZE_CORNER_WAVE_INTERVAL = 10.0 # seconds between five-enemy maze waves
MAZE_CORNER_WAVE_SIZE = 5       # enemies spawned per corner wave
MAZE_POTION_SPAWN_INTERVAL = 10.0 # seconds between repeated maze powerup spawns
MAZE_MAX_POTIONS = 12           # max uncollected powerups waiting in the maze

# ── Maze enemy constants ──────────────────────────────────────────────────────
MAZE_ENEMY_HEALTH         = 90     # HP per maze enemy
MAZE_ENEMY_MAX_SPLITS     = 3      # normal enemies die after their 3rd split form
MAZE_ENEMY_SPLIT_SIZE_MULT = 0.82  # each split form is smaller
MAZE_ENEMY_SPLIT_HEALTH_MULT = 0.75 # each split form has less HP
MAZE_ENEMY_SPEED          = 88     # px/s movement speed
MAZE_ENEMY_BULLET_DAMAGE  = 8      # maze enemy bullet damage
MAZE_ENEMY_BULLET_SPEED   = 330    # px/s
MAZE_ENEMY_FIRE_RATE      = 2.0    # seconds between shots
MAZE_ENEMY_SPAWN_INTERVAL = 2.8    # seconds between spawns
MAZE_ENEMY_SPAWN_MIN_INTERVAL = 0.55  # fastest spawn pace near maze completion
MAZE_ENEMIES_PER_FLOOR    = MAZE_KEYS_REQUIRED * MAZE_ENEMIES_PER_KEY  # initial enemies per floor
MAZE_ENEMY_BULLET_LIFE    = 4.0    # max seconds before auto-removal
MAZE_ENEMY_BASE_CAP       = 200    # starting max active enemies on a maze floor
MAZE_ENEMY_CAP_PER_FLOOR  = 20     # active enemy cap added per visible floor
MAZE_ENEMY_MAX_CAP        = MAZE_ENEMY_BASE_CAP + (MAZE_MAX_LEVELS - 1) * MAZE_ENEMY_CAP_PER_FLOOR
MAZE_POWERUP_DROP_CHANCE  = 70     # % chance a maze enemy drops a powerup
MAZE_POWERUP_PITY_KILLS   = 2      # guarantee a drop after this many dry enemy kills
MAZE_BREACH_DROP_CHANCE   = MAZE_POWERUP_DROP_CHANCE
MAZE_BREACH_DURATION      = 5.0    # seconds breach rounds can damage fragile walls
MAZE_BREACH_MAX_STORAGE   = 10     # floor-1 wall-breaking charge storage
MAZE_POWERUP_STORAGE_PER_FLOOR = 2 # extra storage for each stored powerup per floor
MAZE_BREAKABLE_WALL_HP    = 4      # breach hits needed to crack a fragile wall
MAZE_BREAKABLE_WALL_CHANCE = 0.18  # only some closed internal walls can be destroyed
MAZE_BOSS_TEXTURE         = "image/UvlV4Mu.png"
MAZE_BOSS_TEXTURE_SCALE   = 1.05
MAZE_BOSS_HEALTH          = 1_200
MAZE_BOSS_MAX_SPLITS      = 4
MAZE_BOSS_SPLIT_SIZE_MULT = 0.72
MAZE_BOSS_SHOT_DAMAGE     = 20     # same damage as player bullets
MAZE_PLAYER_START_SPEED_MULT = 0.58
MAZE_PLAYER_FINAL_SPEED_MULT = 1.0
MAZE_PLAYER_FINAL_HEALTH = MAZE_BOSS_HEALTH
STATE_MAZE        = "maze"
STATE_MAZE_OVER   = "maze_over"
STATE_MAZE_LOADOUT = "maze_loadout"
STATE_MAZE_SELECT = "maze_select"

# ─────────────────────────────────────────────────────
#  MAZE PRESETS  (player chooses one before starting)
#  Used by maze mode for different layouts and pacing
# ─────────────────────────────────────────────────────

MAZE_PRESETS = [
    {
        "key":        "classic",
        "name":       "CLASSIC",
        "icon":       "⬡",
        "desc":       "Balanced corridors, steady challenge",
        "detail":     "29×21 start · grows each floor",
        "color":      (90, 198, 255),
        "cols_bonus": 0,
        "rows_bonus": 0,
    },
    {
        "key":        "labyrinth",
        "name":       "LABYRINTH",
        "icon":       "◎",
        "desc":       "Vast twisting corridors to explore",
        "detail":     "33×23 start · massive scale-up",
        "color":      (120, 255, 160),
        "cols_bonus": 4,
        "rows_bonus": 2,
    },
    {
        "key":        "sprint",
        "name":       "SPRINT",
        "icon":       "◈",
        "desc":       "Compact arenas — reach exit fast",
        "detail":     "25×19 start · quick floors",
        "color":      (255, 220, 40),
        "cols_bonus": -4,
        "rows_bonus": -2,
    },
    {
        "key":        "gauntlet",
        "name":       "GAUNTLET",
        "icon":       "✦",
        "desc":       "Tall narrow maze — easy to get lost",
        "detail":     "27×27 start · vertical nightmare",
        "color":      (255, 90, 90),
        "cols_bonus": -2,
        "rows_bonus": 6,
    },
]

# ─────────────────────────────────────────────────────
#  LEVEL DEFINITIONS
#  boss_hp = sum of all enemy HP in that level
# ─────────────────────────────────────────────────────

def _level_boss_hp(regular: int, shooting: int, difficulty_mult: float = 1.0) -> int:
    """Boss HP = combined HP of every enemy in the level."""
    return int((regular * ENEMY_HEALTH + shooting * ENEMY_HEALTH * 1.4) * difficulty_mult)


def _campaign_total_boss_hp(difficulty_mult: float = 1.0) -> int:
    """
    Final level boss HP = every level's enemies combined plus every level boss combined.
    This makes level 10 the full campaign boss.
    """
    total = 0
    for lvl in LEVELS:
        enemy_hp = _level_boss_hp(lvl["regular_enemies"], lvl["shooting_enemies"], 1.0)
        boss_hp = _level_boss_hp(lvl["regular_enemies"], lvl["shooting_enemies"], lvl["boss_hp_mult"])
        total += enemy_hp + boss_hp
    return int(total * difficulty_mult)

def _build_levels() -> list:
    """
    Generate 10 levels.  Enemy count scales logarithmically from 200 (L1) to 600 (L10).
    total(n) = 200 + round(400 * log10(n))    n = 1..10
    Shooting enemies = ~30% of total, rest regular.
    Spawn rate tightens with each level.  Boss HP = combined enemy HP.
    """
    names = [
        (1,  "DAWN PATROL",   "First contact — rookies in the dark",          (80,  220, 130), "AURORA VANGUARD", "image/aurora_vanguard.png", 3.00, 3.50),
        (2,  "NOVA SURGE",    "Faster waves, denser skies",                    (90,  180, 255), "NOVA WRAITH",     "image/nova_wraith.png",     0.38, 0.44),
        (3,  "IRON CROSS",    "Shielded interceptors join the fray",           (255, 200,  50), "IRON SERAPH",     "image/iron_seraph.png",     0.55, 0.72),
        (4,  "CRIMSON TIDE",  "Elite fighters & coordinated fire",             (255, 100,  80), "CRIMSON VIPER",   "image/crimson_viper.png",   0.08, 0.10),
        (5,  "SOLAR FLARE",   "Relentless sun-scorched assault",               (255, 165,  40), "SOLAR PHOENIX",   "image/solar_phoenix.png",   0.36, 0.44),
        (6,  "NEBULA RIFT",   "Dense formations & heavy artillery",            (140, 100, 255), "NEBULA TITAN",    "image/nebula_titan.webp",   0.15, 0.18),
        (7,  "OBSIDIAN GATE", "Elite guard — precision or death",              (80,  210, 220), "OBSIDIAN REX",     "image/obsidian_rex.png",    0.20, 0.32),
        (8,  "VOID STORM",    "Maximum aggression — bullets everywhere",       (200, 100, 255), "VOID REAPER",      "image/void_reaper.png",     0.20, 0.32),
        (9,  "SINGULARITY",   "The abyss opens — no mercy",                   (255,  60, 120), "GRAVECROWN",       "image/gravecrown.png",      0.20, 0.32),
        (10, "FINAL HORIZON", "Last stand — the combined fleet arrives",       (255, 220,  80), "OMEGA CORE",       "image/omega_core.png",      0.20, 0.32),
    ]
    levels = []
    for i, (num, name, subtitle, color, boss_name, boss_texture,
            boss_texture_scale, boss_portrait_scale) in enumerate(names):
        n = i + 1
        if n == 1:
            total = 200
        else:
            total = 200 + round(400 * math.log10(n))
        shooting = round(total * 0.30)
        regular  = total - shooting
        # spawn rate: fast at L1, gets tighter each level (min 0.12s)
        spawn_rate  = max(0.12, 0.55 - 0.04 * i)
        shoot_rate  = max(0.60, 2.2  - 0.17 * i)
        boss_mult   = 1.0 + 0.12 * i
        reward      = 250 + i * 120
        # unlock: completed (beat the boss of) previous level
        levels.append({
            "number":           num,
            "name":             name,
            "subtitle":         subtitle,
            "color":            color,
            "regular_enemies":  regular,
            "shooting_enemies": shooting,
            "spawn_rate":       spawn_rate,
            "shoot_rate":       shoot_rate,
            "boss_hp_mult":     boss_mult,
            "boss_name":        boss_name,
            "boss_texture":     boss_texture,
            "boss_texture_scale": boss_texture_scale,
            "boss_portrait_scale": boss_portrait_scale,
            "reward_coins":     reward,
            "requires_level":   i - 1,   # index of level that must be completed (-1 = none)
        })
    return levels

LEVELS = _build_levels()

# ─────────────────────────────────────────────────────
#  UI THEMES
# ─────────────────────────────────────────────────────

THEMES = {
    "dark": {
        # ── menu / UI ─────────────────────────────────
        "bg":              (6, 9, 24),
        "panel_fill":      (7, 15, 44, 220),
        "panel_border":    (70, 112, 205, 218),
        "panel_inner":     (70, 112, 205, 40),
        "title":           (90, 205, 255),
        "title_shadow":    (25, 85, 185, 110),
        "subtitle":        (125, 162, 222),
        "text":            (200, 220, 255),
        "text_dim":        (115, 140, 192),
        "btn_fill":        (16, 50, 135, 238),
        "btn_border":      (80, 162, 255, 252),
        "btn_hover":       (38, 88, 195, 248),
        "btn_text":        (255, 255, 255),
        "btn_text_dim":    (180, 205, 245),
        "card_fill":       (9, 19, 52, 228),
        "card_border":     (52, 92, 170, 192),
        "card_sel_fill":   (20, 65, 168, 250),
        "card_sel_border": (80, 192, 255, 255),
        "card_hover_fill": (14, 35, 90, 235),
        "locked_fill":     (14, 16, 38, 190),
        "locked_border":   (38, 44, 74, 158),
        "locked_text":     (70, 82, 120),
        "accent":          (90, 198, 255),
        "divider":         (70, 112, 205, 88),
        "stat_filled":     (90, 198, 255),
        "stat_empty":      (30, 45, 85),
        "selected_badge":  (90, 198, 255),
        "toggle_text":     (150, 190, 255),
        "hud_panel":       (8, 16, 42, 178),
        "hud_border":      (90, 122, 188, 182),
        "hud_text":        (210, 228, 255),
        "hud_text_dim":    (165, 185, 225),
        # ── game world ────────────────────────────────
        "world_bg":        (6, 9, 24),
        "nebula1":         (40,  85, 190, 42),
        "nebula2":         (150, 45, 170, 34),
        "nebula3":         (30, 160, 200, 18),
        "grid_line":       (30, 46, 78, 26),
        "star_color":      (205, 228, 255),
        "player_glow":     (95, 200, 255, 68),
        "player_glow_spd": (255, 230, 90, 82),
        "enemy_glow":      (255, 92,  92,  48),
        "shoot_glow":      (255, 130, 90,  55),
        "boss_glow":       (255, 60,  60,  60),
        "bullet_glow":     (255, 200, 110, 55),
        "ebullet_glow":    (255, 85,  85,  55),
        "shield_ring":     (90, 235, 255, 230),
        "crosshair":       (130, 220, 255, 185),
        "damage_flash":    (255, 65,  65,  170),
        "engine_particle": (120, 205, 255),
        "powerup_label":   (255, 255, 255),
        "gameover_bg":     (3, 5, 18, 210),
        "gameover_card":   (8, 12, 32, 235),
        "gameover_border": (200, 40, 40, 180),
        "gameover_accent": (255, 60, 60, 160),
        "hp_bar_bg":       (28, 35, 55, 220),
        "vignette":        (0, 0, 0),
    },
    "light": {
        # ── menu / UI ─────────────────────────────────
        "bg":              (192, 212, 248),
        "panel_fill":      (236, 243, 255, 228),
        "panel_border":    (100, 145, 228, 228),
        "panel_inner":     (100, 145, 228, 35),
        "title":           (14, 50, 142),
        "title_shadow":    (90, 148, 240, 85),
        "subtitle":        (62, 98, 162),
        "text":            (14, 34, 86),
        "text_dim":        (68, 98, 155),
        "btn_fill":        (46, 112, 225, 240),
        "btn_border":      (20, 74, 180, 250),
        "btn_hover":       (35, 98, 212, 250),
        "btn_text":        (255, 255, 255),
        "btn_text_dim":    (215, 230, 255),
        "card_fill":       (222, 234, 255, 235),
        "card_border":     (106, 152, 228, 208),
        "card_sel_fill":   (46, 118, 232, 250),
        "card_sel_border": (20, 80, 198, 255),
        "card_hover_fill": (210, 225, 252, 240),
        "locked_fill":     (206, 214, 232, 205),
        "locked_border":   (148, 162, 200, 165),
        "locked_text":     (132, 148, 186),
        "accent":          (28, 90, 218),
        "divider":         (100, 145, 228, 82),
        "stat_filled":     (28, 90, 218),
        "stat_empty":      (185, 200, 230),
        "selected_badge":  (28, 90, 218),
        "toggle_text":     (255, 255, 255),
        "hud_panel":       (228, 238, 255, 188),
        "hud_border":      (95, 138, 210, 182),
        "hud_text":        (14, 34, 86),
        "hud_text_dim":    (68, 98, 155),
        # ── game world (bright nebula / daytime space) ─
        "world_bg":        (168, 200, 245),
        "nebula1":         (180, 110, 240, 38),
        "nebula2":         (255, 145, 80,  30),
        "nebula3":         (80,  185, 255, 25),
        "grid_line":       (140, 170, 220, 18),
        "star_color":      (50,  80,  180),
        "player_glow":     (30, 130, 255, 90),
        "player_glow_spd": (255, 175, 20, 95),
        "enemy_glow":      (210, 40,  40,  70),
        "shoot_glow":      (215, 95,  20,  75),
        "boss_glow":       (175, 15,  15,  90),
        "bullet_glow":     (255, 165, 20,  80),
        "ebullet_glow":    (210, 30,  30,  80),
        "shield_ring":     (20, 140, 255, 235),
        "crosshair":       (20,  90, 210, 210),
        "damage_flash":    (220, 50,  50,  155),
        "engine_particle": (40, 130, 255),
        "powerup_label":   (14, 34, 86),
        "gameover_bg":     (210, 225, 248, 210),
        "gameover_card":   (230, 240, 255, 238),
        "gameover_border": (30, 90, 200, 180),
        "gameover_accent": (20, 80, 195, 160),
        "hp_bar_bg":       (185, 205, 240, 200),
        "vignette":        (90, 130, 200),
    },
}

# ─────────────────────────────────────────────────────
#  SHIP ROSTER
# ─────────────────────────────────────────────────────

SHIPS = [
    {
        "name":      "NEON FURY",
        "tagline":   "Balanced fighter",
        "stat_spd":  3, "stat_atk": 3, "stat_def": 3,
        "color":     (90, 198, 255),
        "available": True,
        "texture":   "image/player.png",
        "tex_scale": 0.22,
        "spd_mult":  1.0,
        "hp_mult":   1.0,
    },
    {
        "name":      "PHANTOM",
        "tagline":   "Swift & elusive",
        "stat_spd":  5, "stat_atk": 2, "stat_def": 1,
        "color":     (192, 120, 255),
        "available": True,
        "texture":   "image/phantom.png",
        "tex_scale": 0.20,
        "spd_mult":  1.45,
        "hp_mult":   0.65,
    },
    {
        "name":      "TITAN",
        "tagline":   "Heavy destroyer",
        "stat_spd":  1, "stat_atk": 5, "stat_def": 5,
        "color":     (255, 155, 70),
        "available": True,
        "texture":   "image/titan.png",
        "tex_scale": 0.11,
        "spd_mult":  0.68,
        "hp_mult":   1.65,
    },
    {
        "name":      "INTERCEPTOR",
        "tagline":   "Beam destroyer",
        "stat_spd":  4, "stat_atk": 5, "stat_def": 2,
        "color":     (255, 90, 60),
        "available": True,
        "texture":   "image/interceptor.png",
        "tex_scale": 0.17,
        "spd_mult":  1.15,
        "hp_mult":   0.80,
        # unique trait flags
        "beam_weapon": True,    # fires a beam instead of bullets
    },
    {
        "name":      "REAPER",
        "tagline":   "Electric storm",
        "stat_spd":  2, "stat_atk": 5, "stat_def": 4,
        "color":     (120, 80, 255),
        "available": True,
        "texture":   "image/reaper.png",
        "tex_scale": 0.17,
        "spd_mult":  0.85,
        "hp_mult":   1.35,
        # unique trait flags
        "electric_weapon": True,   # fires electric bolts; special 360° blast
    },
]

# Which ship index uses the beam weapon?
BEAM_SHIP_INDICES     = {i for i, s in enumerate(SHIPS) if s.get("beam_weapon")}
# Which ship index uses the electric weapon?
ELECTRIC_SHIP_INDICES = {i for i, s in enumerate(SHIPS) if s.get("electric_weapon")}

# ─────────────────────────────────────────────────────
#  TEXTURE CACHE
# ─────────────────────────────────────────────────────

_texture_cache: dict = {}
ASSET_ROOT = Path(__file__).resolve().parent
ASSET_ALIASES = {
    "image/reaper.png": "image/reaper_1.png",
}


# ===== Merged from game_assets.py =====
import arcade
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


_texture_cache: dict = {}
ASSET_ROOT = Path(__file__).resolve().parent
ASSET_ALIASES = {
    "image/reaper.png": "image/reaper_1.png",
}

def _remove_background(img: Image.Image, threshold: int = 210) -> Image.Image:
    """
    Flood-fill from all four edges to remove the background colour
    (white, light-grey, or any uniform border colour).  Only pixels
    that are *reachable from the image border* and brighter than
    `threshold` in all three channels are made transparent.
    This preserves metallic/silver interior ship parts that happen to
    be bright, because they are not connected to the outer border.
    """
    arr = np.array(img, dtype=np.uint8)   # shape (H, W, 4)
    img_h, img_w = arr.shape[:2]

    # ── Build a boolean mask of background pixels via BFS ──────────
    visited = np.zeros((img_h, img_w), dtype=bool)
    queue   = deque()

    def _seed(row: int, col: int) -> None:
        if not visited[row, col]:
            pr, pg, pb = int(arr[row, col, 0]), int(arr[row, col, 1]), int(arr[row, col, 2])
            if pr > threshold and pg > threshold and pb > threshold:
                visited[row, col] = True
                queue.append((row, col))

    # Seed from every pixel on all four edges
    for col in range(img_w):
        _seed(0, col);         _seed(img_h - 1, col)
    for row in range(img_h):
        _seed(row, 0);         _seed(row, img_w - 1)

    # BFS — spread to 4-connected bright neighbours
    while queue:
        row, col = queue.popleft()
        arr[row, col, 3] = 0          # make transparent
        for drow, dcol in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nrow, ncol = row + drow, col + dcol
            if 0 <= nrow < img_h and 0 <= ncol < img_w and not visited[nrow, ncol]:
                pr, pg, pb = int(arr[nrow, ncol, 0]), int(arr[nrow, ncol, 1]), int(arr[nrow, ncol, 2])
                if pr > threshold and pg > threshold and pb > threshold:
                    visited[nrow, ncol] = True
                    queue.append((nrow, ncol))

    return Image.fromarray(arr)


# Resampling filter — works with both old and new Pillow versions
try:
    _RESAMPLE = Image.Resampling.LANCZOS   # Pillow >= 9.1
except AttributeError:
    _RESAMPLE = Image.LANCZOS              # Pillow < 9.1


def _resolve_asset_path(path: str) -> Path | None:
    raw_path = Path(path)
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(raw_path)
        candidates.append(ASSET_ROOT / raw_path)

    alias = ASSET_ALIASES.get(path)
    if alias:
        alias_path = Path(alias)
        candidates.append(alias_path)
        candidates.append(ASSET_ROOT / alias_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if raw_path.suffix:
        search_dirs = []
        if raw_path.parent:
            search_dirs.extend([raw_path.parent, ASSET_ROOT / raw_path.parent])
        else:
            search_dirs.extend([Path("."), ASSET_ROOT])

        for directory in search_dirs:
            if not directory.exists():
                continue
            matches = sorted(directory.glob(f"{raw_path.stem}*{raw_path.suffix}"))
            if matches:
                return matches[0]

    return None


def _missing_texture(path: str, scale: float) -> arcade.Texture:
    size = max(36, int(160 * max(scale, 0.18)))
    img = Image.new("RGBA", (size, size), (20, 26, 46, 230))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((2, 2, size - 3, size - 3), radius=10,
                           outline=(255, 120, 90, 255), width=3,
                           fill=(28, 34, 60, 230))
    draw.line((10, 10, size - 11, size - 11), fill=(255, 170, 80, 255), width=4)
    draw.line((size - 11, 10, 10, size - 11), fill=(255, 170, 80, 255), width=4)
    draw.rectangle((size * 0.32, size * 0.32, size * 0.68, size * 0.68),
                   outline=(120, 220, 255, 255), width=3)
    return arcade.Texture(image=img)


def _make_phantom_texture() -> arcade.Texture:
    """Sleek purple ghost-wing ship for the Phantom."""
    key = ("__phantom__raw",)
    if key in _texture_cache: return _texture_cache[key]
    S = 96
    img  = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)
    cx   = S // 2
    # Main fuselage — thin elongated needle
    d.polygon([(cx, 4), (cx+7, S-18), (cx, S-8), (cx-7, S-18)],
              fill=(210, 140, 255, 240))
    # swept-back wings
    d.polygon([(cx, 20), (cx+40, S-28), (cx+18, S-22), (cx+4, 32)],
              fill=(160, 80, 230, 200))
    d.polygon([(cx, 20), (cx-40, S-28), (cx-18, S-22), (cx-4, 32)],
              fill=(160, 80, 230, 200))
    # Wing edge glow
    d.line([(cx, 20), (cx+40, S-28)], fill=(230, 180, 255, 255), width=2)
    d.line([(cx, 20), (cx-40, S-28)], fill=(230, 180, 255, 255), width=2)
    # Cockpit glowff
    d.ellipse((cx-5, 10, cx+5, 24), fill=(240, 200, 255, 255))
    # Engine exhaust
    d.ellipse((cx-4, S-18, cx+4, S-8), fill=(180, 100, 255, 200))
    tex = arcade.Texture(image=img)
    _texture_cache[key] = tex
    return tex


def _make_titan_texture() -> arcade.Texture:
    """Massive boxy heavy warship for the Titan."""
    key = ("__titan__raw",)
    if key in _texture_cache: return _texture_cache[key]
    S = 96
    img  = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)
    cx   = S // 2
    # Thick armoured hull
    d.rectangle([cx-14, 12, cx+14, S-10], fill=(200, 120, 50, 240))
    # Wide shoulder plates
    d.rectangle([cx-32, 28, cx+32, S-28], fill=(180, 100, 40, 235))
    # Outer armour panels
    d.rectangle([cx-26, 36, cx-14, S-24], fill=(220, 140, 60, 220))
    d.rectangle([cx+14, 36, cx+26, S-24], fill=(220, 140, 60, 220))
    # Cockpit
    d.rectangle([cx-8, 14, cx+8, 32], fill=(255, 210, 100, 255))
    d.ellipse((cx-6, 16, cx+6, 30), fill=(255, 240, 160, 255))
    # Gun barrels left + right
    d.rectangle([cx-30, 30, cx-22, 50], fill=(140, 80, 30, 255))
    d.rectangle([cx+22, 30, cx+30, 50], fill=(140, 80, 30, 255))
    # Hull edge highlights
    d.line([(cx-14, 12), (cx+14, 12)], fill=(255, 200, 100, 200), width=2)
    d.line([(cx-32, 28), (cx+32, 28)], fill=(255, 180, 80, 180), width=2)
    # Engine glow
    d.ellipse((cx-10, S-18, cx+10, S-8), fill=(255, 160, 50, 220))
    tex = arcade.Texture(image=img)
    _texture_cache[key] = tex
    return tex


def load_texture_clean(path: str, scale: float = 1.0) -> arcade.Texture:
    """Load a sprite image, remove the background using flood-fill, and cache it."""
    key = (path, scale)
    if key in _texture_cache:
        return _texture_cache[key]

    # ── Procedural ships ──────────────────────────────
    if path == "__phantom__":
        tex = _make_phantom_texture()
        _texture_cache[key] = tex
        return tex
    if path == "__titan__":
        tex = _make_titan_texture()
        _texture_cache[key] = tex
        return tex

    resolved_path = _resolve_asset_path(path)
    if resolved_path is None:
        tex = _missing_texture(path, scale)
        _texture_cache[key] = tex
        return tex
    img = Image.open(resolved_path).convert("RGBA")
    img = _remove_background(img, threshold=210)
    if scale != 1.0:
        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        img = img.resize((new_w, new_h), _RESAMPLE)
    tex = arcade.Texture(image=img)
    _texture_cache[key] = tex
    return tex


def solid_texture(size: int, color: tuple) -> arcade.Texture:
    key = ("solid", size, color)
    if key in _texture_cache:
        return _texture_cache[key]
    tex = arcade.Texture(image=Image.new("RGBA", (size, size), color))
    _texture_cache[key] = tex
    return tex


def _draw_texture_fitted(texture: arcade.Texture, center_x: float, center_y: float,
                         max_width: float, max_height: float) -> None:
    """Draw a texture scaled to fit inside a bounded box."""
    if texture.width <= 0 or texture.height <= 0:
        return

    scale = min(max_width / texture.width, max_height / texture.height)
    draw_w = max(1, texture.width * scale)
    draw_h = max(1, texture.height * scale)
    try:
        arcade.draw_texture_rect(texture, arcade.XYWH(center_x, center_y, draw_w, draw_h))
    except (AttributeError, TypeError):
        sprite = arcade.Sprite()
        sprite.texture = texture
        sprite.center_x = center_x
        sprite.center_y = center_y
        sprite.scale = scale
        arcade.draw_sprite(sprite)


# ─────────────────────────────────────────────────────
#  POWERUPS
# ─────────────────────────────────────────────────────

POWERUP_TYPES  = ["health", "shield", "speed", "triple", "beam360", "elec360", "breach"]
MAZE_POWERUP_TYPES = list(POWERUP_TYPES)
POWERUP_COLORS = {
    "health":   (0,   255, 90,  220),
    "shield":   (0,   190, 255, 220),
    "speed":    (255, 220, 0,   220),
    "triple":   (255, 130, 0,   220),
    "beam360":  (255, 60,  20,  220),   # fiery orange-red
    "elec360":  (120, 80,  255, 220),   # electric violet
    "breach":   (255, 205, 60,  220),   # maze wall breaker
    "maze_health": (30, 255, 105, 230),  # maze health potion
    "maze_speed":  (255, 215, 35, 230),  # maze speed potion
}
POWERUP_LABELS = {
    "health":  "+HP",   "shield":  "SHIELD",
    "speed":   "SPEED", "triple":  "TRIPLE",  "beam360":  "360°",
    "elec360": "⚡360°", "breach": "BREACH",
    "maze_health": "+HP", "maze_speed": "BLITZ",
}
# Types that only drop when the beam ship is active
BEAM_ONLY_POWERUPS     = {"beam360"}
# Types that only drop when the electric ship is active
ELECTRIC_ONLY_POWERUPS = {"elec360"}
# Maze-only wall breaker. Normal mode excludes it from random drops.
BREACH_ONLY_POWERUPS = {"breach"}


# ─────────────────────────────────────────────────────
#  POWERUP TEXTURES  (procedural, PIL-generated)
# ─────────────────────────────────────────────────────

def _make_powerup_texture(kind: str, maze_style: bool = False) -> arcade.Texture:
    key = ("pu_tex_v3", kind, maze_style)
    if key in _texture_cache:
        return _texture_cache[key]

    S   = 40          # icon canvas size
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx  = S // 2

    col = POWERUP_COLORS.get(kind, (200, 200, 200))
    r, g, b = col[0], col[1], col[2]

    if maze_style and kind not in ("maze_health", "maze_speed"):
        # Maze pickups are crystal cores: brighter, rounder, and easier to read
        # against the dense wall art than the square normal-mode panels.
        for radius, alpha in ((19, 42), (16, 70), (13, 95)):
            d.ellipse((cx - radius, cx - radius, cx + radius, cx + radius),
                      fill=(r, g, b, alpha))
        d.ellipse((4, 4, S - 5, S - 5), outline=(r, g, b, 165), width=2)
        d.ellipse((8, 8, S - 9, S - 9), fill=(10, 14, 30, 230),
                  outline=(min(255, r + 35), min(255, g + 35), min(255, b + 35), 240),
                  width=2)
        d.polygon([(cx, 7), (31, cx), (cx, 33), (9, cx)],
                  fill=(r, g, b, 88),
                  outline=(255, 255, 230, 145))
        d.arc((5, 5, S - 6, S - 6), 205, 335,
              fill=(255, 255, 255, 105), width=2)
        d.arc((8, 8, S - 9, S - 9), 25, 135,
              fill=(255, 255, 255, 70), width=1)

        symbol = (245, 255, 235, 245)
        if kind == "speed":
            pts = [(cx + 4, 8), (cx - 4, 21), (cx + 2, 21),
                   (cx - 4, 33), (cx + 8, 17), (cx + 2, 17)]
            d.polygon(pts, fill=symbol)
        elif kind == "shield":
            d.polygon([(cx, 9), (cx + 11, 14), (cx + 9, 25),
                       (cx, 33), (cx - 9, 25), (cx - 11, 14)],
                      outline=symbol, fill=(r, g, b, 105))
            d.line((cx, 14, cx, 27), fill=symbol, width=2)
        elif kind == "triple":
            for ox in (-8, 0, 8):
                d.rounded_rectangle((cx + ox - 3, 10, cx + ox + 3, 30),
                                    radius=3, fill=symbol)
        elif kind in ("beam360", "elec360"):
            for i in range(10):
                a = math.radians(i * 36)
                x1 = cx + math.cos(a) * 4;   y1 = cx + math.sin(a) * 4
                x2 = cx + math.cos(a) * 14;  y2 = cx + math.sin(a) * 14
                d.line((x1, y1, x2, y2), fill=symbol, width=2)
            d.ellipse((cx - 4, cx - 4, cx + 4, cx + 4), fill=(r, g, b, 255))
        elif kind == "breach":
            d.line((cx - 10, cx, cx + 10, cx), fill=symbol, width=2)
            d.line((cx - 2, 10, cx + 3, cx - 1, cx - 1, cx + 5, cx + 5, 30),
                   fill=symbol, width=2)
        elif kind == "health":
            d.rectangle((cx - 2, 11, cx + 2, 29), fill=symbol)
            d.rectangle((11, cx - 2, 29, cx + 2), fill=symbol)
        d.ellipse((S - 13, 7, S - 8, 12), fill=(255, 255, 255, 150))
        tex = arcade.Texture(image=img)
        _texture_cache[key] = tex
        return tex

    if kind in ("maze_health", "maze_speed"):
        # Maze potions use a bottle silhouette instead of the square pickup panel.
        d.ellipse((0, 0, S - 1, S - 1), fill=(r, g, b, 35))
        d.ellipse((4, 4, S - 5, S - 5), fill=(r, g, b, 62))
        d.rounded_rectangle((17, 4, 23, 12), radius=2, fill=(230, 250, 220, 235))
        d.rounded_rectangle((15, 10, 25, 16), radius=3, fill=(35, 45, 44, 245),
                            outline=(230, 250, 220, 210), width=1)
        d.rounded_rectangle((10, 14, 30, 35), radius=7, fill=(r, g, b, 205),
                            outline=(230, 255, 220, 235), width=2)
        d.rounded_rectangle((13, 17, 27, 32), radius=5, fill=(r, g, b, 92))
        d.line((15, 18, 13, 27), fill=(255, 255, 255, 115), width=2)
        if kind == "maze_speed":
            bolt = [(22, 17), (15, 25), (20, 25), (17, 33), (27, 22), (22, 22)]
            d.polygon(bolt, fill=(255, 255, 185, 255))
        else:
            d.rectangle((18, 19, 22, 31), fill=(225, 255, 225, 245))
            d.rectangle((14, 23, 26, 27), fill=(225, 255, 225, 245))
        d.ellipse((S - 13, 7, S - 8, 12), fill=(255, 255, 255, 105))
        tex = arcade.Texture(image=img)
        _texture_cache[key] = tex
        return tex

    # ── Outer glow ring ──────────────────────────────
    d.ellipse((1, 1, S-2, S-2),    fill=(r, g, b, 35))
    d.ellipse((4, 4, S-5, S-5),    fill=(r, g, b, 55))
    # ── Panel background ─────────────────────────────
    d.rounded_rectangle((5, 5, S-6, S-6), radius=5, fill=(8, 12, 30, 220))
    # ── Coloured border ──────────────────────────────
    d.rounded_rectangle((5, 5, S-6, S-6), radius=5,
                        outline=(r, g, b, 230), width=2)

    # ── Per-type symbol ──────────────────────────────
    if kind == "speed":
        # Lightning bolt
        pts = [(cx+3, 6), (cx-3, cx+1), (cx+2, cx+1), (cx-3, S-6), (cx+3, cx-1), (cx-2, cx-1)]
        d.polygon(pts, fill=(r, g, b, 255))

    elif kind == "shield":
        # Shield silhouette
        sw = 12
        d.polygon([(cx, 8), (cx+sw, 14), (cx+sw, 24), (cx, S-7), (cx-sw, 24), (cx-sw, 14)],
                  fill=(r, g, b, 200))
        d.polygon([(cx, 11), (cx+sw-3, 15), (cx+sw-3, 23), (cx, S-10), (cx-sw+3, 23), (cx-sw+3, 15)],
                  fill=(8, 12, 30, 200))
        # centre cross
        d.rectangle((cx-1, 14, cx+1, 26), fill=(r, g, b, 255))
        d.rectangle((cx-5, 19, cx+5, 21), fill=(r, g, b, 255))

    elif kind == "triple":
        # Three bullets stacked
        for ox in (-9, 0, 9):
            d.rounded_rectangle((cx+ox-3, 9, cx+ox+3, S-9),
                                 radius=3, fill=(r, g, b, 220))

    elif kind in ("beam360", "elec360"):
        # Star burst  — 8 spokes
        for i in range(8):
            a = math.radians(i * 45)
            x1 = cx + math.cos(a) * 5;   y1 = cx + math.sin(a) * 5
            x2 = cx + math.cos(a) * 14;  y2 = cx + math.sin(a) * 14
            d.line((x1, y1, x2, y2), fill=(r, g, b, 240), width=2)
        d.ellipse((cx-4, cx-4, cx+4, cx+4), fill=(r, g, b, 255))

    elif kind == "breach":
        # Cracked charge cell
        d.polygon([(cx, 7), (cx+12, cx), (cx, S-7), (cx-12, cx)],
                  fill=(r, g, b, 210))
        d.line((cx-3, 10, cx+2, cx-1, cx-2, cx+4, cx+4, S-9),
               fill=(8, 12, 30, 235), width=2)
        d.line((cx-9, cx, cx+9, cx), fill=(255, 245, 165, 230), width=1)

    elif kind == "health":
        # Plus / cross
        d.rectangle((cx-2, 10, cx+2, S-11), fill=(r, g, b, 255))
        d.rectangle((10, cx-2, S-11, cx+2), fill=(r, g, b, 255))

    # ── Inner highlight dot ───────────────────────────
    d.ellipse((S-13, 7, S-8, 12), fill=(255, 255, 255, 80))

    tex = arcade.Texture(image=img)
    _texture_cache[key] = tex
    return tex


# Preload all powerup textures at startup so there's no hitch mid-game
def _preload_powerup_textures():
    for k in POWERUP_TYPES:
        _make_powerup_texture(k)
        _make_powerup_texture(k, maze_style=True)
    _make_powerup_texture("maze_health")
    _make_powerup_texture("maze_speed")


# ===== Merged from game_entities.py =====
import arcade
import math
import random

from PIL import Image, ImageDraw


class Powerup(arcade.Sprite):
    def __init__(self, x: float, y: float, kind: str, maze_style: bool = False):
        super().__init__()
        self.texture      = _make_powerup_texture(kind, maze_style=maze_style)
        self.center_x     = x
        self.center_y     = y
        self.kind         = kind
        self.maze_style   = maze_style
        self.change_y     = -POWERUP_FALL_SPEED
        self.wobble_phase = random.uniform(0.0, math.tau)
        self.life         = POWERUP_SCREEN_LIFE   # fade + auto-remove timer
        self.alpha        = 255

    def update(self, delta_time: float = 1/60, *args, **kwargs):
        self.center_y     += self.change_y * delta_time
        self.wobble_phase += 4.0 * delta_time
        self.center_x     += math.sin(self.wobble_phase) * 18.0 * delta_time
        self.life         -= delta_time
        # fade out in the last 1.2 seconds
        if self.life < 1.2:
            self.alpha = max(0, int(255 * (self.life / 1.2)))


# ─────────────────────────────────────────────────────
#  COIN
# ─────────────────────────────────────────────────────

def _make_coin_texture() -> arcade.Texture:
    key = ("coin_tex",)
    if key in _texture_cache:
        return _texture_cache[key]
    img  = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    drw  = ImageDraw.Draw(img)
    drw.ellipse((1, 1, 18, 18), fill=(255, 205, 20, 255), outline=(255, 240, 100, 255), width=2)
    drw.ellipse((5, 5, 14, 14), fill=(255, 230, 80, 180))
    # small $ symbol in centre
    drw.text((7, 4), "$", fill=(200, 140, 0, 220))
    tex = arcade.Texture(image=img)
    _texture_cache[key] = tex
    return tex


class Coin(arcade.Sprite):
    _tex = None

    def __init__(self, x: float, y: float, value: int = 5):
        super().__init__()
        if Coin._tex is None:
            Coin._tex = _make_coin_texture()
        self.texture      = Coin._tex
        self.center_x     = x
        self.center_y     = y
        self.value        = value
        self.change_y     = -POWERUP_FALL_SPEED * 0.65
        self.wobble_phase = random.uniform(0.0, math.tau)
        self.life         = 9.0   # disappears after 9 s if not collected

    def update(self, delta_time: float = 1/60, *args, **kwargs):
        self.center_y     += self.change_y * delta_time
        self.wobble_phase += 3.8  * delta_time
        self.center_x     += math.sin(self.wobble_phase) * 16 * delta_time
        self.life         -= delta_time


# ─────────────────────────────────────────────────────
#  PLAYER   (boundary clamping moved to GameWindow)
# ─────────────────────────────────────────────────────


class Player(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture    = load_texture_clean("image/player.png", 0.15)
        self.center_x   = SCREEN_WIDTH  // 2
        self.center_y   = SCREEN_HEIGHT // 2
        self.health     = PLAYER_HEALTH
        self.max_health = PLAYER_HEALTH
        self.change_x   = 0.0;  self.change_y = 0.0

        self.shield_active   = False;  self.shield_timer   = 0.0
        self.speed_active    = False;  self.speed_timer    = 0.0
        self.triple_active   = False;  self.triple_timer   = 0.0
        self.beam360_active  = False;  self.beam360_timer  = 0.0
        self.elec360_active  = False;  self.elec360_timer  = 0.0
        self.breach_active   = False;  self.breach_timer   = 0.0

        self.inventory = {"speed": 0, "shield": 0, "triple": 0,
                          "beam360": 0, "elec360": 0, "breach": 0}

    def get_speed(self):
        engine = getattr(self, "_engine_bonus", 1.0)
        return PLAYER_SPEED * engine * (1.65 if self.speed_active else 1.0)

    @staticmethod
    def angle_from_motion(vx: float, vy: float) -> float:
        raw = math.degrees(math.atan2(vx, vy))
        return (raw + 180.0) % 360.0 - 180.0

    def update_powerups(self, delta):
        for attr in ("shield", "speed", "triple", "beam360", "elec360", "breach"):
            if getattr(self, f"{attr}_active"):
                new_t = getattr(self, f"{attr}_timer") - delta
                if new_t <= 0:
                    setattr(self, f"{attr}_active", False);  new_t = 0.0
                setattr(self, f"{attr}_timer", new_t)

    def update(self, delta_time=1/60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        if math.hypot(self.change_x, self.change_y) > 4.0:
            target = self.angle_from_motion(self.change_x, self.change_y)
            diff = (target - self.angle + 180.0) % 360.0 - 180.0
            self.angle += diff * min(1.0, 18.0 * delta_time)


# ─────────────────────────────────────────────────────
#  ENEMIES
# ─────────────────────────────────────────────────────


class Enemy(arcade.Sprite):
    def __init__(self, x, y, health=ENEMY_HEALTH):
        super().__init__()
        self.texture    = load_texture_clean("image/enemy.png", 0.12)
        self.center_x   = x;  self.center_y   = y
        self.health     = health;  self.max_health = health


class ShootingEnemy(arcade.Sprite):
    def __init__(self, x, y, health=ENEMY_HEALTH):
        super().__init__()
        self.texture     = load_texture_clean("image/shooting_enemy.png", 0.12)
        self.center_x    = x;  self.center_y  = y
        self.health      = health;  self.max_health = health
        self.shoot_timer = 0.0


class BossEnemy(arcade.Sprite):
    def __init__(self, x, y, health=BOSS_HEALTH,
                 texture_path="image/boss.png", texture_scale=0.2,
                 boss_name="BOSS"):
        super().__init__()
        self.texture       = load_texture_clean(texture_path, texture_scale)
        self.center_x      = x;  self.center_y  = y
        self.health        = health;  self.max_health = health
        self.boss_name     = boss_name
        self.normal_timer  = 0.0;  self.special_timer = 0.0
        self.electric_timer = 0.0
        self.is_final_boss = False


# ─────────────────────────────────────────────────────
#  BULLETS  — drawn with arcade-generated textures
#  (no external image files required)
# ─────────────────────────────────────────────────────

def _make_bullet_texture(size: int, core: tuple, mid: tuple, glow: tuple) -> arcade.Texture:
    """Create a glowing bullet texture using PIL — cached by args."""
    key = ("bullet_tex", size, core, mid, glow)
    if key in _texture_cache:
        return _texture_cache[key]
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx  = size // 2
    # outer soft glow
    d.ellipse((1, 1, size-2, size-2), fill=(*glow[:3], 60))
    # mid ring
    m = size // 4
    d.ellipse((m, m, size-m-1, size-m-1), fill=(*mid[:3], 160))
    # bright core
    c = size // 3
    d.ellipse((c, c, size-c-1, size-c-1), fill=(*core[:3], 255))
    tex = arcade.Texture(image=img)
    _texture_cache[key] = tex
    return tex


# Pre-baked textures (created once at import time after PIL is available)
_PLAYER_BULLET_TEX  = None
_ENEMY_BULLET_TEX   = None


def _get_player_bullet_tex() -> arcade.Texture:
    global _PLAYER_BULLET_TEX
    if _PLAYER_BULLET_TEX is None:
        # Cyan/white glowing energy shot
        _PLAYER_BULLET_TEX = _make_bullet_texture(
            22,
            core=(220, 250, 255),   # bright white-blue core
            mid =(80,  200, 255),   # cyan mid ring
            glow=(30,  120, 255),   # blue outer glow
        )
    return _PLAYER_BULLET_TEX


def _get_enemy_bullet_tex() -> arcade.Texture:
    global _ENEMY_BULLET_TEX
    if _ENEMY_BULLET_TEX is None:
        # Red/orange hostile shot
        _ENEMY_BULLET_TEX = _make_bullet_texture(
            20,
            core=(255, 240, 200),   # hot white core
            mid =(255, 120,  40),   # orange mid ring
            glow=(200,  30,  20),   # deep red glow
        )
    return _ENEMY_BULLET_TEX


class Bullet(arcade.Sprite):
    def __init__(self, sx, sy, angle_rad, speed=BULLET_SPEED):
        super().__init__()
        self.texture  = _get_player_bullet_tex()
        self.center_x = sx;  self.center_y = sy
        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle    = math.degrees(angle_rad) - 90   # nose-forward
        self.life     = 2.5
        self.scale    = 0.85

    def update(self, delta_time=1/60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life     -= delta_time


class EnemyBullet(arcade.Sprite):
    def __init__(self, sx, sy, dest_x=None, dest_y=None,
                 angle_rad=None, speed=ENEMY_BULLET_SPEED):
        super().__init__()
        self.texture  = _get_enemy_bullet_tex()
        self.center_x = sx;  self.center_y = sy
        if angle_rad is None:
            angle_rad = math.atan2(dest_y - sy, dest_x - sx)
        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle    = math.degrees(angle_rad) - 90
        self.life     = 3.4
        self.scale    = 0.80

    def update(self, delta_time=1/60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life     -= delta_time


# ─────────────────────────────────────────────────────
#  BEAM  (beam-weapon ship projectile — not a Sprite)
# ─────────────────────────────────────────────────────

BEAM_DAMAGE_PER_SEC   = 280    # DPS against bosses
BEAM_BOSS_KILL_THRESH = 0      # regular enemies die instantly; boss takes DPS
BEAM_RANGE            = 1400   # max beam length (longer than any screen)
BEAM_DURATION         = 0.12   # seconds a fired beam lives
BEAM_360_ANGLES       = 12     # number of beams in 360° burst


class BeamRay:
    """A single beam ray — rendered as a glowing line, not a sprite."""
    __slots__ = ("ox", "oy", "angle_rad", "length", "life", "max_life", "color")

    def __init__(self, ox: float, oy: float, angle_rad: float,
                 length: float = BEAM_RANGE, life: float = BEAM_DURATION,
                 color: tuple = (255, 100, 40)):
        self.ox        = ox
        self.oy        = oy
        self.angle_rad = angle_rad
        self.length    = length
        self.life      = life
        self.max_life  = life
        self.color     = color

    @property
    def tip_x(self) -> float:
        return self.ox + math.cos(self.angle_rad) * self.length

    @property
    def tip_y(self) -> float:
        return self.oy + math.sin(self.angle_rad) * self.length

    def update(self, delta: float) -> None:
        self.life -= delta

    def draw(self) -> None:
        """Draw a glowing 3-layer beam."""
        ratio = 0.0 if self.max_life <= 0 else max(0.0, min(1.0, self.life / self.max_life))
        cr, cg, cb_ = self.color
        tx, ty = self.tip_x, self.tip_y
        # outer soft glow
        arcade.draw_line(self.ox, self.oy, tx, ty,
                         (cr, cg, cb_, int(55 * ratio)), 12)
        # mid glow
        arcade.draw_line(self.ox, self.oy, tx, ty,
                         (cr, cg, cb_, int(130 * ratio)), 5)
        # bright core
        arcade.draw_line(self.ox, self.oy, tx, ty,
                         (255, 200, 160, int(240 * ratio)), 2)

    def intersects_circle(self, cx: float, cy: float, r: float) -> bool:
        """Check if this ray hits a circle (enemy hitbox)."""
        # Vector from ray origin toward tip
        dx = math.cos(self.angle_rad)
        dy = math.sin(self.angle_rad)
        # Vector from origin to circle centre
        fx = self.ox - cx
        fy = self.oy - cy
        a  = dx*dx + dy*dy
        b  = 2*(fx*dx + fy*dy)
        c  = fx*fx + fy*fy - r*r
        disc = b*b - 4*a*c
        if disc < 0:
            return False
        sq  = math.sqrt(disc)
        t1  = (-b - sq) / (2*a)
        t2  = (-b + sq) / (2*a)
        return (0 <= t1 <= self.length) or (0 <= t2 <= self.length)


# ─────────────────────────────────────────────────────
#  ELECTRIC BOLT  (Reaper ship weapon)
# ─────────────────────────────────────────────────────

ELECTRIC_SPEED        = 820     # px/s
ELECTRIC_DAMAGE       = 35      # damage per bolt hit
ELECTRIC_BOSS_DAMAGE  = 90      # damage to boss per bolt hit
ELECTRIC_BOLT_LIFE    = 1.8     # seconds
ELECTRIC_FIRE_RATE    = 0.14    # seconds between bolts (faster than normal)
ELECTRIC_360_FIRE_RATE = 0.08   # dense storm pulses while 360° mode is active
ELECTRIC_360_COUNT    = 24      # bolts in each 360° storm pulse
ELECTRIC_360_DURATION = 7.0     # how long 360° mode lasts
ELECTRIC_360_RADIUS   = 185     # storm only reaches this far from the ship
ELECTRIC_360_DAMAGE   = 46      # stronger than the normal electric bolt
ELECTRIC_360_BOSS_DAMAGE = 115

FINAL_BOSS_ELECTRIC_RANGE = 230
FINAL_BOSS_ELECTRIC_RADIUS = 245
FINAL_BOSS_ELECTRIC_COUNT = 36
FINAL_BOSS_ELECTRIC_FIRE_RATE = 0.90
FINAL_BOSS_ELECTRIC_DAMAGE = 16


class ElectricBolt(arcade.Sprite):
    """
    A zigzag lightning bolt fired by the Reaper ship.
    Visually drawn as a chain of short jittered segments — re-randomised
    every frame so it flickers like real electricity.
    """

    def __init__(self, sx: float, sy: float, angle_rad: float,
                 speed: float = ELECTRIC_SPEED,
                 damage: int = ELECTRIC_DAMAGE,
                 boss_damage: int = ELECTRIC_BOSS_DAMAGE,
                 max_range: float | None = None):
        super().__init__()
        # Use a tiny 1×1 transparent texture so arcade collision still works
        img = Image.new("RGBA", (6, 6), (0, 0, 0, 0))
        self.texture  = arcade.Texture(image=img)
        self.center_x = sx
        self.center_y = sy
        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle_rad = angle_rad
        self.life      = ELECTRIC_BOLT_LIFE
        self.damage    = damage
        self.boss_damage = boss_damage
        self.max_range = max_range
        self.distance_travelled = 0.0
        # pre-generate zigzag offsets (regenerated each draw for flicker)
        self._segs     = 8     # number of zigzag segments
        self._length   = 28.0  # length of each segment
        self._offsets  = [random.uniform(-5, 5) for _ in range(self._segs)]

    def update(self, delta_time: float = 1/60, *args, **kwargs) -> None:
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life     -= delta_time
        self.distance_travelled += math.hypot(self.change_x, self.change_y) * delta_time
        if self.max_range is not None and self.distance_travelled >= self.max_range:
            self.life = 0.0
        # Re-randomise jitter every frame → flickering effect
        self._offsets = [random.uniform(-6, 6) for _ in range(self._segs)]

    def draw_bolt(self) -> None:
        """Draw a glowing zigzag lightning bolt."""
        ratio = max(0.0, self.life / ELECTRIC_BOLT_LIFE)
        perp  = self.angle_rad + math.pi / 2   # perpendicular direction

        px, py = self.center_x, self.center_y
        for i, off in enumerate(self._offsets):
            nx = px + math.cos(self.angle_rad)*self._length \
                    + math.cos(perp)*off
            ny = py + math.sin(self.angle_rad)*self._length \
                    + math.sin(perp)*off
            # outer soft glow (blue)
            arcade.draw_line(px, py, nx, ny,
                             (80, 80, 255, int(60*ratio)), 8)
            # mid glow (blue-white)
            arcade.draw_line(px, py, nx, ny,
                             (140, 120, 255, int(140*ratio)), 3)
            # bright white core
            arcade.draw_line(px, py, nx, ny,
                             (230, 210, 255, int(245*ratio)), 1)
            px, py = nx, ny


# ═════════════════════════════════════════════════════
#  MAZE GRID  —  recursive-backtracker generator + BFS
# ═════════════════════════════════════════════════════


class MazeGrid:
    """Grid-based maze.  Walls are stored as *open* passages (direction removed)."""
    N, E, S, W = 0, 1, 2, 3
    OPP  = {0: 2, 1: 3, 2: 0, 3: 1}
    DX   = {0: 0, 1:  1, 2:  0, 3: -1}   # col delta per direction
    DY   = {0: 1, 1:  0, 2: -1, 3:  0}   # row delta (Y up = N positive)

    def __init__(self, cols: int, rows: int, seed=None):
        self.cols = cols
        self.rows = rows
        # open_walls[row][col] = set of directions where the wall is removed (passage exists)
        self.open_walls: list[list[set]] = [[set() for _ in range(cols)] for _ in range(rows)]
        # breakable_walls[(col,row,dir)] = current HP for closed internal walls.
        # Canonical dir is always N or E so the same wall is not stored twice.
        self.breakable_walls: dict[tuple[int, int, int], int] = {}
        self.breakable_wall_max_hp = MAZE_BREAKABLE_WALL_HP
        self._generate(seed)

    # ── Iterative recursive-backtracker ───────────────
    def _generate(self, seed=None):
        rng  = random.Random(seed)
        vis  = [[False] * self.cols for _ in range(self.rows)]
        # Start at top-left cell
        start_col, start_row = 0, self.rows - 1
        stack = [(start_col, start_row)]
        vis[start_row][start_col] = True
        while stack:
            col, row = stack[-1]
            neighbours = []
            for d in (self.N, self.E, self.S, self.W):
                nc, nr = col + self.DX[d], row + self.DY[d]
                if 0 <= nc < self.cols and 0 <= nr < self.rows and not vis[nr][nc]:
                    neighbours.append((d, nc, nr))
            if neighbours:
                d, nc, nr = rng.choice(neighbours)
                self.open_walls[row][col].add(d)
                self.open_walls[nr][nc].add(self.OPP[d])
                vis[nr][nc] = True
                stack.append((nc, nr))
            else:
                stack.pop()

    def is_open(self, col: int, row: int, direction: int) -> bool:
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return False
        return direction in self.open_walls[row][col]

    def _wall_key(self, col: int, row: int, direction: int) -> tuple[int, int, int] | None:
        """Return a canonical key for an internal wall, or None for maze borders."""
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None
        nc = col + self.DX[direction]
        nr = row + self.DY[direction]
        if not (0 <= nc < self.cols and 0 <= nr < self.rows):
            return None
        if direction in (self.N, self.E):
            return (col, row, direction)
        return (nc, nr, self.OPP[direction])

    def is_breakable_wall(self, col: int, row: int, direction: int) -> bool:
        key = self._wall_key(col, row, direction)
        return key in self.breakable_walls if key else False

    def wall_hp(self, col: int, row: int, direction: int) -> int:
        key = self._wall_key(col, row, direction)
        return self.breakable_walls.get(key, 0) if key else 0

    def configure_breakable_walls(self, seed=None, chance: float = MAZE_BREAKABLE_WALL_CHANCE,
                                  hp: int = MAZE_BREAKABLE_WALL_HP,
                                  protected_cells: set[tuple[int, int]] | None = None) -> None:
        """Mark only selected closed internal walls as fragile; all others stay permanent."""
        rng = random.Random(seed)
        protected_cells = protected_cells or set()
        self.breakable_walls.clear()
        self.breakable_wall_max_hp = hp

        candidates: list[tuple[int, int, int]] = []
        for row in range(self.rows):
            for col in range(self.cols):
                if (col, row) in protected_cells:
                    continue
                for direction in (self.N, self.E):
                    nc = col + self.DX[direction]
                    nr = row + self.DY[direction]
                    if not (0 <= nc < self.cols and 0 <= nr < self.rows):
                        continue
                    if (nc, nr) in protected_cells or self.is_open(col, row, direction):
                        continue
                    candidates.append((col, row, direction))

        for key in candidates:
            if rng.random() < chance:
                self.breakable_walls[key] = hp

        # Guarantee at least a few readable break targets on tiny/sparse layouts.
        minimum = min(max(4, (self.cols * self.rows) // 22), len(candidates))
        if len(self.breakable_walls) < minimum:
            remaining = [key for key in candidates if key not in self.breakable_walls]
            rng.shuffle(remaining)
            for key in remaining[:minimum - len(self.breakable_walls)]:
                self.breakable_walls[key] = hp

    def carve_passage(self, col: int, row: int, direction: int) -> bool:
        """Force a passage open between a cell and its neighbor."""
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return False
        nc = col + self.DX[direction]
        nr = row + self.DY[direction]
        if not (0 <= nc < self.cols and 0 <= nr < self.rows):
            return False
        self.open_walls[row][col].add(direction)
        self.open_walls[nr][nc].add(self.OPP[direction])
        key = self._wall_key(col, row, direction)
        if key:
            self.breakable_walls.pop(key, None)
        return True

    def damage_wall(self, col: int, row: int, direction: int, amount: int = 1) -> tuple[bool, bool, int]:
        """Damage a fragile wall. Returns (damaged, broken, remaining_hp)."""
        key = self._wall_key(col, row, direction)
        if key not in self.breakable_walls:
            return False, False, 0
        next_hp = self.breakable_walls[key] - amount
        if next_hp <= 0:
            k_col, k_row, k_dir = key
            self.carve_passage(k_col, k_row, k_dir)
            return True, True, 0
        self.breakable_walls[key] = next_hp
        return True, False, next_hp

    def open_start_area(self) -> None:
        """Give the spawn cell more than one opening so the run starts with choices."""
        start_col = 0
        start_row = self.rows - 1

        self.carve_passage(start_col, start_row, self.E)
        self.carve_passage(start_col, start_row, self.S)

        if self.cols > 1 and self.rows > 1:
            self.carve_passage(start_col + 1, start_row, self.S)
            self.carve_passage(start_col, start_row - 1, self.E)

    def bfs(self, sc: int, sr: int, ec: int, er: int) -> list:
        """Return list of (col,row) steps from (sc,sr) to (ec,er), exclusive of start."""
        from collections import deque
        prev: dict = {(sc, sr): None}
        q = deque([(sc, sr)])
        while q:
            col, row = q.popleft()
            if col == ec and row == er:
                path: list = []
                cur = (col, row)
                while prev[cur] is not None:
                    path.append(cur)
                    cur = prev[cur]
                path.reverse()
                return path
            for d in (self.N, self.E, self.S, self.W):
                if self.is_open(col, row, d):
                    nc, nr = col + self.DX[d], row + self.DY[d]
                    if (nc, nr) not in prev:
                        prev[(nc, nr)] = (col, row)
                        q.append((nc, nr))
        return []


# ─────────────────────────────────────────────────────
#  MAZE ENEMY SPRITE
# ─────────────────────────────────────────────────────

class MazeEnemy(arcade.Sprite):
    """Enemy that navigates the maze via BFS toward the player."""

    def __init__(self, col: int, row: int, cell_size: int, ox: float, oy: float,
                 health: int | None = None, split_depth: int = 0):
        super().__init__()
        self.split_depth = max(0, min(split_depth, MAZE_ENEMY_MAX_SPLITS))
        size_mult        = MAZE_ENEMY_SPLIT_SIZE_MULT ** self.split_depth
        self.texture     = load_texture_clean("image/enemy.png", 0.12 * size_mult)
        self.center_x    = ox + (col + 0.5) * cell_size
        self.center_y    = oy + (row + 0.5) * cell_size
        self.maze_col    = col
        self.maze_row    = row
        base_health      = MAZE_ENEMY_HEALTH if health is None else max(1, int(health))
        self.health      = base_health
        self.max_health  = base_health
        self.speed       = (MAZE_ENEMY_SPEED + random.uniform(-10, 10)) * (1.0 + 0.06 * self.split_depth)
        self.path: list  = []
        self.path_timer  = random.uniform(0.0, 0.5)   # stagger first recalc
        self.shoot_timer = random.uniform(1.8, 3.5)

    @staticmethod
    def _angle_from_motion(dx: float, dy: float) -> float:
        return (math.degrees(math.atan2(dx, dy)) + 180.0) % 360.0 - 180.0

    def maze_update_flow(self, delta: float, flow_next: dict,
                         cs: int, ox: float, oy: float) -> None:
        """Move using a shared maze flow map instead of per-enemy BFS."""
        if (self.maze_col, self.maze_row) not in flow_next:
            return

        nc, nr = flow_next[(self.maze_col, self.maze_row)]
        tx = ox + (nc + 0.5) * cs
        ty = oy + (nr + 0.5) * cs
        dx = tx - self.center_x
        dy = ty - self.center_y
        dist = math.hypot(dx, dy)
        if dist < 3:
            self.maze_col, self.maze_row = nc, nr
        elif dist > 0:
            self.center_x += (dx / dist) * self.speed * delta
            self.center_y += (dy / dist) * self.speed * delta
        if dist > 0:
            self.angle = self._angle_from_motion(dx, dy)

    def maze_update(self, delta: float, player_col: int, player_row: int,
                    maze: MazeGrid, cs: int, ox: float, oy: float) -> None:
        # Re-path every ~0.55 s
        self.path_timer -= delta
        if self.path_timer <= 0 or not self.path:
            self.path_timer = 0.55
            self.path = maze.bfs(self.maze_col, self.maze_row, player_col, player_row)

        if not self.path:
            return

        nc, nr = self.path[0]
        tx = ox + (nc + 0.5) * cs
        ty = oy + (nr + 0.5) * cs
        dx = tx - self.center_x
        dy = ty - self.center_y
        dist = math.hypot(dx, dy)
        if dist < 3:
            self.maze_col, self.maze_row = nc, nr
            self.path.pop(0)
        elif dist > 0:
            self.center_x += (dx / dist) * self.speed * delta
            self.center_y += (dy / dist) * self.speed * delta
        if dist > 0:
            self.angle = self._angle_from_motion(dx, dy)


class MazeBoss(arcade.Sprite):
    """Large maze boss that hunts the player after all keys are collected."""

    def __init__(self, col: int, row: int, cell_size: int, ox: float, oy: float,
                 health: int = MAZE_BOSS_HEALTH, split_depth: int = 0):
        super().__init__()
        self.split_depth = split_depth
        size_mult        = MAZE_BOSS_SPLIT_SIZE_MULT ** split_depth
        self.texture     = load_texture_clean(
            MAZE_BOSS_TEXTURE,
            MAZE_BOSS_TEXTURE_SCALE * size_mult,
        )
        self.center_x    = ox + (col + 0.5) * cell_size
        self.center_y    = oy + (row + 0.5) * cell_size
        self.maze_col    = col
        self.maze_row    = row
        self.health      = health
        self.max_health  = health
        self.speed       = PLAYER_SPEED
        self.shoot_timer = 0.45
        self.angle       = 0.0


__all__ = [name for name in globals() if not name.startswith("__")]


# ═════════════════════════════════════════════════════
#  GAME WINDOW
# ═════════════════════════════════════════════════════
