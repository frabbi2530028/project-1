import arcade
import random
import math
from collections import deque
from PIL import Image
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

NORMAL_FIRE_RATE    = 0.22
AUTO_FIRE_RATE      = 0.075

POWERUP_DURATION    = 10.0
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
}

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
    },
    "light": {
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
        "available": False,
        "texture":   None,
        "tex_scale": 0.22,
        "spd_mult":  1.45,
        "hp_mult":   0.65,
    },
    {
        "name":      "TITAN",
        "tagline":   "Heavy destroyer",
        "stat_spd":  1, "stat_atk": 5, "stat_def": 5,
        "color":     (255, 155, 70),
        "available": False,
        "texture":   None,
        "tex_scale": 0.22,
        "spd_mult":  0.68,
        "hp_mult":   1.65,
    },
]

# ─────────────────────────────────────────────────────
#  TEXTURE CACHE
# ─────────────────────────────────────────────────────

_texture_cache: dict = {}


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


def load_texture_clean(path: str, scale: float = 1.0) -> arcade.Texture:
    """Load a sprite image, remove the background using flood-fill, and cache it."""
    key = (path, scale)
    if key in _texture_cache:
        return _texture_cache[key]
    img = Image.open(path).convert("RGBA")
    img = _remove_background(img, threshold=210)
    if scale != 1.0:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
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

POWERUP_TYPES  = ["health", "shield", "autofire", "speed", "triple"]
POWERUP_COLORS = {
    "health":   (0,   255, 90,  220),
    "shield":   (0,   190, 255, 220),
    "autofire": (255, 70,  255, 220),
    "speed":    (255, 220, 0,   220),
    "triple":   (255, 130, 0,   220),
}
POWERUP_LABELS = {
    "health":  "+HP",  "shield": "SHIELD", "autofire": "AUTO",
    "speed":   "SPEED", "triple": "TRIPLE",
}


class Powerup(arcade.Sprite):
    def __init__(self, x, y, kind: str):
        super().__init__()
        self.texture      = solid_texture(22, POWERUP_COLORS[kind])
        self.center_x     = x;  self.center_y = y
        self.kind         = kind
        self.change_y     = -POWERUP_FALL_SPEED
        self.wobble_phase = random.uniform(0.0, math.tau)

    def update(self, delta_time=1/60, *args, **kwargs):
        self.center_y     += self.change_y * delta_time
        self.wobble_phase += 4.0 * delta_time
        self.center_x     += math.sin(self.wobble_phase) * 18.0 * delta_time


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

        self.inventory = {"speed": 0, "shield": 0, "autofire": 0, "triple": 0}

    def get_speed(self):
        return PLAYER_SPEED * (1.65 if self.speed_active else 1.0)

    def update_powerups(self, delta):
        for attr in ("shield", "autofire", "speed", "triple"):
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
#  BULLETS
# ─────────────────────────────────────────────────────


