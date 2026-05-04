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
}

# ─────────────────────────────────────────────────────
#  CURRENCY
# ─────────────────────────────────────────────────────

COIN_VALUE_ENEMY    = 5
COIN_VALUE_SHOOTING = 8
COIN_VALUE_BOSS     = 35
COIN_MAGNET_RANGE   = 130   # px — auto-collect radius when Coin Magnet is purchased
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
        (1,  "DAWN PATROL",   "First contact — rookies in the dark",          (80,  220, 130), "AVATAR 2472",      "image/avatar_2472.png",    3.00, 3.50),
        (2,  "NOVA SURGE",    "Faster waves, denser skies",                    (90,  180, 255), "FCDXFW1",          "image/FcdXFW1.png",        0.38, 0.44),
        (3,  "IRON CROSS",    "Shielded interceptors join the fray",           (255, 200,  50), "UVLV4MU",          "image/UvlV4Mu.png",        0.55, 0.72),
        (4,  "CRIMSON TIDE",  "Elite fighters & coordinated fire",             (255, 100,  80), "PLANE 6",          "image/plane6.png",         0.08, 0.10),
        (5,  "SOLAR FLARE",   "Relentless sun-scorched assault",               (255, 165,  40), "WD5NR2U",          "image/wd5Nr2u.png",        0.36, 0.44),
        (6,  "NEBULA RIFT",   "Dense formations & heavy artillery",            (140, 100, 255), "REMADE PLANE",     "image/1-year-later-i-remade-this-plane-its-still-unrealistic-but-v0-3fszatcdqw2e1.webp", 0.15, 0.18),
        (7,  "OBSIDIAN GATE", "Elite guard — precision or death",              (80,  210, 220), "OBSIDIAN REX",     "image/boss.png",           0.20, 0.32),
        (8,  "VOID STORM",    "Maximum aggression — bullets everywhere",       (200, 100, 255), "VOID REAPER",      "image/boss.png",           0.20, 0.32),
        (9,  "SINGULARITY",   "The abyss opens — no mercy",                   (255,  60, 120), "GRAVECROWN",       "image/boss.png",           0.20, 0.32),
        (10, "FINAL HORIZON", "Last stand — the combined fleet arrives",       (255, 220,  80), "OMEGA CORE",       "image/boss.png",           0.20, 0.32),
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
