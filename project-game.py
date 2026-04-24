import arcade
import random
import math
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

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
AUTO_FIRE_ENEMY_THRESHOLD = 5
AUTO_SHIELD_HEALTH_RATIO  = 0.50

POWERUP_KEYS = {
    arcade.key.KEY_1: "speed",
    arcade.key.KEY_2: "shield",
    arcade.key.KEY_3: "autofire",
    arcade.key.KEY_4: "triple",
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

STATE_MENU     = "menu"
STATE_PLAYING  = "playing"
STATE_PAUSED   = "paused"
STATE_GAMEOVER = "gameover"

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
        "texture":   "__phantom__",
        "tex_scale": 1.0,
        "spd_mult":  1.45,
        "hp_mult":   0.65,
    },
    {
        "name":      "TITAN",
        "tagline":   "Heavy destroyer",
        "stat_spd":  1, "stat_atk": 5, "stat_def": 5,
        "color":     (255, 155, 70),
        "available": True,
        "texture":   "__titan__",
        "tex_scale": 1.0,
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
        "tex_scale": 0.18,
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
    # Cockpit glow
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


# ─────────────────────────────────────────────────────
#  POWERUPS
# ─────────────────────────────────────────────────────

POWERUP_TYPES  = ["health", "shield", "autofire", "speed", "triple", "beam360", "elec360"]
POWERUP_COLORS = {
    "health":   (0,   255, 90,  220),
    "shield":   (0,   190, 255, 220),
    "autofire": (255, 70,  255, 220),
    "speed":    (255, 220, 0,   220),
    "triple":   (255, 130, 0,   220),
    "beam360":  (255, 60,  20,  220),   # fiery orange-red
    "elec360":  (120, 80,  255, 220),   # electric violet
}
POWERUP_LABELS = {
    "health":  "+HP",   "shield":  "SHIELD",  "autofire": "AUTO",
    "speed":   "SPEED", "triple":  "TRIPLE",  "beam360":  "360°",
    "elec360": "⚡360°",
}
# Types that only drop when the beam ship is active
BEAM_ONLY_POWERUPS     = {"beam360"}
# Types that only drop when the electric ship is active
ELECTRIC_ONLY_POWERUPS = {"elec360"}


# ─────────────────────────────────────────────────────
#  POWERUP TEXTURES  (procedural, PIL-generated)
# ─────────────────────────────────────────────────────

def _make_powerup_texture(kind: str) -> arcade.Texture:
    key = ("pu_tex_v2", kind)
    if key in _texture_cache:
        return _texture_cache[key]

    S   = 40          # icon canvas size
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx  = S // 2

    col = POWERUP_COLORS.get(kind, (200, 200, 200))
    r, g, b = col[0], col[1], col[2]

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

    elif kind == "autofire":
        # Crosshair
        d.ellipse((cx-10, cx-10, cx+10, cx+10), outline=(r, g, b, 255), width=2)
        d.ellipse((cx-4,  cx-4,  cx+4,  cx+4),  fill=(r, g, b, 255))
        for ox, oy, ex, ey in [(-18,0,-12,0),(12,0,18,0),(0,-18,0,-12),(0,12,0,18)]:
            d.line((cx+ox, cx+oy, cx+ex, cx+ey), fill=(r, g, b, 255), width=2)

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
    _make_powerup_texture("health")


class Powerup(arcade.Sprite):
    def __init__(self, x: float, y: float, kind: str):
        super().__init__()
        self.texture      = _make_powerup_texture(kind)
        self.center_x     = x
        self.center_y     = y
        self.kind         = kind
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
        self.autofire_active = False;  self.autofire_timer = 0.0
        self.speed_active    = False;  self.speed_timer    = 0.0
        self.triple_active   = False;  self.triple_timer   = 0.0
        self.beam360_active  = False;  self.beam360_timer  = 0.0
        self.elec360_active  = False;  self.elec360_timer  = 0.0

        self.inventory = {"speed": 0, "shield": 0, "autofire": 0, "triple": 0,
                          "beam360": 0, "elec360": 0}

    def get_speed(self):
        engine = getattr(self, "_engine_bonus", 1.0)
        return PLAYER_SPEED * engine * (1.65 if self.speed_active else 1.0)

    def update_powerups(self, delta):
        for attr in ("shield", "autofire", "speed", "triple", "beam360", "elec360"):
            if getattr(self, f"{attr}_active"):
                new_t = getattr(self, f"{attr}_timer") - delta
                if new_t <= 0:
                    setattr(self, f"{attr}_active", False);  new_t = 0.0
                setattr(self, f"{attr}_timer", new_t)

    def update(self, delta_time=1/60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.angle = max(-20, min(20, -self.change_x * 0.06))


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
    def __init__(self, x, y, health=BOSS_HEALTH):
        super().__init__()
        self.texture       = load_texture_clean("image/boss.png", 0.2)
        self.center_x      = x;  self.center_y  = y
        self.health        = health;  self.max_health = health
        self.normal_timer  = 0.0;  self.special_timer = 0.0


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
ELECTRIC_360_COUNT    = 16      # bolts in 360° burst
ELECTRIC_360_DURATION = 8.0     # how long 360° mode lasts


class ElectricBolt(arcade.Sprite):
    """
    A zigzag lightning bolt fired by the Reaper ship.
    Visually drawn as a chain of short jittered segments — re-randomised
    every frame so it flickers like real electricity.
    """

    def __init__(self, sx: float, sy: float, angle_rad: float,
                 speed: float = ELECTRIC_SPEED):
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
        # pre-generate zigzag offsets (regenerated each draw for flicker)
        self._segs     = 8     # number of zigzag segments
        self._length   = 28.0  # length of each segment
        self._offsets  = [random.uniform(-5, 5) for _ in range(self._segs)]

    def update(self, delta_time: float = 1/60, *args, **kwargs) -> None:
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life     -= delta_time
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
#  GAME WINDOW
# ═════════════════════════════════════════════════════


def _draw_btn(x, w, y, h, fill, border, text_color, label, font_size):
    font_ui_local = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
    arcade.draw_lrbt_rectangle_filled(x, x + w, y, y + h, fill)
    arcade.draw_lrbt_rectangle_outline(x, x + w, y, y + h, border, 2)
    cx = x + w // 2;  cy = y + h // 2
    sa = min(175, int((text_color[3] if len(text_color)==4 else 255)*0.45))
    arcade.draw_text(label, cx+2, cy-2, (0,0,0,sa), font_size,
                     anchor_x="center", anchor_y="center", bold=True, font_name=font_ui_local)
    arcade.draw_text(label, cx, cy, text_color, font_size,
                     anchor_x="center", anchor_y="center", bold=True, font_name=font_ui_local)


def _notif_color(kind: str) -> tuple:
    return {"speed":(255,220,120),"shield":(110,230,255),
            "autofire":(255,130,255),"triple":(255,180,120),
            "health":(130,255,130)}.get(kind,(255,255,255))


class GameWindow(arcade.Window):

    # ──────────────────────────────────────────────────
    #  INIT
    # ──────────────────────────────────────────────────

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
        arcade.set_background_color(BG_COLOR)
        self.set_mouse_visible(True)

        # pre-warm textures
        for path, sc in [("image/player.png", 0.15), ("image/player.png", 0.22),
                          ("image/interceptor.png", 0.18), ("image/interceptor.png", 0.22),
                          ("image/reaper.png", 0.17), ("image/reaper.png", 0.22),
                          ("image/enemy.png", 0.12), ("image/shooting_enemy.png", 0.12),
                          ("image/boss.png", 0.2), ("image/bullet.png", 0.1),
                          ("image/enemy_bullet.png", 0.1)]:
            try:
                load_texture_clean(path, sc)
            except (FileNotFoundError, OSError):
                pass   # image not yet in place — handled gracefully at runtime
        for k in POWERUP_TYPES:
            solid_texture(22, POWERUP_COLORS[k])

        _preload_powerup_textures()

        # ── UI/menu state ─────────────────────────────
        self.game_state    = STATE_MENU
        self.menu_theme         = "dark"
        self.selected_ship      = 0
        self.selected_difficulty = "medium"   # default
        self._menu_btns:  dict  = {}
        self._ship_cards: dict  = {}
        self._diff_btns:  dict  = {}
        self._shop_btns:  dict  = {}

        # ── Currency / Shop ───────────────────────────
        self.coins:    int  = 0          # total saved coins
        self.run_coins: int = 0          # coins earned this run
        self.upgrades: dict = {item["id"]: 0 for item in SHOP_ITEMS}
        self._load_progress()            # restore coins + upgrades from disk

        # ── HUD text objects  (Futura→Century Gothic→Arial fallback chain) ──
        FONT_UI  = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
        FONT_NUM = ("Courier New", "Menlo", "Monaco", "monospace")
        h = SCREEN_HEIGHT
        self.txt_score   = arcade.Text("SCORE 0", 22, h-28,
                                        (255,255,255,240), 22, bold=True, font_name=FONT_UI)
        self.txt_health  = arcade.Text("100 / 100", 22, h-74,
                                        (200,230,255,210), 11, font_name=FONT_NUM)
        self.txt_active  = arcade.Text("", 22, h-112,
                                        (255,240,100,230), 11, bold=True, font_name=FONT_UI)
        self.txt_inv     = arcade.Text("", 22, h-132,
                                        (160,185,225,200), 10, font_name=FONT_NUM)
        self.txt_notif   = arcade.Text("", SCREEN_WIDTH//2, SCREEN_HEIGHT//2+90,
                                        (255,255,110,255), 26, anchor_x="center",
                                        bold=True, font_name=FONT_UI)
        self.txt_hint    = arcade.Text(
            "WASD · LMB Shoot · 1-4 Power-ups · H HUD · F11 Fullscreen · R Restart · ESC Menu",
            SCREEN_WIDTH//2, 11, (100, 125, 175, 140), 9,
            anchor_x="center", font_name=FONT_UI)
        self.txt_over    = arcade.Text("GAME OVER", SCREEN_WIDTH//2, SCREEN_HEIGHT//2+18,
                                        (255,75,75,255), 56, anchor_x="center",
                                        bold=True, font_name=FONT_UI)
        self.txt_score2  = arcade.Text("SCORE 0",   SCREEN_WIDTH//2, SCREEN_HEIGHT//2-44,
                                        (200,225,255,240), 26, anchor_x="center",
                                        font_name=FONT_NUM)
        self.txt_restart = arcade.Text("PRESS  R  TO  RESTART", SCREEN_WIDTH//2, SCREEN_HEIGHT//2-96,
                                        (140,170,220,200), 16, anchor_x="center",
                                        font_name=FONT_UI)
        self.txt_combo   = arcade.Text("", SCREEN_WIDTH-18, SCREEN_HEIGHT-28,
                                        (255,220,60,235), 20, anchor_x="right",
                                        bold=True, font_name=FONT_UI)
        self.txt_timer   = arcade.Text("", SCREEN_WIDTH-18, SCREEN_HEIGHT-30,
                                        (165,200,255,215), 13, anchor_x="right",
                                        font_name=FONT_NUM)
        # stash font names for dynamic Text objects created later
        self._FONT_UI  = FONT_UI
        self._FONT_NUM = FONT_NUM

        # ── Game object handles ───────────────────────
        self.player = self.player_list = None
        self.enemies = self.shooting_enemies = self.bosses = None
        self.bullets = self.enemy_bullets = self.powerups = None

        # ── Runtime vars ─────────────────────────────
        self.score       = 0
        self.show_hud    = True
        self.up = self.down = self.left_key = self.right_key = False
        self.enemy_spawn = self.shooting_spawn = self.boss_spawn = 0.0
        self.mouse_held  = False
        self.mouse_x     = SCREEN_WIDTH  // 2
        self.mouse_y     = SCREEN_HEIGHT // 2
        self.fire_timer  = 0.0
        self.notif_text  = ""
        self.notif_timer = 0.0
        self.notif_color = (255, 255, 110)
        self.bg_time     = 0.0
        self.stars: list  = []
        self.particles: list = []
        self.damage_flash         = 0.0
        self.contact_damage_timer = 0.0
        self.time_alive  = 0.0
        self.combo       = 0
        self.combo_timer = 0.0
        self._fullscreen = False
        self.boss_on_screen = False
        self._dpreset = DIFFICULTY_PRESETS[self.selected_difficulty]
        self.beams: list = []          # active BeamRay objects (Interceptor)
        self.elec_bolts = arcade.SpriteList()  # active ElectricBolt sprites (Reaper)

        self._build_starfield()

    # ──────────────────────────────────────────────────
    #  RESIZE
    # ──────────────────────────────────────────────────

    def on_resize(self, width, height):
        super().on_resize(width, height)
        w, h = width, height
        self.txt_score.x   = 22;      self.txt_score.y   = h-28
        self.txt_health.x  = 22;      self.txt_health.y  = h-62   # numbers row (drawn via shadow)
        self.txt_active.x  = 22;      self.txt_active.y  = h-108
        self.txt_inv.x     = 22;      self.txt_inv.y     = h-142
        self.txt_notif.x   = w//2;    self.txt_notif.y   = h//2+90
        self.txt_hint.x    = w//2;    self.txt_hint.y    = 11
        self.txt_over.x    = w//2;    self.txt_over.y    = h//2+18
        self.txt_score2.x  = w//2;    self.txt_score2.y  = h//2-44
        self.txt_restart.x = w//2;    self.txt_restart.y = h//2-96
        self.txt_combo.x   = w-18;    self.txt_combo.y   = h-28
        self.txt_timer.x   = w-18;    self.txt_timer.y   = h-30
        self._build_starfield()

    # ──────────────────────────────────────────────────
    #  SETUP  (resets and starts a game)
    # ──────────────────────────────────────────────────

    def setup(self):
        ship = SHIPS[self.selected_ship]

        # ── Apply shop upgrades ────────────────────────
        armor_tier  = self.upgrades.get("armor",   0)
        engine_tier = self.upgrades.get("engine",  0)

        self.player           = Player()
        self.player.center_x  = self.width  // 2
        self.player.center_y  = self.height // 2
        base_hp = int(PLAYER_HEALTH * ship["hp_mult"]) + armor_tier * 25
        self.player.max_health = base_hp
        self.player.health     = base_hp
        # Apply the selected ship's texture (Player.__init__ defaults to player.png)
        if ship["texture"]:
            self.player.texture = load_texture_clean(ship["texture"], ship["tex_scale"])
        # Speed multiplier from Engine Tuner
        self.player._engine_bonus = 1.0 + engine_tier * 0.12

        # Starter Shield upgrade — give 1 free shield at run start
        if self.upgrades.get("starter_shield", 0) >= 1:
            self.player.inventory["shield"] = 1

        self.player_list       = arcade.SpriteList()
        self.player_list.append(self.player)

        self.enemies          = arcade.SpriteList()
        self.shooting_enemies = arcade.SpriteList()
        self.bosses           = arcade.SpriteList()
        self.bullets          = arcade.SpriteList()
        self.enemy_bullets    = arcade.SpriteList()
        self.powerups         = arcade.SpriteList()
        self.coins_list       = arcade.SpriteList()   # ← coin sprites on screen

        self.run_coins = 0   # reset per-run coin counter

        self.score       = 0
        self.show_hud    = True
        self.enemy_spawn = self.shooting_spawn = self.boss_spawn = 0.0
        self.mouse_held  = False;  self.fire_timer = 0.0
        self.notif_text  = "";  self.notif_timer = 0.0
        self.notif_color = (255,255,110)
        self.up = self.down = self.left_key = self.right_key = False
        self.damage_flash = 0.0;  self.contact_damage_timer = 0.0
        self.time_alive   = 0.0
        self.combo        = 0;  self.combo_timer = 0.0
        self.particles    = []
        self.beams        = []
        self.elec_bolts   = arcade.SpriteList()
        self.boss_on_screen = False   # lockout flag: True while any boss lives

        # Cache the active preset so AI code can read it cheaply
        self._dpreset = DIFFICULTY_PRESETS[self.selected_difficulty]

        self.game_state = STATE_PLAYING
        self.set_mouse_visible(False)

    # ──────────────────────────────────────────────────
    #  STARFIELD / PARTICLES
    # ──────────────────────────────────────────────────

    def _build_starfield(self):
        w, h = self.width, self.height
        self.stars = []
        for _ in range(STAR_COUNT):
            layer = random.randint(1, 3)
            self.stars.append({
                "x": random.uniform(0, w), "y": random.uniform(0, h),
                "size":    random.uniform(0.8, 2.3)*(0.85+layer*0.2),
                "speed":   random.uniform(18, 52)*layer,
                "alpha":   random.randint(80, 220),
                "phase":   random.uniform(0, math.tau),
                "twinkle": random.uniform(1.2, 3.4),
            })

    def _add_particle(self, x, y, vx, vy, size, life, color, drag):
        if len(self.particles) >= MAX_PARTICLES:
            return
        self.particles.append({"x":x,"y":y,"vx":vx,"vy":vy,
                                "size":size,"life":life,"max_life":life,
                                "color":color,"drag":drag})

    def _burst(self, x, y, n, color, smin, smax,
               zmin=1.5, zmax=3.6, lmin=0.2, lmax=0.5, drag=0.93):
        for _ in range(n):
            a = random.uniform(0, math.tau);  s = random.uniform(smin, smax)
            self._add_particle(x, y, math.cos(a)*s, math.sin(a)*s,
                                random.uniform(zmin,zmax), random.uniform(lmin,lmax),
                                color, drag)

    def _spawn_muzzle(self, x, y, ar):
        for _ in range(4):
            off = random.uniform(-0.25, 0.25);  spd = random.uniform(120, 280)
            self._add_particle(
                x+math.cos(ar)*random.uniform(6,14), y+math.sin(ar)*random.uniform(6,14),
                math.cos(ar+off)*spd, math.sin(ar+off)*spd,
                random.uniform(1.4,2.4), random.uniform(0.08,0.18), (255,220,120), 0.88)

    def _update_starfield(self, delta):
        w, h = self.width, self.height
        flow = 1.0+min(0.9, self.time_alive/80.0)
        for s in self.stars:
            s["y"] -= s["speed"]*flow*delta
            if s["y"] < -6:
                s["y"] = h+random.uniform(4,60);  s["x"] = random.uniform(0,w)

    def _update_particles(self, delta):
        alive = []
        for pt in self.particles:
            pt["life"] -= delta
            if pt["life"] <= 0: continue
            pt["x"] += pt["vx"]*delta;  pt["y"] += pt["vy"]*delta
            pt["vx"] *= pt["drag"];     pt["vy"] *= pt["drag"]
            alive.append(pt)
        self.particles = alive

    # ══════════════════════════════════════════════════
    #  MENU DRAWING
    # ══════════════════════════════════════════════════

    def _is_hovering(self, l, r, b, t):
        return l <= self.mouse_x <= r and b <= self.mouse_y <= t

    @staticmethod
    def _draw_stat_pips(cx: int, y: int, value: int, max_v: int,
                        c_on: tuple, c_off: tuple) -> None:
        spacing = 18   # was 14 — wider spacing between pips
        total   = spacing * (max_v - 1)
        sx      = cx - total // 2
        for i in range(max_v):
            color = c_on if i < value else c_off
            # filled pips get a bigger radius + inner bright dot
            if i < value:
                arcade.draw_circle_filled(sx + i*spacing, y, 7, color)
                bright = tuple(min(255, c + 90) for c in color[:3])
                arcade.draw_circle_filled(sx + i*spacing, y, 3, (*bright, 200))
            else:
                arcade.draw_circle_filled(sx + i*spacing, y, 6, color)
                arcade.draw_circle_outline(sx + i*spacing, y, 6,
                                           (*color[:3], 120), 1)

    def _draw_menu(self):
        is_pause = (self.game_state == STATE_PAUSED)
        # Pause overlay always uses the dark theme for a clean dark panel look.
        # Only the main menu respects the user's light/dark preference.
        theme_c  = THEMES["dark"] if is_pause else THEMES[self.menu_theme]
        w, h = self.width, self.height
        t  = self.bg_time

        # ── Background ───────────────────────────────
        if is_pause:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (2, 5, 16, 170))
        else:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, theme_c["bg"])
            if self.menu_theme == "dark":
                p = (math.sin(t*0.65)+1)*0.5
                arcade.draw_circle_filled(w*0.13,h*0.88,228+18*p,     (38,80,185,42))
                arcade.draw_circle_filled(w*0.87,h*0.20,265+28*(1-p), (145,40,165,36))
                arcade.draw_circle_filled(w*0.52,h*1.06,268,           (28,155,195,20))
                off = (t*14)%28
                for yi in range(-30, h+30, 28):
                    arcade.draw_line(0,yi+off,w,yi+off-18,(28,44,76,24),1)
                for s in self.stars:
                    tw = 0.55+0.45*math.sin(t*s["twinkle"]+s["phase"])
                    al = max(20,min(255,int(s["alpha"]*tw)))
                    arcade.draw_circle_filled(s["x"],s["y"],s["size"],(200,222,255,al))
            else:
                for i in range(7):
                    ang = t*0.28+i*math.tau/7
                    rx = w*0.5+math.cos(ang)*w*0.40
                    ry = h*0.5+math.sin(ang*0.62)*h*0.36
                    arcade.draw_circle_filled(rx,ry,88+22*math.sin(t*0.9+i),(255,255,255,24))
                off = (t*12)%26
                for yi in range(-30,h+30,26):
                    arcade.draw_line(0,yi+off,w,yi+off-14,(155,182,228,20),1)

        # ── Panel ────────────────────────────────────
        pw = min(int(w*0.88), 820)   # wider panel — 5 ship cards need room
        ph = min(int(h*0.95), 580 if is_pause else 560)
        pl = (w-pw)//2;  pr = pl+pw
        pb = (h-ph)//2;  ptop = pb+ph

        arcade.draw_lrbt_rectangle_filled(pl+7,pr+7,pb-7,ptop-7,(0,0,0,70))
        arcade.draw_lrbt_rectangle_filled(pl,pr,pb,ptop, theme_c["panel_fill"])
        arcade.draw_lrbt_rectangle_outline(pl,pr,pb,ptop, theme_c["panel_border"], 2)
        arcade.draw_lrbt_rectangle_outline(pl+5,pr-5,pb+5,ptop-5, theme_c["panel_inner"], 1)

        # corner accents
        ac = theme_c["panel_border"];  sz = 24
        for (ax,ay,dx,dy) in [(pl,pb,-1,-1),(pr,pb,1,-1),(pl,ptop,-1,1),(pr,ptop,1,1)]:
            arcade.draw_line(ax,ay,ax+dx*sz,ay,          ac,2)
            arcade.draw_line(ax,ay,ax,      ay+dy*sz,    ac,2)

        # ── Title ────────────────────────────────────
        font_ui_local = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
        title = "PAUSED" if is_pause else "NEON  DRIFT"
        ty    = ptop - 52
        arcade.draw_text(title, w//2+4, ty-4, theme_c["title_shadow"], 42,
                         anchor_x="center", bold=True, font_name=font_ui_local)
        arcade.draw_text(title, w//2,   ty,   theme_c["title"],        42,
                         anchor_x="center", bold=True, font_name=font_ui_local)
        sub = "GAME SUSPENDED" if is_pause else "S P A C E   S H O O T E R"
        arcade.draw_text(sub, w//2+1, ty-31, (0,0,0,80), 12,
                         anchor_x="center", font_name=font_ui_local)
        arcade.draw_text(sub, w//2, ty-30, theme_c["subtitle"], 12,
                         anchor_x="center", font_name=font_ui_local)

        div_y = ptop - 97
        arcade.draw_line(pl+22, div_y, pr-22, div_y, theme_c["divider"], 1)
        arcade.draw_text("SELECT YOUR SHIP", w//2+1, div_y-23, (0,0,0,90), 13,
                         anchor_x="center", bold=True, font_name=font_ui_local)
        arcade.draw_text("SELECT YOUR SHIP", w//2, div_y-22,
                         theme_c["text"], 13, anchor_x="center", bold=True, font_name=font_ui_local)

        # ── Ship cards ───────────────────────────────
        n   = len(SHIPS)
        gap = 14
        # Dynamic card width: fill panel interior (22px margin each side) exactly
        panel_inner_w = pw - 44
        cw = (panel_inner_w - gap * (n - 1)) // n
        ch  = min(210, int(cw * 1.22))   # keep aspect ratio proportional
        total_cw = cw * n + gap * (n - 1)
        cx0  = pl + 22                   # start at panel left margin
        cy0  = div_y - 54 - ch           # card bottom y

        self._ship_cards = {}
        for i, ship in enumerate(SHIPS):
            cl  = cx0+i*(cw+gap);  cr = cl+cw
            cb  = cy0;             ct = cy0+ch
            sel = (i == self.selected_ship)
            avl = ship["available"]
            hov = self._is_hovering(cl,cr,cb,ct)

            if not avl:
                fill = theme_c["locked_fill"];  bord = theme_c["locked_border"];  bthk = 1
            elif sel:
                fill = theme_c["card_sel_fill"]; bord = theme_c["card_sel_border"]; bthk = 3
            elif hov:
                fill = theme_c["card_hover_fill"]; bord = theme_c["card_border"]; bthk = 2
            else:
                fill = theme_c["card_fill"]; bord = theme_c["card_border"]; bthk = 1

            arcade.draw_lrbt_rectangle_filled(cl,cr,cb,ct, fill)
            arcade.draw_lrbt_rectangle_outline(cl,cr,cb,ct, bord, bthk)

            # selection pulse
            if sel and avl:
                pulse = 0.5+0.5*math.sin(t*4.5)
                g = ship["color"]
                arcade.draw_lrbt_rectangle_outline(
                    cl-3,cr+3,cb-3,ct+3, (*g,int(55+50*pulse)), 2)

            # ship preview — centred in top 48% of card (above text zone at 52%)
            pcx = cl + cw//2
            pcy = cb + int(ch * 0.76)   # 76% up from bottom = centre of top 48%

            if avl and ship["texture"]:
                tex  = load_texture_clean(ship["texture"], ship["tex_scale"])
                draw_y = pcy + (math.sin(t*2.8)*4 if sel else 0)
                # draw_texture_rect works across arcade versions; fall back to SpriteList if needed
                try:
                    arcade.draw_texture_rect(
                        tex,
                        arcade.XYWH(pcx, draw_y, tex.width, tex.height)
                    )
                except (AttributeError, TypeError):
                    # Older arcade versions don't have draw_texture_rect — use SpriteList
                    _sl = arcade.SpriteList()
                    _sp = arcade.Sprite()
                    _sp.texture  = tex
                    _sp.center_x = pcx
                    _sp.center_y = draw_y
                    _sl.append(_sp)
                    _sl.draw()
                arcade.draw_circle_filled(pcx, pcy, 30,
                                          (*ship["color"], 35+int(20*math.sin(t*3))))
            else:
                arcade.draw_circle_outline(pcx,pcy,28, theme_c["locked_border"],2)
                arcade.draw_text("?", pcx, pcy, theme_c["locked_text"], 28,
                                 anchor_x="center", anchor_y="center", bold=True,
                                 font_name=("Futura","Century Gothic","Arial"))

            # ── Ship name / stats — proportional layout ──
            # All Y positions relative to ch so they scale with card height.
            # Text zone = bottom 52% of card; preview zone = top 48%.
            # Gap of at least 8px kept between preview bottom and name top.
            badge_y  = cb + int(ch * 0.04)
            def_y    = cb + int(ch * 0.14)
            atk_y    = cb + int(ch * 0.24)
            spd_y    = cb + int(ch * 0.34)
            tag_y    = cb + int(ch * 0.43)
            name_y   = cb + int(ch * 0.52)

            # scale font size with card width so text doesn't overflow
            fname_sz = max(8, min(12, cw // 13))
            ftag_sz  = max(7, min(10, cw // 16))
            fstat_sz = max(7, min(10, cw // 16))

            nc = theme_c["locked_text"] if not avl else \
                 (theme_c["card_sel_border"] if sel else theme_c["text"])
            # name shadow + main
            arcade.draw_text(ship["name"], pcx+1, name_y-1, (0,0,0,100), fname_sz,
                             anchor_x="center", bold=True,
                             font_name=("Futura","Century Gothic","Arial"))
            arcade.draw_text(ship["name"], pcx, name_y, nc, fname_sz,
                             anchor_x="center", bold=True,
                             font_name=("Futura","Century Gothic","Arial"))

            if avl:
                # tagline
                arcade.draw_text(ship["tagline"], pcx, tag_y,
                                 theme_c["text_dim"], ftag_sz, anchor_x="center",
                                 font_name=("Futura","Century Gothic","Arial"))

                # thin divider between tagline and stats
                arcade.draw_line(cl+8, tag_y-6, cr-8, tag_y-6,
                                 (*theme_c["divider"][:3], 80), 1)

                # stat rows — SPD / ATK / DEF
                pip_x = cl + int(cw * 0.42)   # pips start at 42% of card width
                for row_y, lbl, val in [(spd_y, "SPD", ship["stat_spd"]),
                                         (atk_y, "ATK", ship["stat_atk"]),
                                         (def_y, "DEF", ship["stat_def"])]:
                    arcade.draw_text(lbl, cl+6, row_y, theme_c["text_dim"], fstat_sz,
                                     anchor_y="center", bold=True,
                                     font_name=("Courier New","Menlo","monospace"))
                    self._draw_stat_pips(pip_x, row_y, val, 5,
                                         theme_c["stat_filled"], theme_c["stat_empty"])

                # SELECTED badge
                if sel:
                    arcade.draw_text("✔ SELECTED", pcx, badge_y,
                                     theme_c["selected_badge"], fstat_sz,
                                     anchor_x="center", bold=True,
                                     font_name=("Futura","Century Gothic","Arial"))
            else:
                arcade.draw_text("COMING SOON", pcx, tag_y,
                                 theme_c["locked_text"], ftag_sz, anchor_x="center",
                                 font_name=("Futura","Century Gothic","Arial"))

            self._ship_cards[i] = (cl, cr, cb, ct)

        # ── Buttons ──────────────────────────────────
        self._menu_btns = {}
        self._diff_btns = {}
        btn_top = cy0 - 12

        # ── Difficulty selector ──────────────────────
        arcade.draw_text("SELECT DIFFICULTY", w//2+1, btn_top-3, (0,0,0,90), 12,
                         anchor_x="center", bold=True, font_name=font_ui_local)
        arcade.draw_text("SELECT DIFFICULTY", w//2, btn_top-2,
                         theme_c["text"], 12, anchor_x="center", bold=True, font_name=font_ui_local)

        dw, dh = 118, 38
        dgap   = 10
        dtotal = dw*3 + dgap*2
        dx0    = (w - dtotal)//2
        diff_by = btn_top - dh - 20   # bottom y of difficulty buttons

        for di, dkey in enumerate(DIFFICULTY_ORDER):
            preset = DIFFICULTY_PRESETS[dkey]
            dleft  = dx0 + di*(dw+dgap)
            dright = dleft + dw
            dtop   = diff_by + dh
            sel_d  = (dkey == self.selected_difficulty)
            hov_d  = self._is_hovering(dleft, dright, diff_by, dtop)

            dc     = preset["color"]
            if sel_d:
                fill   = (*dc, 210)
                border = (*dc, 255)
                bthk   = 3
                tcolor = (255, 255, 255)
            elif hov_d:
                fill   = (*dc[:3], 80)
                border = (*dc, 200)
                bthk   = 2
                tcolor = (255, 255, 255)
            else:
                fill   = (*dc[:3], 30)
                border = (*dc[:3], 110)
                bthk   = 1
                tcolor = (*dc[:3], 200)

            arcade.draw_lrbt_rectangle_filled(dleft, dright, diff_by, dtop, fill)
            arcade.draw_lrbt_rectangle_outline(dleft, dright, diff_by, dtop, border, bthk)
            if sel_d:
                pulse = 0.5+0.5*math.sin(t*4.0)
                arcade.draw_lrbt_rectangle_outline(
                    dleft-3, dright+3, diff_by-3, dtop+3, (*dc, int(50+45*pulse)), 2)
            sa_ = min(175, int((tcolor[3] if len(tcolor)==4 else 255)*0.4))
            arcade.draw_text(preset["label"], dleft+dw//2+1, diff_by+dh//2-1,
                             (0,0,0,sa_), 14, anchor_x="center", anchor_y="center",
                             bold=True, font_name=font_ui_local)
            arcade.draw_text(preset["label"], dleft+dw//2, diff_by+dh//2,
                             tcolor, 14, anchor_x="center", anchor_y="center",
                             bold=True, font_name=font_ui_local)

            self._diff_btns[dkey] = (dleft, dright, diff_by, dtop)

        play_y = diff_by - 14   # play button sits below difficulty row

        bw, bh = 230, 50
        bx = w//2-bw//2;  by = play_y - bh
        hov_p = self._is_hovering(bx, bx+bw, by, by+bh)
        _draw_btn(bx, bw, by, bh,
                  theme_c["btn_hover"] if hov_p else theme_c["btn_fill"],
                  theme_c["btn_border"], theme_c["btn_text"],
                  "[ RESUME ]" if is_pause else "[ PLAY GAME ]", 20)
        self._menu_btns["play"] = (bx, bx+bw, by, by+bh)

        # ── Shop button (main menu only) ─────────────
        if not is_pause:
            sw, sh2 = 230, 38
            sx2 = w//2 - sw//2;  sy2 = by - sh2 - 8
            hov_s = self._is_hovering(sx2, sx2+sw, sy2, sy2+sh2)
            coin_label = f"[ SHOP ]  $ {self.coins:,}"
            _draw_btn(sx2, sw, sy2, sh2,
                      theme_c["btn_hover"] if hov_s else (*theme_c["btn_fill"][:3], 200),
                      (255, 210, 30, 220), (255, 215, 40, 255),
                      coin_label, 14)
            self._menu_btns["shop"] = (sx2, sx2+sw, sy2, sy2+sh2)
            _theme_ref_y = sy2
        else:
            qw, qh = 196, 40
            qx = w//2-qw//2;  qy = by-qh-10
            hov_q = self._is_hovering(qx, qx+qw, qy, qy+qh)
            _draw_btn(qx, qw, qy, qh,
                      theme_c["btn_hover"] if hov_q else (*theme_c["btn_fill"][:3], 145),
                      (*theme_c["btn_border"][:3], 152), theme_c["btn_text_dim"],
                      "QUIT TO MENU", 14)
            self._menu_btns["quit"] = (qx, qx+qw, qy, qy+qh)
            _theme_ref_y = qy

        # theme toggle — always a fixed gap below the lowest action button
        tw, th2 = 190, 32
        tx  = w//2 - tw//2
        ty2 = max(pb + 10, _theme_ref_y - th2 - 12)
        hov_t = self._is_hovering(tx, tx+tw, ty2, ty2+th2)
        _draw_btn(tx, tw, ty2, th2,
                  theme_c["btn_hover"] if hov_t else (*theme_c["btn_fill"][:3], 145),
                  (*theme_c["btn_border"][:3], 158),
                  theme_c["toggle_text"],
                  "[ LIGHT MODE ]" if self.menu_theme=="dark" else "[ DARK MODE ]",
                  12)
        self._menu_btns["theme"] = (tx, tx+tw, ty2, ty2+th2)

    # ══════════════════════════════════════════════════
    #  SHOP DRAWING
    # ══════════════════════════════════════════════════

    def _draw_shop(self):
        w, h   = self.width, self.height
        tc     = THEMES["dark"]
        font_u = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
        font_n = ("Courier New", "Menlo", "Monaco", "monospace")

        # Background
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, tc["bg"])
        # Subtle animated lines
        t = self.bg_time
        off = (t * 14) % 28
        for yi in range(-30, h+30, 28):
            arcade.draw_line(0, yi+off, w, yi+off-18, (28,44,76,24), 1)

        # Panel
        pw = min(int(w * 0.90), 760);  ph = min(int(h * 0.92), 560)
        pl = (w-pw)//2;  pr = pl+pw
        pb = (h-ph)//2;  ptop = pb+ph

        arcade.draw_lrbt_rectangle_filled(pl+7, pr+7, pb-7, ptop-7, (0,0,0,70))
        arcade.draw_lrbt_rectangle_filled(pl, pr, pb, ptop, tc["panel_fill"])
        arcade.draw_lrbt_rectangle_outline(pl, pr, pb, ptop, tc["panel_border"], 2)
        arcade.draw_lrbt_rectangle_outline(pl+5, pr-5, pb+5, ptop-5, tc["panel_inner"], 1)

        # Title
        ty_title = ptop - 48
        arcade.draw_text("SHOP", w//2+3, ty_title-3, tc["title_shadow"], 38,
                         anchor_x="center", bold=True, font_name=font_u)
        arcade.draw_text("SHOP", w//2, ty_title, tc["title"], 38,
                         anchor_x="center", bold=True, font_name=font_u)
        # Coin balance
        bal_str = f"$ {self.coins:,}  coins"
        arcade.draw_text(bal_str, w//2, ty_title-30,
                         (255, 220, 40, 245), 14, anchor_x="center",
                         bold=True, font_name=font_n)

        div_y = ptop - 88
        arcade.draw_line(pl+22, div_y, pr-22, div_y, tc["divider"], 1)

        # ── Item grid ────────────────────────────────
        n        = len(SHOP_ITEMS)
        cols     = 3
        rows     = (n + cols - 1) // cols
        cw_      = (pw - 60) // cols
        ch_      = 148
        gap_     = 14
        grid_top = div_y - 18
        self._shop_btns = {}

        for idx, item in enumerate(SHOP_ITEMS):
            col = idx % cols;  row = idx // cols
            cl  = pl + 30 + col * (cw_ + gap_)
            ct  = grid_top - row * (ch_ + gap_)
            cr  = cl + cw_;  cb_ = ct - ch_
            tier = self.upgrades.get(item["id"], 0)
            maxed = (tier >= item["max"])
            cost  = item["cost"][tier] if not maxed else 0
            can_afford = (self.coins >= cost) and not maxed
            ic    = item["color"]

            # Card background
            if maxed:
                fill_c  = (20, 40, 20, 200)
                bord_c  = (60, 160, 60, 180)
            elif can_afford:
                hov = self._is_hovering(cl, cr, cb_, ct)
                fill_c  = (*ic[:3], 35) if not hov else (*ic[:3], 60)
                bord_c  = (*ic[:3], 200)
            else:
                fill_c  = (14, 16, 38, 180)
                bord_c  = (38, 44, 74, 120)

            arcade.draw_lrbt_rectangle_filled(cl, cr, cb_, ct, fill_c)
            arcade.draw_lrbt_rectangle_outline(cl, cr, cb_, ct, bord_c, 2)

            # Icon badge
            icon_x = cl + 20;  icon_y = ct - 28
            ic_alpha = 255 if (can_afford or maxed) else 110
            arcade.draw_lrbt_rectangle_filled(icon_x-2, icon_x+38, icon_y-18, icon_y+4,
                                               (*ic[:3], 60 if can_afford else 30))
            arcade.draw_text(item["icon"], icon_x, icon_y-14,
                             (*ic[:3], ic_alpha), 14, bold=True, font_name=font_u)

            # Name
            nc = (*ic[:3], 240) if (can_afford or maxed) else (80, 90, 120, 180)
            arcade.draw_text(item["name"], cl + cw_//2, ct - 22,
                             nc, 11, anchor_x="center", bold=True, font_name=font_u)
            # Desc
            arcade.draw_text(item["desc"], cl + cw_//2, ct - 42,
                             (160, 180, 215, 180), 9, anchor_x="center", font_name=font_u)

            # Tier dots
            dot_y  = ct - 60
            dot_cx = cl + cw_//2
            dot_sp = 14
            dot_total = item["max"] * dot_sp
            dot_sx = dot_cx - dot_total//2
            for d in range(item["max"]):
                dc = (*ic[:3], 240) if d < tier else (40, 50, 75, 200)
                arcade.draw_circle_filled(dot_sx + d*dot_sp, dot_y, 5, dc)
                if d < tier:
                    arcade.draw_circle_filled(dot_sx + d*dot_sp, dot_y, 2,
                                              (255, 255, 255, 180))

            # Buy / maxed label
            btn_y = cb_ + 10
            if maxed:
                arcade.draw_text("✔ MAXED", cl + cw_//2, btn_y + 4,
                                 (80, 220, 100, 230), 10, anchor_x="center",
                                 bold=True, font_name=font_u)
            else:
                cost_c = (255, 220, 40, 240) if can_afford else (130, 140, 160, 160)
                arcade.draw_text(f"$ {cost}  coins", cl + cw_//2, btn_y + 4,
                                 cost_c, 11, anchor_x="center",
                                 bold=True, font_name=font_n)

            if not maxed:
                self._shop_btns[item["id"]] = (cl, cr, cb_, ct)

        # ── Back button ─────────────────────────────
        bkw, bkh = 160, 38
        bkx = w//2 - bkw//2
        bky = pb + 12
        hov_bk = self._is_hovering(bkx, bkx+bkw, bky, bky+bkh)
        _draw_btn(bkx, bkw, bky, bkh,
                  tc["btn_hover"] if hov_bk else (*tc["btn_fill"][:3], 180),
                  tc["btn_border"], tc["btn_text"], "[ BACK ]", 14)
        self._shop_btns["__back__"] = (bkx, bkx+bkw, bky, bky+bkh)

    # ══════════════════════════════════════════════════
    #  GAME-WORLD DRAW HELPERS
    # ══════════════════════════════════════════════════

    def _draw_bg_space(self):
        w, h  = self.width, self.height
        tc    = THEMES[self.menu_theme]   # active theme colors
        pulse = (math.sin(self.bg_time*0.7)+1)*0.5

        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, tc["world_bg"])
        arcade.draw_circle_filled(w*0.19, h*0.83, 250+20*pulse,       tc["nebula1"])
        arcade.draw_circle_filled(w*0.84, h*0.28, 280+30*(1.0-pulse), tc["nebula2"])
        arcade.draw_circle_filled(w*0.53, h*1.07, 280,                tc["nebula3"])

        off = (self.bg_time*14) % 28
        for grid_y in range(-30, h+30, 28):
            arcade.draw_line(0, grid_y+off, w, grid_y+off-18, tc["grid_line"], 1)

        sc = tc["star_color"]
        for s in self.stars:
            tw = 0.55 + 0.45*math.sin(self.bg_time*s["twinkle"]+s["phase"])
            al = max(20, min(255, int(s["alpha"]*tw)))
            arcade.draw_circle_filled(s["x"], s["y"], s["size"], (*sc[:3], al))

    def _draw_entity_glows(self):
        tc = THEMES[self.menu_theme]
        p  = self.player
        pg = tc["player_glow_spd"] if p.speed_active else tc["player_glow"]
        arcade.draw_circle_filled(p.center_x, p.center_y, 34, pg)
        for e in self.enemies:
            arcade.draw_circle_filled(e.center_x, e.center_y, 24, tc["enemy_glow"])
        for e in self.shooting_enemies:
            arcade.draw_circle_filled(e.center_x, e.center_y, 26, tc["shoot_glow"])
        for b in self.bosses:
            boss_r = 54 + 8*math.sin(self.bg_time*2.5)
            arcade.draw_circle_filled(b.center_x, b.center_y, boss_r, tc["boss_glow"])

    def _draw_particles(self):
        for pt in self.particles:
            lr = pt["life"]/pt["max_life"]
            r  = max(0.5, pt["size"]*(0.45+0.55*lr))
            c  = pt["color"]
            arcade.draw_circle_filled(pt["x"],pt["y"],r,(c[0],c[1],c[2],int(255*lr)))

    def _draw_enemy_health_bars(self):
        for sl in [self.enemies, self.shooting_enemies, self.bosses]:
            for e in sl:
                if e.health >= e.max_health: continue
                ratio = max(0.0, e.health/e.max_health)
                l = e.center_x-e.width*0.45;  r = e.center_x+e.width*0.45
                tb = e.top+8;  bb = tb-5
                arcade.draw_lrbt_rectangle_filled(l,r,bb,tb,(35,25,25,220))
                arcade.draw_lrbt_rectangle_filled(l,l+(r-l)*ratio,bb,tb,(255,100,90,235))

    # ──────────────────────────────────────────────────
    #  HUD  (H hides the ENTIRE panel)
    # ──────────────────────────────────────────────────

    # ──────────────────────────────────────────────────
    #  HUD  — floating, no box, futuristic style
    # ──────────────────────────────────────────────────

    @staticmethod
    def _txt_shadow(text, x, y, color, size, font_name,
                    anchor_x="left", anchor_y="baseline",
                    bold=False, ox=2, oy=-2):
        """Draw text with a dark drop-shadow for crisp readability."""
        sr, sg, sb = 0, 0, 0
        sa = min(200, int(color[3] * 0.55) if len(color) == 4 else 140)
        arcade.draw_text(text, x+ox, y+oy, (sr,sg,sb,sa), size,
                         anchor_x=anchor_x, anchor_y=anchor_y,
                         bold=bold, font_name=font_name)
        arcade.draw_text(text, x, y, color, size,
                         anchor_x=anchor_x, anchor_y=anchor_y,
                         bold=bold, font_name=font_name)

    def _draw_powerup_panel(self, p, t: float, font_ui, font_num) -> None:
        """
        Unified power-up GUI panel — bottom-left of screen.
        Layout (bottom → top):
          14px margin from bottom
          Row A: inventory slot cards  (52×52 each)
          8px gap
          Row B: active-effect cards   (shown only when a powerup is running)
        """
        inv = p.inventory

        # ── Slot definitions ──────────────────────────────────────────────
        slots = [
            ("1", "SPD",  "SPEED",   inv.get("speed",    0),
             p.speed_active,   getattr(p, "speed_timer",    0), POWERUP_DURATION,
             (255, 215,  40)),
            ("2", "SHD",  "SHIELD",  inv.get("shield",   0),
             p.shield_active,  getattr(p, "shield_timer",   0), POWERUP_DURATION,
             ( 55, 215, 255)),
            ("3", "AUTO", "AUTO",    inv.get("autofire",  0),
             p.autofire_active,getattr(p, "autofire_timer", 0), POWERUP_DURATION,
             (235,  80, 255)),
            ("4", "TRP",  "TRIPLE",  inv.get("triple",   0),
             p.triple_active,  getattr(p, "triple_timer",   0), POWERUP_DURATION,
             (255, 140,  40)),
        ]
        if self.selected_ship in BEAM_SHIP_INDICES:
            slots.append(
                ("5", "360B", "360°BEAM", inv.get("beam360", 0),
                 p.beam360_active, getattr(p, "beam360_timer", 0), POWERUP_DURATION,
                 (255, 110,  40)))
        elif self.selected_ship in ELECTRIC_SHIP_INDICES:
            slots.append(
                ("5", "⚡360", "⚡360°", inv.get("elec360", 0),
                 p.elec360_active, getattr(p, "elec360_timer", 0), ELECTRIC_360_DURATION,
                 (155, 100, 255)))

        # ── Geometry ─────────────────────────────────────────────────────
        SZ    = 52          # card size
        GAP   = 8           # gap between cards
        PAD   = 10          # inner padding inside card
        MX    = 14          # left margin from edge
        MY    = 14          # bottom margin from edge
        n     = len(slots)
        total_w = n * SZ + (n - 1) * GAP

        # Panel backdrop
        backdrop_pad = 8
        arcade.draw_lrbt_rectangle_filled(
            MX - backdrop_pad,
            MX + total_w + backdrop_pad,
            MY - backdrop_pad,
            MY + SZ + backdrop_pad,
            (6, 10, 26, 170))
        arcade.draw_lrbt_rectangle_outline(
            MX - backdrop_pad,
            MX + total_w + backdrop_pad,
            MY - backdrop_pad,
            MY + SZ + backdrop_pad,
            (60, 90, 150, 90), 1)

        # ── Draw each slot card ───────────────────────────────────────────
        for idx, (key, short, full, cnt, active, timer, max_dur, ic) in enumerate(slots):
            cx_ = MX + idx * (SZ + GAP)        # card left x
            cy_ = MY                            # card bottom y
            cr_ = cx_ + SZ
            ct_ = cy_ + SZ
            ccx = cx_ + SZ // 2                # card centre x
            ccy = cy_ + SZ // 2                # card centre y

            has_stock = cnt > 0
            dim       = not has_stock and not active
            pulse     = 0.5 + 0.5 * math.sin(t * 6.0 + idx * 1.1)

            # ── Card fill ────────────────────────────────────────────────
            if active:
                fill_a = int(80 + 40 * pulse)
                arcade.draw_lrbt_rectangle_filled(cx_, cr_, cy_, ct_,
                                                   (*ic, fill_a))
            elif has_stock:
                arcade.draw_lrbt_rectangle_filled(cx_, cr_, cy_, ct_,
                                                   (*ic, 40))
            else:
                arcade.draw_lrbt_rectangle_filled(cx_, cr_, cy_, ct_,
                                                   (12, 16, 32, 180))

            # ── Card border ──────────────────────────────────────────────
            if active:
                brd_a = int(200 + 55 * pulse)
                arcade.draw_lrbt_rectangle_outline(cx_, cr_, cy_, ct_,
                                                    (*ic, brd_a), 2)
                # outer glow ring
                arcade.draw_lrbt_rectangle_outline(cx_-3, cr_+3, cy_-3, ct_+3,
                                                    (*ic, int(55 * pulse)), 3)
            elif has_stock:
                arcade.draw_lrbt_rectangle_outline(cx_, cr_, cy_, ct_,
                                                    (*ic, 180), 1)
            else:
                arcade.draw_lrbt_rectangle_outline(cx_, cr_, cy_, ct_,
                                                    (45, 55, 80, 120), 1)

            # ── Arc timer ring (active only) ─────────────────────────────
            if active and max_dur > 0:
                ratio = max(0.0, min(1.0, timer / max_dur))
                arc_r = SZ // 2 - 3
                # dim track
                arcade.draw_arc_outline(ccx, ccy, arc_r * 2, arc_r * 2,
                                        (50, 60, 90, 120),
                                        90, 90 + 360, 3)
                # filled sweep (counter-clockwise from top = 90°)
                end_ang = 90 + 360 * ratio
                if ratio > 0.02:
                    arcade.draw_arc_outline(ccx, ccy, arc_r * 2, arc_r * 2,
                                            (*ic, 220),
                                            90, end_ang, 3)
                # timer text in centre
                self._txt_shadow(f"{timer:.0f}s", ccx, ccy - 5,
                                 (*ic, 245), 11, font_num,
                                 anchor_x="center", bold=True)

            # ── Icon symbol (not active) ──────────────────────────────────
            else:
                icon_col = (*ic, 90) if dim else (*ic, 220)
                icon_sz  = 14 if dim else 16
                if short == "SPD":
                    # Lightning bolt polygon
                    bx, by = ccx, ccy
                    pts = [(bx+2, by+9),(bx-1, by+1),(bx+3, by+1),
                           (bx-2, by-9),(bx+1, by-1),(bx-3, by-1)]
                    arcade.draw_polygon_filled(pts, icon_col)
                elif short == "SHD":
                    # Shield arc + bar
                    arcade.draw_arc_filled(ccx, ccy+2, 20, 18, icon_col, 0, 180)
                    arcade.draw_lrbt_rectangle_filled(ccx-10, ccx+10,
                                                       ccy-8, ccy+2, icon_col)
                elif short == "AUTO":
                    # Crosshair
                    arcade.draw_circle_outline(ccx, ccy, 9, icon_col, 2)
                    arcade.draw_line(ccx-14, ccy, ccx-4, ccy, icon_col, 2)
                    arcade.draw_line(ccx+4,  ccy, ccx+14, ccy, icon_col, 2)
                    arcade.draw_line(ccx, ccy-14, ccx, ccy-4, icon_col, 2)
                    arcade.draw_line(ccx, ccy+4,  ccx, ccy+14, icon_col, 2)
                elif short == "TRP":
                    # Three bullet dots
                    for ox in (-8, 0, 8):
                        arcade.draw_circle_filled(ccx + ox, ccy, 4, icon_col)
                elif "360" in short or "⚡" in short:
                    # Star burst
                    for ang_i in range(8):
                        a = math.radians(ang_i * 45)
                        arcade.draw_line(ccx + math.cos(a)*4, ccy + math.sin(a)*4,
                                         ccx + math.cos(a)*12, ccy + math.sin(a)*12,
                                         icon_col, 2)

            # ── Hotkey badge (top-left corner) ───────────────────────────
            key_col = (*ic, 110) if dim else (*ic, 220)
            arcade.draw_text(f"[{key}]", cx_ + 4, ct_ - 12,
                             key_col, 8, font_name=font_num)

            # ── Name label (bottom centre) ───────────────────────────────
            if not active:
                name_col = (*ic, 80) if dim else (*ic, 200)
                self._txt_shadow(short, ccx, cy_ + 4, name_col, 8,
                                 font_ui, anchor_x="center", bold=True)

            # ── Stock count badge (top-right corner) ─────────────────────
            badge_x = cr_ - 4
            badge_y = ct_ - 4
            if cnt > 0:
                # filled circle badge
                arcade.draw_circle_filled(badge_x, badge_y, 9, (*ic, 210))
                arcade.draw_circle_outline(badge_x, badge_y, 9, (255,255,255,80), 1)
                arcade.draw_text(str(cnt), badge_x, badge_y - 5,
                                 (10, 10, 20, 255), 10, anchor_x="center",
                                 bold=True, font_name=font_num)
            elif not active:
                # empty badge
                arcade.draw_circle_filled(badge_x, badge_y, 8, (20, 25, 45, 200))
                arcade.draw_circle_outline(badge_x, badge_y, 8, (50, 60, 90, 150), 1)
                arcade.draw_text("0", badge_x, badge_y - 5,
                                 (60, 70, 100, 160), 9, anchor_x="center",
                                 bold=True, font_name=font_num)

    @staticmethod
    def _draw_seg_bar(x: int, y: int, width: int, height: int, ratio: float,
                      color_fill: tuple, segs: int = 20, gap: int = 2) -> None:
        """Segmented health / progress bar — no border rectangle."""
        seg_w  = (width - gap * (segs - 1)) / segs
        filled = int(ratio * segs + 0.5)
        for i in range(segs):
            lx = x + i * (seg_w + gap)
            rx = lx + seg_w
            if i < filled:
                arcade.draw_lrbt_rectangle_filled(lx, rx, y, y + height, color_fill)
                bright = tuple(min(255, c + 80) for c in color_fill[:3])
                arcade.draw_lrbt_rectangle_filled(lx, rx, y + height - 2, y + height,
                                                   (*bright, 180))
            else:
                arcade.draw_lrbt_rectangle_filled(lx, rx, y, y + height, (35, 45, 70, 100))

    def _draw_hud(self):
        w, h = self.width, self.height
        p    = self.player
        font_ui  = self._FONT_UI
        font_num = self._FONT_NUM

        # ── Subtle vignette edges so text floats on any background ──
        vig = THEMES[self.menu_theme]["vignette"]
        for i in range(5):
            va = 28 - i*5
            arcade.draw_lrbt_rectangle_filled(0, w, h-i*12, h, (*vig, va))
            arcade.draw_lrbt_rectangle_filled(0, w, 0, i*12,   (*vig, va))
            arcade.draw_lrbt_rectangle_filled(0, i*12, 0, h,   (*vig, va))

        if not self.show_hud:
            self._txt_shadow("[H] show HUD", 14, h-18,
                             (110,135,185,110), 9, font_ui)
            return

        t = self.bg_time

        # ══ TOP-LEFT  ════════════════════════════════

        # ── SCORE ──────────────────────────────────
        self.txt_score.text = f"{self.score:,}"
        self.txt_score.draw()
        self._txt_shadow("SCORE", 22, h-12, (120,165,230,180), 9, font_ui)

        # ── HP section ─────────────────────────────
        # Row positions (all from h, spaced so nothing overlaps):
        #   h-46 : "HEALTH" small label
        #   h-60 : "100 / 100" numbers
        #   h-76 to h-68 : segmented bar  (8px below numbers)
        #   h-66 : neon glow line on top of bar
        hr   = max(0.0, p.health/p.max_health)
        hc   = (60,235,110) if hr>0.55 else (255,195,55) if hr>0.28 else (255,60,60)

        # "HEALTH" label row
        self._txt_shadow("HEALTH", 22, h-46, (120,165,230,200), 10, font_ui)

        # HP numbers row — drawn BEFORE bar so bar doesn't cover them
        hp_str = f"{int(max(0, p.health))}  /  {p.max_health}"
        self._txt_shadow(hp_str, 22, h-62, (*hc[:3], 230), 11, font_num, bold=True)

        # Segmented bar — clear below numbers (bar top = h-68, number baseline = h-62, gap = 6px)
        self._draw_seg_bar(22, h-82, 230, 10, hr, hc, segs=23, gap=2)
        # Neon glow highlight line
        if hr > 0:
            gw = int(230 * hr)
            arcade.draw_lrbt_rectangle_filled(22, 22+gw, h-72, h-71,
                                               (*hc[:3], int(155*hr)))

        # ══ POWER-UP PANEL (bottom-left) ══════════════
        self._draw_powerup_panel(p, t, font_ui, font_num)

        # ══ TOP-RIGHT ════════════════════════════════

        # ── Timer ──────────────────────────────────
        self._txt_shadow("TIME", w-18, h-14, (120,165,230,175), 9, font_ui,
                         anchor_x="right")
        self.txt_timer.text = f"{self.time_alive:06.1f}s"
        self.txt_timer.draw()

        # ── Coin counter (top-right, below timer) ───
        coin_c = (255, 220, 40, 245)
        self._txt_shadow(f"$ {self.coins:,}", w-18, h-46, coin_c, 14,
                         font_num, anchor_x="right", bold=True)
        self._txt_shadow("COINS", w-18, h-62, (200, 170, 30, 160), 9,
                         font_ui, anchor_x="right")

        # ── Difficulty badge ────────────────────────
        dp  = self._dpreset
        dc  = dp["color"]
        dlbl = dp["label"]
        bw_ = len(dlbl)*9 + 24
        bx_ = w - 18 - bw_
        by_ = h - 54
        arcade.draw_lrbt_rectangle_filled(bx_, bx_+bw_, by_, by_+18,
                                           (*dc, 55))
        arcade.draw_lrbt_rectangle_outline(bx_, bx_+bw_, by_, by_+18,
                                            (*dc, 185), 1)
        self._txt_shadow(dlbl, bx_+bw_//2, by_+3, (*dc, 240), 10, font_ui,
                         anchor_x="center", bold=True)

        # ══ COMBO (top-right below difficulty) ═══════
        if self.combo > 1 and self.combo_timer > 0:
            pulse = 0.75 + 0.25*math.sin(t*8)
            self.txt_combo.text  = f"×{self.combo}  COMBO"
            self.txt_combo.color = (255, 220, 60, int(230*pulse))
            self.txt_combo.draw()

        # ══ BOTTOM ════════════════════════════════════

        # hint bar (very subtle, center bottom)
        self.txt_hint.draw()

        # ── Boss lockout banner ─────────────────────
        if self.boss_on_screen:
            pulse = int(170 + 85*math.sin(t*5.5))
            # glowing background strip
            arcade.draw_lrbt_rectangle_filled(0, w, 26, 46, (180,20,20,int(60*math.sin(t*5.5)+65)))
            self._txt_shadow("!! BOSS FIGHT  ·  ENEMY SPAWN LOCKED !!",
                             w//2, 30, (255,85,85,pulse), 12, font_ui,
                             anchor_x="center", bold=True)

        # ── Notification ───────────────────────────
        if self.notif_timer > 0:
            a = min(255, int(self.notif_timer*290))
            c = self.notif_color
            self.txt_notif.text  = self.notif_text
            self.txt_notif.color = (*c[:3], a)
            self.txt_notif.draw()

    def _draw_crosshair(self):
        x, y = self.mouse_x, self.mouse_y
        cc   = THEMES[self.menu_theme]["crosshair"]
        arcade.draw_circle_outline(x, y, 13, cc, 2)
        for x1, y1, x2, y2 in [(x-20, y, x-8, y), (x+8, y, x+20, y),
                                 (x, y-20, x, y-8), (x, y+8, x, y+20)]:
            arcade.draw_line(x1, y1, x2, y2, cc, 2)

    # ══════════════════════════════════════════════════
    #  ON DRAW
    # ══════════════════════════════════════════════════

    def on_draw(self):
        w, h = self.width, self.height
        self.clear()

        if self.game_state == STATE_MENU:
            self._draw_menu()
            return

        if self.game_state == STATE_SHOP:
            self._draw_shop()
            return

        # Playing / paused / gameover — always draw the world
        tc = THEMES[self.menu_theme]   # pull once, use everywhere below
        self._draw_bg_space()
        self._draw_entity_glows()
        self.powerups.draw()
        self.coins_list.draw()
        self.player_list.draw()
        self.enemies.draw();  self.shooting_enemies.draw();  self.bosses.draw()
        self.bullets.draw();  self.enemy_bullets.draw()

        # Bullets draw their own glow via arcade-generated textures — no overlay needed

        # ── Beams (beam-ship) ────────────────────────────────────────
        for beam in self.beams:
            beam.draw()

        # ── Electric bolts (Reaper) ───────────────────────────────────
        for bolt in self.elec_bolts:
            bolt.draw_bolt()

        # ── 360° electric aura ring while elec360 is active ──────────
        if self.player.elec360_active:
            t_pulse = self.bg_time
            ring_r  = 48 + 12*math.sin(t_pulse*11)
            for layer, (col, width) in enumerate([
                    ((80,  50, 255, 38), 20),
                    ((140, 90, 255, 80), 8),
                    ((220, 180, 255, 200), 2)]):
                arcade.draw_circle_outline(
                    self.player.center_x, self.player.center_y,
                    ring_r + layer*3, col, width)
            # Randomly spark off the ring
            if random.random() < 0.5:
                ang = random.uniform(0, math.tau)
                sx  = self.player.center_x + math.cos(ang)*ring_r
                sy  = self.player.center_y + math.sin(ang)*ring_r
                self._add_particle(sx, sy,
                                    math.cos(ang)*random.uniform(40,120),
                                    math.sin(ang)*random.uniform(40,120),
                                    random.uniform(1.0, 2.2),
                                    random.uniform(0.05, 0.14),
                                    (180, 140, 255), 0.80)

        if self.player.shield_active:
            rr = 38 + 2.5*math.sin(self.bg_time*9)
            arcade.draw_circle_outline(self.player.center_x, self.player.center_y,
                                        rr, tc["shield_ring"], 3)

        # ── Auto-fire target lock ring ───────────────
        if self.player.autofire_active:
            tgt = self._targeted_enemy(self.mouse_x, self.mouse_y)
            if tgt:
                pulse = 0.55 + 0.45*math.sin(self.bg_time*9)
                ring_r = max(tgt.width, tgt.height)*0.65 + 8
                arcade.draw_circle_outline(tgt.center_x, tgt.center_y,
                                            ring_r, (255, 80, 255, int(210*pulse)), 2)
                # corner brackets
                bk = ring_r * 0.55
                for (sx, sy) in [(tgt.center_x-ring_r, tgt.center_y+ring_r),
                                  (tgt.center_x+ring_r, tgt.center_y+ring_r),
                                  (tgt.center_x-ring_r, tgt.center_y-ring_r),
                                  (tgt.center_x+ring_r, tgt.center_y-ring_r)]:
                    dx = 1 if sx > tgt.center_x else -1
                    dy = 1 if sy > tgt.center_y else -1
                    c_ = (255, 80, 255, int(230*pulse))
                    arcade.draw_line(sx, sy, sx + dx*bk, sy, c_, 2)
                    arcade.draw_line(sx, sy, sx, sy - dy*bk, c_, 2)

        # powerup sprites draw their own icon — no text label needed

        self._draw_enemy_health_bars()
        self._draw_particles()
        self._draw_hud()

        if self.damage_flash > 0:
            df_r, df_g, df_b = tc["damage_flash"][:3]
            df_base_a = tc["damage_flash"][3] if len(tc["damage_flash"]) == 4 else 170
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h,
                (df_r, df_g, df_b, int(df_base_a * self.damage_flash)))

        self._draw_crosshair()

        if self.game_state == STATE_GAMEOVER:
            # ── Full-screen overlay ──────────────────────────────────────
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, tc["gameover_bg"])

            # ── Central card ─────────────────────────────────────────────
            cw_ = min(560, int(w * 0.72))
            ch_ = 310
            cx_ = (w - cw_) // 2
            cy_ = h // 2 - ch_ // 2
            arcade.draw_lrbt_rectangle_filled(
                cx_+6, cx_+cw_+6, cy_-6, cy_+ch_-6, (0, 0, 0, 80))
            arcade.draw_lrbt_rectangle_filled(
                cx_, cx_+cw_, cy_, cy_+ch_, tc["gameover_card"])
            arcade.draw_lrbt_rectangle_outline(
                cx_, cx_+cw_, cy_, cy_+ch_, tc["gameover_border"], 2)
            arcade.draw_lrbt_rectangle_outline(
                cx_+4, cx_+cw_-4, cy_+4, cy_+ch_-4,
                (*tc["gameover_border"][:3], 55), 1)
            # corner accents
            csz = 18
            ga  = tc["gameover_accent"]
            for (ax, ay, dx, dy) in [(cx_, cy_, -1,-1), (cx_+cw_, cy_, 1,-1),
                                      (cx_, cy_+ch_, -1, 1), (cx_+cw_, cy_+ch_, 1, 1)]:
                arcade.draw_line(ax, ay, ax+dx*csz, ay, ga, 2)
                arcade.draw_line(ax, ay, ax, ay+dy*csz, ga, 2)

            # ── Content ──────────────────────────────────────────────────
            mid_x  = w // 2
            top_y  = cy_ + ch_ - 58
            lbl_y  = cy_ + ch_ - 128
            num_y  = cy_ + ch_ - 172
            div_y_ = cy_ + ch_ - 200
            rst_y  = cy_ + 22

            arcade.draw_line(cx_+24, top_y-14, cx_+cw_-24, top_y-14,
                             tc["gameover_border"], 1)
            arcade.draw_line(cx_+24, div_y_,   cx_+cw_-24, div_y_,
                             (*tc["gameover_accent"][:3], 100), 1)

            go_title_c = (255, 50, 50, 255) if self.menu_theme == "dark" \
                         else (20, 50, 180, 255)
            score_c    = (210, 235, 255, 245) if self.menu_theme == "dark" \
                         else (14, 34, 86, 245)
            label_c    = (130, 165, 215, 200) if self.menu_theme == "dark" \
                         else (60, 90, 165, 200)
            restart_c  = (120, 158, 215, 195) if self.menu_theme == "dark" \
                         else (50, 80, 160, 195)

            self._txt_shadow("GAME OVER", mid_x, top_y, go_title_c, 52,
                             self._FONT_UI, anchor_x="center", bold=True)
            self._txt_shadow("FINAL  SCORE", mid_x, lbl_y, label_c, 12,
                             self._FONT_UI, anchor_x="center")
            self._txt_shadow(f"{self.score:,}", mid_x, num_y, score_c, 36,
                             self._FONT_NUM, anchor_x="center", bold=True)
            # Coins earned this run
            self._txt_shadow(f"+ {self.run_coins}  coins  earned  (total: {self.coins})",
                             mid_x, div_y_ + 14, (255, 215, 40, 210), 11,
                             self._FONT_NUM, anchor_x="center")
            self._txt_shadow("PRESS  R  TO  RESTART", mid_x, rst_y, restart_c, 15,
                             self._FONT_UI, anchor_x="center")

        if self.game_state == STATE_PAUSED:
            self._draw_menu()   # menu overlaid on frozen world

    # ══════════════════════════════════════════════════
    #  ON UPDATE
    # ══════════════════════════════════════════════════

    def on_update(self, delta_time):
        delta = min(0.05, delta_time)
        self.bg_time += delta

        self._update_starfield(delta)
        self._update_particles(delta)

        if self.notif_timer  > 0: self.notif_timer  -= delta
        if self.damage_flash > 0: self.damage_flash = max(0.0, self.damage_flash-2.6*delta)
        if self.contact_damage_timer > 0: self.contact_damage_timer -= delta
        if self.combo_timer > 0: self.combo_timer -= delta
        elif self.combo > 0:     self.combo = 0

        if self.game_state != STATE_PLAYING:
            return

        self.time_alive += delta
        p = self.player
        difficulty = min(3.0, self.time_alive/90.0)

        # movement
        ix = float(self.right_key)-float(self.left_key)
        iy = float(self.up)-float(self.down)
        if ix and iy: ix *= 0.70710678;  iy *= 0.70710678
        ship_spd = p.get_speed() * SHIPS[self.selected_ship]["spd_mult"]
        sm = min(1.0, 14.0*delta)
        p.change_x += (ix*ship_spd - p.change_x)*sm
        p.change_y += (iy*ship_spd - p.change_y)*sm
        p.update(delta)
        p.update_powerups(delta)

        # boundary clamp uses live window size (fixes fullscreen)
        p.left   = max(p.left,   0)
        p.right  = min(p.right,  self.width)
        p.bottom = max(p.bottom, 0)
        p.top    = min(p.top,    self.height)

        # engine particles
        mv = abs(p.change_x)+abs(p.change_y)
        if mv > 130 and random.random() < 0.55:
            ang   = math.atan2(-p.change_y,-p.change_x)+random.uniform(-0.5,0.5)
            s2    = random.uniform(80,160)
            ep_c  = THEMES[self.menu_theme]["engine_particle"]
            self._add_particle(
                p.center_x+random.uniform(-4,4), p.center_y-8+random.uniform(-3,3),
                math.cos(ang)*s2, math.sin(ang)*s2,
                random.uniform(1.4,2.8), random.uniform(0.12,0.24), ep_c, 0.9)

        # firing
        is_beam_ship     = (self.selected_ship in BEAM_SHIP_INDICES)
        is_electric_ship = (self.selected_ship in ELECTRIC_SHIP_INDICES)

        firing = self.mouse_held or p.autofire_active
        if firing:
            rate = (ELECTRIC_FIRE_RATE if is_electric_ship
                    else AUTO_FIRE_RATE if p.autofire_active
                    else NORMAL_FIRE_RATE)
            self.fire_timer += delta
            while self.fire_timer >= rate:
                if is_beam_ship:
                    self._fire_beam(p.beam360_active)
                elif is_electric_ship:
                    # 360° mode active → burst every shot; aim mode → track cursor
                    if p.elec360_active:
                        self._fire_electric(full_360=True)
                    elif p.autofire_active:
                        tgt = self._targeted_enemy(self.mouse_x, self.mouse_y)
                        aim_x = tgt.center_x if tgt else self.mouse_x
                        aim_y = tgt.center_y if tgt else self.mouse_y
                        ang   = math.atan2(aim_y - p.center_y, aim_x - p.center_x)
                        self.elec_bolts.append(ElectricBolt(p.center_x, p.center_y, ang))
                    else:
                        self._fire_electric(full_360=False)
                else:
                    if p.autofire_active:
                        tgt = self._targeted_enemy(self.mouse_x, self.mouse_y)
                        self._shoot_toward(tgt.center_x if tgt else self.mouse_x,
                                           tgt.center_y if tgt else self.mouse_y)
                    else:
                        self._shoot_toward(self.mouse_x, self.mouse_y)
                self.fire_timer -= rate

        # Update beams
        self.beams = [b for b in self.beams if b.life > 0]
        for beam in self.beams:
            beam.update(delta)

        # Update electric bolts
        self.elec_bolts.update(delta)
        for bolt in list(self.elec_bolts):
            if bolt.life <= 0:
                bolt.remove_from_sprite_lists()

        self.bullets.update(delta);  self.enemy_bullets.update(delta)
        self.powerups.update(delta)
        self.coins_list.update(delta)

        ww, hh = self.width, self.height
        for b in list(self.bullets):
            if b.life<=0 or b.right<-30 or b.left>ww+30 or b.top<-30 or b.bottom>hh+30:
                b.remove_from_sprite_lists()
        for b in list(self.enemy_bullets):
            if b.life<=0 or b.right<-30 or b.left>ww+30 or b.top<-30 or b.bottom>hh+30:
                b.remove_from_sprite_lists()
        for pu in list(self.powerups):
            if pu.top < -10 or pu.life <= 0:
                pu.remove_from_sprite_lists()
        # Remove expired or off-screen coins
        for c in list(self.coins_list):
            if c.life <= 0 or c.top < -10:
                c.remove_from_sprite_lists()

        # Coin Magnet — pull nearby coins toward player
        if self.upgrades.get("magnet", 0) >= 1:
            px, py = self.player.center_x, self.player.center_y
            for c in list(self.coins_list):
                dist = math.hypot(c.center_x - px, c.center_y - py)
                if dist <= COIN_MAGNET_RANGE:
                    if dist < 12:
                        self._collect_coin(c)
                    else:
                        pull = 320 * delta / max(dist, 1)
                        c.center_x += (px - c.center_x) * pull
                        c.center_y += (py - c.center_y) * pull

        dp  = self._dpreset                 # shorthand for active difficulty preset
        sim = dp["spawn_interval_mult"]     # slowdown/speedup factor for spawn timers

        # ── Boss lockout: while any boss lives, freeze all other spawns ──────
        self.boss_on_screen = len(self.bosses) > 0

        # base intervals (time-scaled) then multiplied by difficulty preset
        ei = max(0.10, (1.0 -0.58*min(difficulty,1)-0.16*max(0,difficulty-1)
                        -0.08*max(0,difficulty-2)) * sim)
        si = max(0.45, (3.0 -2.30*min(difficulty,1)-0.40*max(0,difficulty-1)) * sim)
        bi = max(6.0,  (22.0-9.0 *min(difficulty,1)-3.0 *max(0,difficulty-1)) * sim)

        # batch sizes — medium caps at max_regular_enemies
        reg_on_screen = len(self.enemies)+len(self.shooting_enemies)
        eb = max(1, min(1+int(difficulty*1.8),
                        dp["max_regular_enemies"] - reg_on_screen))
        sb = max(1, min(1+int(difficulty*0.9),
                        dp["max_regular_enemies"] - reg_on_screen))

        if not self.boss_on_screen:
            self.enemy_spawn += delta
            if self.enemy_spawn >= ei and reg_on_screen < dp["max_regular_enemies"]:
                for _ in range(eb): self.spawn_enemy(difficulty)
                self.enemy_spawn = 0.0

            self.shooting_spawn += delta
            if self.shooting_spawn >= si and reg_on_screen < dp["max_regular_enemies"]:
                for _ in range(sb): self.spawn_shooting_enemy(difficulty)
                self.shooting_spawn = 0.0

        self.boss_spawn += delta
        if self.boss_spawn >= bi and not self.boss_on_screen:
            self.spawn_boss(difficulty);  self.boss_spawn = 0.0

        self.update_enemies(delta, difficulty)
        self.check_collisions()
        self._check_auto_triggers()

    # ──────────────────────────────────────────────────
    #  ENEMY AI
    # ──────────────────────────────────────────────────

    def _nearest_enemy(self):
        """Returns the enemy closest to the player (fallback for auto-fire)."""
        all_e = list(self.enemies)+list(self.shooting_enemies)+list(self.bosses)
        if not all_e: return None
        px, py = self.player.center_x, self.player.center_y
        return min(all_e, key=lambda e: math.hypot(e.center_x-px, e.center_y-py))

    def _targeted_enemy(self, cursor_x: float, cursor_y: float):
        """
        Returns the enemy closest to the cursor position.
        Used by auto-fire so the player can steer which enemy gets shot.
        Falls back to nearest-to-player if no enemy is within 220 px of cursor.
        """
        all_e = list(self.enemies)+list(self.shooting_enemies)+list(self.bosses)
        if not all_e: return None
        # find closest to cursor
        best = min(all_e, key=lambda e: math.hypot(e.center_x-cursor_x, e.center_y-cursor_y))
        dist = math.hypot(best.center_x-cursor_x, best.center_y-cursor_y)
        if dist <= 220:
            return best          # cursor is near this enemy — lock on
        return self._nearest_enemy()  # cursor is in open space — pick nearest

    def _shoot_toward(self, tx, ty):
        px, py = self.player.center_x, self.player.center_y
        base   = math.atan2(ty-py, tx-px)
        for off in ([-0.18,0.0,0.18] if self.player.triple_active else [0.0]):
            ang = base+off
            self.bullets.append(Bullet(px,py,ang))
            self._spawn_muzzle(px,py,ang)

    def _fire_beam(self, full_360: bool = False) -> None:
        """Fire a beam (or 360° burst) from the player's position."""
        px, py = self.player.center_x, self.player.center_y
        bc     = (255, 100, 40)   # beam core colour

        if full_360:
            # Fire BEAM_360_ANGLES evenly-spaced beams
            for i in range(BEAM_360_ANGLES):
                ang = i * (math.tau / BEAM_360_ANGLES)
                self.beams.append(BeamRay(px, py, ang, color=bc))
            # Burst particle effect
            self._burst(px, py, 24, (255,120,50), 80, 260, 1.8, 3.5, .12, .28)
        else:
            ang = math.atan2(self.mouse_y - py, self.mouse_x - px)
            self.beams.append(BeamRay(px, py, ang, color=bc))
            # Small muzzle flash along beam
            for _ in range(5):
                off = random.uniform(-0.15, 0.15)
                spd = random.uniform(150, 320)
                self._add_particle(
                    px + math.cos(ang)*random.uniform(8, 20),
                    py + math.sin(ang)*random.uniform(8, 20),
                    math.cos(ang+off)*spd, math.sin(ang+off)*spd,
                    random.uniform(1.6, 2.8), random.uniform(0.06, 0.14),
                    (255, 160, 80), 0.85)

    def _fire_electric(self, full_360: bool = False) -> None:
        """Fire electric bolt(s) from the Reaper ship."""
        px, py = self.player.center_x, self.player.center_y

        if full_360:
            # 360° burst — fire ELECTRIC_360_COUNT bolts evenly around the ship
            for i in range(ELECTRIC_360_COUNT):
                ang  = i * (math.tau / ELECTRIC_360_COUNT)
                bolt = ElectricBolt(px, py, ang)
                self.elec_bolts.append(bolt)
            # Big electric burst effect
            self._burst(px, py, 40, (130, 90, 255), 90, 310, 2.0, 4.5, .12, .35)
            self._burst(px, py, 20, (210, 180, 255), 50, 180, 1.2, 2.8, .08, .22)
            # Screen flash
            self.damage_flash = max(self.damage_flash, 0.45)
            self.notif_text   = "⚡ 360° ELECTRIC BLAST!"
            self.notif_color  = (150, 100, 255)
            self.notif_timer  = 1.4
        else:
            # Single aimed bolt toward cursor
            ang  = math.atan2(self.mouse_y - py, self.mouse_x - px)
            bolt = ElectricBolt(px, py, ang)
            self.elec_bolts.append(bolt)
            # Small muzzle spark effect
            for _ in range(6):
                off  = random.uniform(-0.30, 0.30)
                spd  = random.uniform(120, 260)
                self._add_particle(
                    px + math.cos(ang)*random.uniform(6, 16),
                    py + math.sin(ang)*random.uniform(6, 16),
                    math.cos(ang+off)*spd, math.sin(ang+off)*spd,
                    random.uniform(1.2, 2.2), random.uniform(0.05, 0.12),
                    (160, 120, 255), 0.82)

    def update_enemies(self, delta: float, difficulty: float) -> None:
        p  = self.player
        dp = self._dpreset

        def _face_player(sprite, a_rad, smooth=18.0):
            """Smoothly rotate sprite to face direction a_rad (angle to player)."""
            target = math.degrees(a_rad) - 90   # -90: nose-up sprites face the player
            # Shortest-path angle difference  (-180 to +180)
            diff = (target - sprite.angle + 180) % 360 - 180
            sprite.angle += diff * min(1.0, smooth * delta)

        # ── Basic chasers ─────────────────────────────
        for e in self.enemies:
            a   = math.atan2(p.center_y-e.center_y, p.center_x-e.center_x)
            spd = ENEMY_SPEED * (1.0+0.22*difficulty) * dp["enemy_speed_mult"]
            e.center_x += math.cos(a)*spd*delta
            e.center_y += math.sin(a)*spd*delta
            _face_player(e, a)

        # ── Shooting enemies ─────────────────────────
        for e in self.shooting_enemies:
            a   = math.atan2(p.center_y-e.center_y, p.center_x-e.center_x)
            spd = ENEMY_SPEED * (0.9+0.22*difficulty) * dp["enemy_speed_mult"]
            e.center_x += math.cos(a)*spd*delta
            e.center_y += math.sin(a)*spd*delta
            _face_player(e, a)
            e.shoot_timer += delta
            if e.shoot_timer >= dp["enemy_fire_rate"]:
                self.enemy_bullets.append(
                    EnemyBullet(e.center_x, e.center_y, p.center_x, p.center_y))
                e.shoot_timer = 0.0

        # ── Boss ────────────────────────────────────
        for boss in self.bosses:
            a   = math.atan2(p.center_y-boss.center_y, p.center_x-boss.center_x)
            spd = BOSS_SPEED * (0.95+0.15*difficulty) * dp["boss_speed_mult"]
            boss.center_x += math.cos(a)*spd*delta
            boss.center_y += math.sin(a)*spd*delta
            _face_player(boss, a, smooth=10.0)  # boss turns slightly slower = more menacing

            boss.normal_timer  += delta
            boss.special_timer += delta

            # regular single shot
            if boss.normal_timer >= dp["boss_normal_rate"]:
                self.enemy_bullets.append(
                    EnemyBullet(boss.center_x, boss.center_y, p.center_x, p.center_y))
                boss.normal_timer = 0.0

            # spread attack — always exactly dp["boss_spread_count"] bullets
            if boss.special_timer >= dp["boss_special_rate"]:
                base  = math.atan2(p.center_y-boss.center_y, p.center_x-boss.center_x)
                nn    = dp["boss_spread_count"]
                step  = 0.26
                half  = nn // 2
                for i in range(-half, half+1):
                    self.enemy_bullets.append(EnemyBullet(
                        boss.center_x, boss.center_y,
                        angle_rad = base + i*step,
                        speed     = ENEMY_BULLET_SPEED * dp["boss_spread_speed"]))
                self._burst(boss.center_x, boss.center_y,
                            16, (255,100,100), 60, 170, 2, 3.8, .15, .35)
                boss.special_timer = 0.0

    # ──────────────────────────────────────────────────
    #  COLLISIONS
    # ──────────────────────────────────────────────────

    def check_collisions(self):
        p = self.player

        # ── Beam collisions (beam-ship only) ─────────────────────────
        for beam in list(self.beams):
            # Check regular enemies — instant kill
            for sprite_list in (self.enemies, self.shooting_enemies):
                for e in list(sprite_list):
                    hit_r = max(e.width, e.height) * 0.45
                    if beam.intersects_circle(e.center_x, e.center_y, hit_r):
                        self.score += 12 + min(24, self.combo*2)
                        self.combo += 1;  self.combo_timer = 2.0
                        self._try_drop_powerup(e.center_x, e.center_y, False)
                        self._drop_coin(e.center_x, e.center_y, COIN_VALUE_SHOOTING if isinstance(e, ShootingEnemy) else COIN_VALUE_ENEMY)
                        self._burst(e.center_x, e.center_y,
                                    30, (255,140,60), 60, 260, 1.8, 4.0, .15, .40)
                        e.remove_from_sprite_lists()
            # Check bosses — damage over time (DPS × beam life remaining)
            for boss in list(self.bosses):
                hit_r = max(boss.width, boss.height) * 0.45
                if beam.intersects_circle(boss.center_x, boss.center_y, hit_r):
                    dmg = BEAM_DAMAGE_PER_SEC * beam.life   # damage proportional to contact
                    boss.health -= dmg
                    self._burst(boss.center_x, boss.center_y,
                                8, (255,120,50), 40, 140, 1.2, 2.4, .06, .18)
                    if boss.health <= 0:
                        self.score += 70 + min(24, self.combo*2)
                        self.combo += 1;  self.combo_timer = 2.0
                        self._try_drop_powerup(boss.center_x, boss.center_y, True)
                        self._drop_coin(boss.center_x, boss.center_y, COIN_VALUE_BOSS)
                        self._burst(boss.center_x, boss.center_y,
                                    64,(255,100,80),70,320,2.3,4.8,.25,.65)
                        boss.remove_from_sprite_lists()
        # ── Electric bolt collisions (Reaper ship) ───────────────────
        for bolt in list(self.elec_bolts):
            hits = arcade.check_for_collision_with_lists(
                bolt, [self.enemies, self.shooting_enemies])
            if hits:
                enemy = hits[0]
                enemy.health -= ELECTRIC_DAMAGE
                # Electric spark burst on hit
                self._burst(bolt.center_x, bolt.center_y,
                            10, (140, 100, 255), 55, 200, 1.2, 2.6, .06, .18)
                self._burst(bolt.center_x, bolt.center_y,
                            4,  (220, 200, 255), 80, 260, 0.8, 1.8, .04, .10)
                bolt.remove_from_sprite_lists()
                if enemy.health <= 0:
                    self.score += 12 + min(24, self.combo*2)
                    self.combo += 1;  self.combo_timer = 2.0
                    self._try_drop_powerup(enemy.center_x, enemy.center_y, False)
                    self._drop_coin(enemy.center_x, enemy.center_y, COIN_VALUE_SHOOTING if isinstance(enemy, ShootingEnemy) else COIN_VALUE_ENEMY)
                    self._burst(enemy.center_x, enemy.center_y,
                                20, (130, 90, 255), 60, 240, 1.6, 3.5, .14, .38)
                    enemy.remove_from_sprite_lists()
                continue

            # Boss hit check — bolts damage boss but don't one-shot
            boss_hits = arcade.check_for_collision_with_list(bolt, self.bosses)
            if boss_hits:
                boss = boss_hits[0]
                boss.health -= ELECTRIC_BOSS_DAMAGE
                self._burst(bolt.center_x, bolt.center_y,
                            12, (150, 110, 255), 60, 220, 1.4, 3.0, .08, .20)
                bolt.remove_from_sprite_lists()
                if boss.health <= 0:
                    self.score += 70 + min(24, self.combo*2)
                    self.combo += 1;  self.combo_timer = 2.0
                    self._try_drop_powerup(boss.center_x, boss.center_y, True)
                    self._drop_coin(boss.center_x, boss.center_y, COIN_VALUE_BOSS)
                    self._burst(boss.center_x, boss.center_y,
                                64, (255, 100, 80), 70, 320, 2.3, 4.8, .25, .65)
                    boss.remove_from_sprite_lists()

        for bullet in list(self.bullets):
            hits = arcade.check_for_collision_with_lists(
                bullet, [self.enemies, self.shooting_enemies, self.bosses])
            if not hits: continue
            enemy = hits[0];  enemy.health -= 20
            self._burst(bullet.center_x,bullet.center_y,6,(255,220,140),70,190,1.2,2.2,.08,.2)
            bullet.remove_from_sprite_lists()
            if enemy.health <= 0:
                is_boss = isinstance(enemy, BossEnemy)
                self.score += (70 if is_boss else 12)+min(24,self.combo*2)
                self.combo += 1;  self.combo_timer = 2.0
                self._try_drop_powerup(enemy.center_x,enemy.center_y,is_boss)
                coin_val = (COIN_VALUE_BOSS if is_boss
                            else COIN_VALUE_SHOOTING if isinstance(enemy, ShootingEnemy)
                            else COIN_VALUE_ENEMY)
                self._drop_coin(enemy.center_x, enemy.center_y, coin_val)
                if is_boss:
                    self._burst(enemy.center_x,enemy.center_y,64,(255,100,80),70,320,2.3,4.8,.25,.65)
                else:
                    self._burst(enemy.center_x,enemy.center_y,24,(255,145,90),55,240,1.7,3.5,.2,.45)
                enemy.remove_from_sprite_lists()

        for b in list(self.enemy_bullets):
            if not arcade.check_for_collision(b, p): continue
            hx, hy = b.center_x, b.center_y;  b.remove_from_sprite_lists()
            if p.shield_active:
                self._burst(hx,hy,10,(110,230,255),80,220,1.2,2.8,.1,.24)
            else:
                p.health -= 10;  self.combo = 0
                self.damage_flash = max(self.damage_flash,0.95)
                self._burst(hx,hy,18,(255,95,95),90,260,1.6,3.4,.15,.32)

        touching = arcade.check_for_collision_with_lists(
            p, [self.enemies, self.shooting_enemies, self.bosses])
        if touching and self.contact_damage_timer <= 0:
            self.contact_damage_timer = CONTACT_DAMAGE_COOLDOWN
            if p.shield_active:
                self._burst(p.center_x,p.center_y,14,(100,230,255),70,180,1.6,3.2,.1,.24)
            else:
                p.health -= CONTACT_DAMAGE;  self.combo = 0
                self.damage_flash = max(self.damage_flash,1.0)
                self._burst(p.center_x,p.center_y,24,(255,80,80),90,260,1.8,4,.16,.36)

        for pu in list(self.powerups):
            if arcade.check_for_collision(pu, p):
                self._collect_powerup(pu.kind)
                c = POWERUP_COLORS[pu.kind]
                self._burst(pu.center_x,pu.center_y,20,(c[0],c[1],c[2]),70,240,1.4,3,.12,.32)
                pu.remove_from_sprite_lists()

        # ── Coin collection ──────────────────────────
        for coin in list(self.coins_list):
            if arcade.check_for_collision(coin, p):
                self._collect_coin(coin)

        if p.health <= 0 and self.game_state == STATE_PLAYING:
            self.game_state = STATE_GAMEOVER;  self.mouse_held = False
            self._burst(p.center_x,p.center_y,85,(255,75,75),80,360,2,5,.25,.75)
            self._save_progress()   # persist coins + upgrades to disk

    # ──────────────────────────────────────────────────
    #  AUTO TRIGGERS
    # ──────────────────────────────────────────────────

    def _check_auto_triggers(self):
        p  = self.player
        ne = len(self.enemies)+len(self.shooting_enemies)+len(self.bosses)
        if (not p.autofire_active and ne > AUTO_FIRE_ENEMY_THRESHOLD
                and p.inventory.get("autofire",0) > 0):
            p.inventory["autofire"] -= 1
            self._activate_powerup("autofire")
            self.notif_text  = f"AUTO-FIRE TRIGGERED  ({ne} enemies!)"
            self.notif_color = (255,130,255);  self.notif_timer = 1.6
        if (not p.shield_active
                and (p.health/p.max_health) <= AUTO_SHIELD_HEALTH_RATIO
                and p.inventory.get("shield",0) > 0):
            p.inventory["shield"] -= 1
            self._activate_powerup("shield")
            self.notif_text  = "SHIELD AUTO-ACTIVATED  (low HP!)"
            self.notif_color = (90,220,255);  self.notif_timer = 1.6

    # ──────────────────────────────────────────────────
    #  POWERUP HANDLERS
    # ──────────────────────────────────────────────────

    def _collect_powerup(self, kind: str):
        p = self.player
        if kind == "health":
            p.health = min(p.max_health, p.health+30)
            self.notif_text  = "+30 HEALTH!"
            self.notif_color = (130,255,130);  self.notif_timer = 1.4
            return
        if p.inventory[kind] < MAX_POWERUP_STORAGE:
            p.inventory[kind] += 1
            self.notif_text  = f"{POWERUP_LABELS[kind]} STORED  [{p.inventory[kind]}/{MAX_POWERUP_STORAGE}]"
            self.notif_color = _notif_color(kind);  self.notif_timer = 1.0
        else:
            self._activate_powerup(kind, immediate=True)

    def _collect_coin(self, coin: "Coin") -> None:
        self.coins      += coin.value
        self.run_coins  += coin.value
        self._burst(coin.center_x, coin.center_y,
                    8, (255, 220, 50), 55, 180, 1.0, 2.2, .06, .16)
        coin.remove_from_sprite_lists()

    def _activate_powerup(self, kind: str, immediate: bool = False):
        p = self.player
        msgs = {"shield":   ("SHIELD ONLINE!",       (110, 230, 255)),
                "autofire": ("AUTO-FIRE!",            (255, 130, 255)),
                "speed":    ("SPEED BOOST!",          (255, 220, 120)),
                "triple":   ("TRIPLE SHOT!",          (255, 180, 120)),
                "beam360":  ("360° BEAM BURST!",      (255, 120,  50)),
                "elec360":  ("⚡ 360° ELECTRIC MODE!", (160, 110, 255))}
        text, color = msgs.get(kind, (kind.upper() + "!", (255, 255, 255)))
        self.notif_text  = ("STORAGE FULL - " + text) if immediate else text
        self.notif_color = color;  self.notif_timer = 1.6
        setattr(p, f"{kind}_active", True)
        setattr(p, f"{kind}_timer",  POWERUP_DURATION
                if kind != "elec360" else ELECTRIC_360_DURATION)

    def _try_drop_powerup(self, x, y, boss=False):
        lucky_bonus = self.upgrades.get("lucky", 0) * 15
        threshold   = (100 if boss else DROP_CHANCE) + lucky_bonus
        if random.randint(1, 100) > threshold:
            return
        # Build pool: universal powerups + ship-specific if applicable
        pool = [k for k in POWERUP_TYPES
                if k not in BEAM_ONLY_POWERUPS and k not in ELECTRIC_ONLY_POWERUPS]
        if self.selected_ship in BEAM_SHIP_INDICES:
            pool += ["beam360"] * 2     # extra weight
        if self.selected_ship in ELECTRIC_SHIP_INDICES:
            pool += ["elec360"] * 2     # extra weight
        self.powerups.append(Powerup(x, y, random.choice(pool)))

    def _drop_coin(self, x: float, y: float, base_value: int) -> None:
        """Spawn a coin at (x, y) with value adjusted for Coin Doubler upgrade."""
        multiplier = 1.5 if self.upgrades.get("double_coins", 0) >= 1 else 1.0
        value = max(1, int(base_value * multiplier))
        # Scatter 1-3 coins so they fan out nicely
        count = 3 if base_value >= COIN_VALUE_BOSS else random.randint(1, 2)
        per   = max(1, value // count)
        for _ in range(count):
            ox = random.uniform(-18, 18)
            oy = random.uniform(-8,  12)
            self.coins_list.append(Coin(x + ox, y + oy, per))

    # ──────────────────────────────────────────────────
    #  SAVE / LOAD
    # ──────────────────────────────────────────────────

    def _save_progress(self) -> None:
        try:
            data = {"coins": self.coins, "upgrades": self.upgrades}
            SAVE_FILE.write_text(__import__("json").dumps(data))
        except OSError:
            pass

    def _load_progress(self) -> None:
        try:
            import json
            data = json.loads(SAVE_FILE.read_text())
            self.coins    = int(data.get("coins", 0))
            saved_upg     = data.get("upgrades", {})
            for item in SHOP_ITEMS:
                iid = item["id"]
                self.upgrades[iid] = min(
                    int(saved_upg.get(iid, 0)), item["max"])
        except (OSError, ValueError, KeyError):
            pass   # first run or corrupted save — start fresh

    # ──────────────────────────────────────────────────
    #  SPAWNING
    # ──────────────────────────────────────────────────

    def spawn_enemy(self, difficulty=0.0):
        hp = int(ENEMY_HEALTH*(1+0.35*difficulty))
        self.enemies.append(Enemy(random.randint(40,self.width-40), self.height+20, hp))

    def spawn_shooting_enemy(self, difficulty=0.0):
        hp = int(ENEMY_HEALTH*(1+0.35*difficulty))
        self.shooting_enemies.append(
            ShootingEnemy(random.randint(50,self.width-50), self.height+30, hp))

    def spawn_boss(self, difficulty=0.0):
        dp = self._dpreset
        hp = int(BOSS_HEALTH * (1 + 0.45*difficulty) * dp["boss_health_mult"])
        self.bosses.append(BossEnemy(random.randint(140,self.width-140), self.height+55, hp))
        dlabel = dp["label"]
        self.notif_text  = f"BOSS INCOMING!  [{dlabel}]"
        self.notif_color = (255,120,120);  self.notif_timer = 1.8

    # ══════════════════════════════════════════════════
    #  INPUT
    # ══════════════════════════════════════════════════

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x;  self.mouse_y = y

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        if self.game_state in (STATE_MENU, STATE_PAUSED):
            # difficulty button click
            for dkey, rect in self._diff_btns.items():
                l, r, b, t = rect
                if l<=x<=r and b<=y<=t:
                    self.selected_difficulty = dkey
                    self._dpreset = DIFFICULTY_PRESETS[dkey]
                    return
            # ship card selection
            for i, rect in self._ship_cards.items():
                l, r, b, t = rect
                if l<=x<=r and b<=y<=t and SHIPS[i]["available"]:
                    self.selected_ship = i;  return
            # button actions
            for name, rect in self._menu_btns.items():
                l, r, b, t = rect
                if l<=x<=r and b<=y<=t:
                    if name == "play":
                        if self.game_state == STATE_MENU:
                            self.setup()
                        else:
                            self.game_state = STATE_PLAYING
                            self.set_mouse_visible(False)
                    elif name == "quit":
                        self.game_state = STATE_MENU
                        self.set_mouse_visible(True)
                    elif name == "theme":
                        self.menu_theme = "light" if self.menu_theme=="dark" else "dark"
                    return
            return

        if self.game_state == STATE_PLAYING:
            self.mouse_held = True;  self.mouse_x = x;  self.mouse_y = y
            self._shoot_toward(x, y);  self.fire_timer = 0.0

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.mouse_held = False

    def on_key_press(self, key, modifiers):
        if   key == arcade.key.W: self.up        = True
        elif key == arcade.key.S: self.down      = True
        elif key == arcade.key.A: self.left_key  = True
        elif key == arcade.key.D: self.right_key = True

        elif key == arcade.key.ESCAPE:
            if self.game_state == STATE_PLAYING:
                self.game_state = STATE_PAUSED
                self.set_mouse_visible(True)
            elif self.game_state == STATE_PAUSED:
                self.game_state = STATE_PLAYING
                self.set_mouse_visible(False)
            # no ESC action in STATE_MENU or STATE_GAMEOVER

        elif key == arcade.key.H:
            if self.game_state in (STATE_PLAYING, STATE_PAUSED):
                self.show_hud = not self.show_hud

        elif key == arcade.key.R and self.game_state == STATE_GAMEOVER:
            self.setup()

        elif key == arcade.key.F11:
            self._toggle_fullscreen()

        elif key in POWERUP_KEYS:
            if self.game_state == STATE_PLAYING:
                self._use_stored_powerup(POWERUP_KEYS[key])

    def on_key_release(self, key, modifiers):
        if   key == arcade.key.W: self.up        = False
        elif key == arcade.key.S: self.down      = False
        elif key == arcade.key.A: self.left_key  = False
        elif key == arcade.key.D: self.right_key = False

    # ──────────────────────────────────────────────────
    #  FULLSCREEN
    # ──────────────────────────────────────────────────

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.set_fullscreen(self._fullscreen)
        if not self._fullscreen:
            self.set_size(SCREEN_WIDTH, SCREEN_HEIGHT)
            try:
                dw, dh = arcade.get_display_size()
                self.set_location((dw-SCREEN_WIDTH)//2, (dh-SCREEN_HEIGHT)//2)
            except (AttributeError, OSError):
                pass   # get_display_size not available on all platforms

    def _use_stored_powerup(self, kind: str):
        p = self.player
        if p.inventory.get(kind, 0) <= 0:
            self.notif_text  = f"NO {POWERUP_LABELS[kind]} IN STORAGE!"
            self.notif_color = (220,100,100);  self.notif_timer = 0.9
            return
        p.inventory[kind] -= 1
        self._activate_powerup(kind)


# ─────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────

def main():
    game = GameWindow()
    arcade.run()


if __name__ == "__main__":
    main()