class Bullet(arcade.Sprite):
    def __init__(self, sx, sy, angle_rad, speed=BULLET_SPEED):
        super().__init__()
        self.texture  = load_texture_clean("image/bullet.png", 0.1)
        self.center_x = sx;  self.center_y = sy
        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle    = math.degrees(angle_rad)
        self.life     = 2.5

    def update(self, delta_time=1/60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life     -= delta_time


class EnemyBullet(arcade.Sprite):
    def __init__(self, sx, sy, dest_x=None, dest_y=None,
                 angle_rad=None, speed=ENEMY_BULLET_SPEED):
        super().__init__()
        self.texture  = load_texture_clean("image/enemy_bullet.png", 0.1)
        self.center_x = sx;  self.center_y = sy
        if angle_rad is None:
            angle_rad = math.atan2(dest_y - sy, dest_x - sx)
        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle    = math.degrees(angle_rad)
        self.life     = 3.4

    def update(self, delta_time=1/60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life     -= delta_time


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
                          ("image/enemy.png", 0.12), ("image/shooting_enemy.png", 0.12),
                          ("image/boss.png", 0.2), ("image/bullet.png", 0.1),
                          ("image/enemy_bullet.png", 0.1)]:
            load_texture_clean(path, sc)
        for k in POWERUP_TYPES:
            solid_texture(22, POWERUP_COLORS[k])

        # ── UI/menu state ─────────────────────────────
        self.game_state    = STATE_MENU
        self.menu_theme         = "dark"
        self.selected_ship      = 0
        self.selected_difficulty = "medium"   # default
        self._menu_btns:  dict  = {}
        self._ship_cards: dict  = {}
        self._diff_btns:  dict  = {}

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

        self._build_starfield()

    # ──────────────────────────────────────────────────
    #  RESIZE
    # ──────────────────────────────────────────────────

    def on_resize(self, width, height):
        super().on_resize(width, height)
        w, h = width, height
        self.txt_score.x   = 22;      self.txt_score.y   = h-28
        self.txt_health.x  = 22;      self.txt_health.y  = h-74
        self.txt_active.x  = 22;      self.txt_active.y  = h-112
        self.txt_inv.x     = 22;      self.txt_inv.y     = h-132
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
        self.player           = Player()
        self.player.center_x  = self.width  // 2
        self.player.center_y  = self.height // 2
        self.player.max_health = int(PLAYER_HEALTH * ship["hp_mult"])
        self.player.health     = self.player.max_health
        self.player_list       = arcade.SpriteList()
        self.player_list.append(self.player)

        self.enemies          = arcade.SpriteList()
        self.shooting_enemies = arcade.SpriteList()
        self.bosses           = arcade.SpriteList()
        self.bullets          = arcade.SpriteList()
        self.enemy_bullets    = arcade.SpriteList()
        self.powerups         = arcade.SpriteList()

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
        spacing = 14
        total   = spacing * (max_v - 1)
        sx      = cx - total // 2
        for i in range(max_v):
            arcade.draw_circle_filled(sx + i*spacing, y, 5,
                                      c_on if i < value else c_off)

    def _draw_menu(self):
        theme_c  = THEMES[self.menu_theme]
        w, h = self.width, self.height
        t  = self.bg_time
        is_pause = (self.game_state == STATE_PAUSED)

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
        pw = min(int(w*0.80), 650)
        ph = min(int(h*0.92), 560 if is_pause else 525)
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
        n  = len(SHIPS)
        cw, ch = 158, 172
        gap    = 16
        total_cw = cw*n+gap*(n-1)
        cx0  = (w-total_cw)//2
        cy0  = div_y - 54 - ch        # card bottom y

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

            # ship preview
            pcx = cl+cw//2
            pcy = ct - int(ch*0.52)//2 - 8

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

            name_y = cb+int(ch*0.41)
            nc = theme_c["locked_text"] if not avl else \
                 (theme_c["card_sel_border"] if sel else theme_c["text"])
            arcade.draw_text(ship["name"], pcx+1, name_y-1, (0,0,0,100), 11,
                             anchor_x="center", bold=True,
                             font_name=("Futura","Century Gothic","Arial"))
            arcade.draw_text(ship["name"], pcx, name_y, nc, 11,
                             anchor_x="center", bold=True,
                             font_name=("Futura","Century Gothic","Arial"))

            if avl:
                arcade.draw_text(ship["tagline"], pcx, name_y-17,
                                 theme_c["text_dim"], 9, anchor_x="center",
                                 font_name=("Futura","Century Gothic","Arial"))
                sy = name_y-36
                for j,(lbl,val) in enumerate([("SPD",ship["stat_spd"]),
                                               ("ATK",ship["stat_atk"]),
                                               ("DEF",ship["stat_def"])]):
                    ry = sy-j*18
                    arcade.draw_text(lbl, cl+18, ry, theme_c["text_dim"], 8,
                                     anchor_y="center",
                                     font_name=("Courier New","Menlo","monospace"))
                    self._draw_stat_pips(cl+80, ry, val, 5, theme_c["stat_filled"], theme_c["stat_empty"])
                if sel:
                    arcade.draw_text("SELECTED", pcx, cb+9,
                                     theme_c["selected_badge"], 9, anchor_x="center", bold=True,
                                     font_name=("Futura","Century Gothic","Arial"))
            else:
                arcade.draw_text("COMING SOON", pcx, name_y-20,
                                 theme_c["locked_text"], 9, anchor_x="center",
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

        if is_pause:
            qw, qh = 196, 40
            qx = w//2-qw//2;  qy = by-qh-10
            hov_q = self._is_hovering(qx, qx+qw, qy, qy+qh)
            _draw_btn(qx, qw, qy, qh,
                      theme_c["btn_hover"] if hov_q else (*theme_c["btn_fill"][:3], 145),
                      (*theme_c["btn_border"][:3], 152), theme_c["btn_text_dim"],
                      "QUIT TO MENU", 14)
            self._menu_btns["quit"] = (qx, qx+qw, qy, qy+qh)

        # theme toggle — always at bottom
        tw, th2 = 190, 32
        tx = w//2-tw//2;  ty2 = pb+16
        hov_t = self._is_hovering(tx, tx+tw, ty2, ty2+th2)
        _draw_btn(tx, tw, ty2, th2,
                  theme_c["btn_hover"] if hov_t else (*theme_c["btn_fill"][:3], 145),
                  (*theme_c["btn_border"][:3], 158),
                  theme_c["toggle_text"],
                  "[ DARK MODE ]" if self.menu_theme=="dark" else "[ LIGHT MODE ]",
                  12)
        self._menu_btns["theme"] = (tx, tx+tw, ty2, ty2+th2)

    # ══════════════════════════════════════════════════
    #  GAME-WORLD DRAW HELPERS
    # ══════════════════════════════════════════════════

    def _draw_bg_space(self):
        w, h = self.width, self.height
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, BG_COLOR)
        pulse = (math.sin(self.bg_time*0.7)+1)*0.5
        arcade.draw_circle_filled(w*0.19,h*0.83,250+20*pulse,     (40, 85,190,42))
        arcade.draw_circle_filled(w*0.84,h*0.28,280+30*(1-pulse), (150,45,170,34))
        arcade.draw_circle_filled(w*0.53,h*1.07,280,               (30,160,200,18))
        off = (self.bg_time*14)%28
        for y in range(-30, h+30, 28):
            arcade.draw_line(0,y+off,w,y+off-18,(30,46,78,26),1)
        for s in self.stars:
            tw = 0.55+0.45*math.sin(self.bg_time*s["twinkle"]+s["phase"])
            al = max(20,min(255,int(s["alpha"]*tw)))
            arcade.draw_circle_filled(s["x"],s["y"],s["size"],(205,228,255,al))

    def _draw_entity_glows(self):
        p = self.player
        c = (255,230,90,82) if p.speed_active else (95,200,255,68)
        arcade.draw_circle_filled(p.center_x, p.center_y, 34, c)
        for e in self.enemies:
            arcade.draw_circle_filled(e.center_x,e.center_y,24,(255,92,92,45))
        for e in self.shooting_enemies:
            arcade.draw_circle_filled(e.center_x,e.center_y,26,(255,130,90,55))
        for b in self.bosses:
            r = 54+8*math.sin(self.bg_time*2.5)
            arcade.draw_circle_filled(b.center_x,b.center_y,r,(255,70,70,55))

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

        # ── Invisible vignette edges for readability ──
        # (subtle dark gradient around borders so text floats on any BG)
        for i in range(5):
            a = 28 - i*5
            arcade.draw_lrbt_rectangle_filled(0, w, h-i*12, h, (0,0,0,a))
            arcade.draw_lrbt_rectangle_filled(0, w, 0, i*12, (0,0,0,a))
            arcade.draw_lrbt_rectangle_filled(0, i*12, 0, h,  (0,0,0,a))

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

        # ── HP bar ─────────────────────────────────
        hr   = max(0.0, p.health/p.max_health)
        hc   = (60,235,110) if hr>0.55 else (255,195,55) if hr>0.28 else (255,60,60)
        # label
        self._txt_shadow("HEALTH", 22, h-56, (120,165,230,180), 9, font_ui)
        # segmented bar
        self._draw_seg_bar(22, h-80, 210, 9, hr, hc, segs=21, gap=2)
        # neon glow line along the filled portion
        if hr > 0:
            gw = int(210*hr)
            arcade.draw_lrbt_rectangle_filled(22, 22+gw, h-72, h-71,
                                               (*hc[:3], int(160*hr)))
        # numbers
        self.txt_health.text  = f"{int(max(0,p.health))}  /  {p.max_health}"
        self.txt_health.color = (*hc[:3], 210)
        self.txt_health.draw()

        # ── Active power-ups ───────────────────────
        active_pills = []
        if p.shield_active:   active_pills.append(("SHIELD",  p.shield_timer,   (55,215,255)))
        if p.autofire_active: active_pills.append(("AUTO",    p.autofire_timer,  (235,80,255)))
        if p.speed_active:    active_pills.append(("SPEED",   p.speed_timer,     (255,215,40)))
        if p.triple_active:   active_pills.append(("TRIPLE",  p.triple_timer,    (255,140,40)))

        pill_x = 22
        pill_y = h-108
        for label, timer, pc in active_pills:
            pw = len(label)*7 + 44
            arcade.draw_lrbt_rectangle_filled(pill_x, pill_x+pw, pill_y-1, pill_y+16,
                                               (*pc, 40))
            arcade.draw_lrbt_rectangle_outline(pill_x, pill_x+pw, pill_y-1, pill_y+16,
                                                (*pc, 165), 1)
            self._txt_shadow(f"{label} {timer:.0f}s", pill_x+6, pill_y+3,
                             (*pc, 230), 9, font_ui)
            pill_x += pw + 6

        # ── Inventory ──────────────────────────────
        inv  = p.inventory
        inv_data = [
            ("1", "SPD", inv["speed"],   (255,215,40)),
            ("2", "SHD", inv["shield"],  (55,215,255)),
            ("3", "AUT", inv["autofire"],(235,80,255)),
            ("4", "TRP", inv["triple"],  (255,140,40)),
        ]
        ix = 22
        iy = h - 132
        for key, lbl, cnt, ic in inv_data:
            dim = cnt == 0
            fc  = (*ic, 55 if dim else 130)
            bc  = (*ic, 70 if dim else 175)
            tc  = (*ic, 120 if dim else 230)
            arcade.draw_lrbt_rectangle_filled(ix, ix+52, iy-1, iy+14, fc)
            arcade.draw_lrbt_rectangle_outline(ix, ix+52, iy-1, iy+14, bc, 1)
            self._txt_shadow(f"[{key}]{lbl}:{cnt}", ix+4, iy+2, tc, 8, font_num)
            ix += 58

        # ══ TOP-RIGHT ════════════════════════════════

        # ── Timer ──────────────────────────────────
        self._txt_shadow("TIME", w-18, h-14, (120,165,230,175), 9, font_ui,
                         anchor_x="right")
        self.txt_timer.text = f"{self.time_alive:06.1f}s"
        self.txt_timer.draw()

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
            # subtle glow behind notification
            arcade.draw_lrbt_rectangle_filled(
                w//2-240, w//2+240, h//2+74, h//2+106, (0,0,0,int(a*0.35)))
            self.txt_notif.text  = self.notif_text
            self.txt_notif.color = (*c[:3], a)
            self.txt_notif.draw()

    def _draw_crosshair(self):
        x, y = self.mouse_x, self.mouse_y
        arcade.draw_circle_outline(x,y,13,(130,220,255,185),2)
        for x1,y1,x2,y2 in [(x-20,y,x-8,y),(x+8,y,x+20,y),
                              (x,y-20,x,y-8),(x,y+8,x,y+20)]:
            arcade.draw_line(x1,y1,x2,y2,(130,220,255,185),2)

    # ══════════════════════════════════════════════════
    #  ON DRAW
    # ══════════════════════════════════════════════════

    def on_draw(self):
        w, h = self.width, self.height
        self.clear()

        if self.game_state == STATE_MENU:
            self._draw_menu()
            return

        # Playing / paused / gameover — always draw the world
        self._draw_bg_space()
        self._draw_entity_glows()
        self.powerups.draw()
        self.player_list.draw()
        self.enemies.draw();  self.shooting_enemies.draw();  self.bosses.draw()
        self.bullets.draw();  self.enemy_bullets.draw()

        for b in self.bullets:
            arcade.draw_circle_filled(b.center_x,b.center_y,6,(255,200,110,55))
        for b in self.enemy_bullets:
            arcade.draw_circle_filled(b.center_x,b.center_y,7,(255,85,85,55))

        if self.player.shield_active:
            rr = 38+2.5*math.sin(self.bg_time*9)
            arcade.draw_circle_outline(self.player.center_x,self.player.center_y,
                                        rr,(90,235,255,230),3)

        for pu in self.powerups:
            arcade.draw_text(POWERUP_LABELS[pu.kind],pu.center_x,pu.center_y-8,
                             arcade.color.WHITE,9,anchor_x="center")

        self._draw_enemy_health_bars()
        self._draw_particles()
        self._draw_hud()

        if self.damage_flash > 0:
            arcade.draw_lrbt_rectangle_filled(0,w,0,h,
                (255,65,65,int(170*self.damage_flash)))

        self._draw_crosshair()

        if self.game_state == STATE_GAMEOVER:
            # ── Full-screen blackout (solid enough to hide all sprites) ──
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (3, 5, 18, 210))

            # ── Central dark card ────────────────────────────────────────
            cw_ = min(560, int(w * 0.72))
            ch_ = 310
            cx_ = (w - cw_) // 2
            cy_ = h // 2 - ch_ // 2
            # card shadow
            arcade.draw_lrbt_rectangle_filled(
                cx_+6, cx_+cw_+6, cy_-6, cy_+ch_-6, (0, 0, 0, 90))
            # card body
            arcade.draw_lrbt_rectangle_filled(
                cx_, cx_+cw_, cy_, cy_+ch_, (8, 12, 32, 235))
            # card border with red glow
            arcade.draw_lrbt_rectangle_outline(
                cx_, cx_+cw_, cy_, cy_+ch_, (200, 40, 40, 180), 2)
            arcade.draw_lrbt_rectangle_outline(
                cx_+4, cx_+cw_-4, cy_+4, cy_+ch_-4, (200, 40, 40, 55), 1)
            # corner accents
            csz = 18
            for (ax, ay, dx, dy) in [(cx_, cy_, -1,-1), (cx_+cw_, cy_, 1,-1),
                                      (cx_, cy_+ch_, -1, 1), (cx_+cw_, cy_+ch_, 1, 1)]:
                arcade.draw_line(ax, ay, ax+dx*csz, ay, (255,60,60,160), 2)
                arcade.draw_line(ax, ay, ax, ay+dy*csz, (255,60,60,160), 2)

            # ── Content (all Y inside the card) ─────────────────────────
            mid_x  = w // 2
            top_y  = cy_ + ch_ - 58    # "GAME OVER" title
            lbl_y  = cy_ + ch_ - 128   # "FINAL SCORE" label
            num_y  = cy_ + ch_ - 172   # score number
            div_y_ = cy_ + ch_ - 200   # thin divider line
            rst_y  = cy_ + 22          # "PRESS R" restart prompt

            # decorative top/bottom lines inside card
            arcade.draw_line(cx_+24, top_y-14, cx_+cw_-24, top_y-14,
                             (200, 40, 40, 100), 1)
            arcade.draw_line(cx_+24, div_y_,   cx_+cw_-24, div_y_,
                             (80, 100, 160, 100), 1)

            # GAME OVER
            self._txt_shadow("GAME OVER", mid_x, top_y,
                             (255, 50, 50, 255), 52,
                             self._FONT_UI, anchor_x="center", bold=True)

            # FINAL SCORE label
            self._txt_shadow("FINAL  SCORE", mid_x, lbl_y,
                             (130, 165, 215, 200), 12,
                             self._FONT_UI, anchor_x="center")

            # Score value — large, bright, monospace
            self._txt_shadow(f"{self.score:,}", mid_x, num_y,
                             (210, 235, 255, 245), 36,
                             self._FONT_NUM, anchor_x="center", bold=True)

            # PRESS R TO RESTART
            self._txt_shadow("PRESS  R  TO  RESTART", mid_x, rst_y,
                             (120, 158, 215, 195), 15,
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
            ang = math.atan2(-p.change_y,-p.change_x)+random.uniform(-0.5,0.5)
            s2  = random.uniform(80,160)
            self._add_particle(
                p.center_x+random.uniform(-4,4), p.center_y-8+random.uniform(-3,3),
                math.cos(ang)*s2, math.sin(ang)*s2,
                random.uniform(1.4,2.8), random.uniform(0.12,0.24), (120,205,255), 0.9)

        # firing
        firing = self.mouse_held or p.autofire_active
        if firing:
            rate = AUTO_FIRE_RATE if p.autofire_active else NORMAL_FIRE_RATE
            self.fire_timer += delta
            while self.fire_timer >= rate:
                if p.autofire_active:
                    tgt = self._nearest_enemy()
                    self._shoot_toward(tgt.center_x if tgt else self.mouse_x,
                                       tgt.center_y if tgt else self.mouse_y)
                else:
                    self._shoot_toward(self.mouse_x, self.mouse_y)
                self.fire_timer -= rate

        self.bullets.update(delta);  self.enemy_bullets.update(delta)
        self.powerups.update(delta)

        ww, hh = self.width, self.height
        for b in list(self.bullets):
            if b.life<=0 or b.right<-30 or b.left>ww+30 or b.top<-30 or b.bottom>hh+30:
                b.remove_from_sprite_lists()
        for b in list(self.enemy_bullets):
            if b.life<=0 or b.right<-30 or b.left>ww+30 or b.top<-30 or b.bottom>hh+30:
                b.remove_from_sprite_lists()
        for pu in list(self.powerups):
            if pu.top < -10: pu.remove_from_sprite_lists()

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
        all_e = list(self.enemies)+list(self.shooting_enemies)+list(self.bosses)
        if not all_e: return None
        px, py = self.player.center_x, self.player.center_y
        return min(all_e, key=lambda e: math.hypot(e.center_x-px, e.center_y-py))

    def _shoot_toward(self, tx, ty):
        px, py = self.player.center_x, self.player.center_y
        base   = math.atan2(ty-py, tx-px)
        for off in ([-0.18,0.0,0.18] if self.player.triple_active else [0.0]):
            ang = base+off
            self.bullets.append(Bullet(px,py,ang))
            self._spawn_muzzle(px,py,ang)

    def update_enemies(self, delta, difficulty):
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

        if p.health <= 0 and self.game_state == STATE_PLAYING:
            self.game_state = STATE_GAMEOVER;  self.mouse_held = False
            self._burst(p.center_x,p.center_y,85,(255,75,75),80,360,2,5,.25,.75)

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

    def _activate_powerup(self, kind: str, immediate: bool = False):
        p = self.player
        msgs = {"shield":("SHIELD ONLINE!",(110,230,255)),
                "autofire":("AUTO-FIRE!",(255,130,255)),
                "speed":("SPEED BOOST!",(255,220,120)),
                "triple":("TRIPLE SHOT!",(255,180,120))}
        text, color = msgs[kind]
        self.notif_text  = ("STORAGE FULL - "+text) if immediate else text
        self.notif_color = color;  self.notif_timer = 1.4
        setattr(p, f"{kind}_active", True)
        setattr(p, f"{kind}_timer",  POWERUP_DURATION)

    def _try_drop_powerup(self, x, y, boss=False):
        if random.randint(1,100) <= (100 if boss else DROP_CHANCE):
            self.powerups.append(Powerup(x, y, random.choice(POWERUP_TYPES)))

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