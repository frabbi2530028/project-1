from game_support import *
from game_window_maze import MazeModeMixin

# ===== Merged from game_window.py =====
import arcade
import math
import random


FONT_UI_DISPLAY = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
FONT_UI_MENU = ("Avenir Next", "Verdana", "Trebuchet MS", "Arial")
FONT_NUMERIC = ("SF Mono", "Menlo", "Monaco", "Courier New", "monospace")

def _draw_btn(x, w, y, h, fill, border, text_color, label, font_size):
    arcade.draw_lrbt_rectangle_filled(x, x + w, y, y + h, fill)
    arcade.draw_lrbt_rectangle_outline(x, x + w, y, y + h, border, 2)
    cx = x + w // 2;  cy = y + h // 2
    sa = min(175, int((text_color[3] if len(text_color)==4 else 255)*0.45))
    arcade.draw_text(label, cx+2, cy-2, (0,0,0,sa), font_size,
                     anchor_x="center", anchor_y="center", bold=True, font_name=FONT_UI_MENU)
    arcade.draw_text(label, cx, cy, text_color, font_size,
                     anchor_x="center", anchor_y="center", bold=True, font_name=FONT_UI_MENU)


def _notif_color(kind: str) -> tuple:
    return {"speed":(255,220,120),"shield":(110,230,255),
            "triple":(255,180,120),
            "health":(130,255,130),
            "breach":(255,205,80)}.get(kind,(255,255,255))


class GameWindow(MazeModeMixin, arcade.Window):

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
        for lvl in LEVELS:
            for scale_key in ("boss_texture_scale", "boss_portrait_scale"):
                try:
                    load_texture_clean(lvl["boss_texture"], lvl[scale_key])
                except (FileNotFoundError, OSError):
                    pass
        for k in POWERUP_TYPES:
            solid_texture(22, POWERUP_COLORS[k])

        _preload_powerup_textures()

        # ── UI/menu state ─────────────────────────────
        self.game_state    = STATE_MODE_SELECT
        self.selected_mode      = None          # "normal" | "maze" | "multiplayer"
        self._mode_btns:  dict  = {}
        self.selected_maze_preset: str = "classic"
        self._maze_preset_btns: dict   = {}
        self.maze_preset: dict | None  = None   # active preset params
        self.menu_theme         = "dark"
        self.selected_ship      = 0
        self.selected_difficulty = "medium"
        self._menu_btns:  dict  = {}
        self._ship_cards: dict  = {}
        self._diff_btns:  dict  = {}
        self._shop_btns:  dict  = {}
        self._shop_return_state = STATE_MENU
        self._pause_return_state: str | None = None
        self.shop_feedback      = ""
        self.shop_feedback_color = (160, 180, 215, 180)

        # ── Level system ──────────────────────────────
        self.selected_level:    int  = 0
        self.level_enemies_remaining: int = 0
        self.level_shooting_remaining: int = 0
        self.level_boss_spawned: bool = False
        self.level_complete:     bool = False
        self._level_clear_timer: float = 0.0
        self.best_scores:  dict = {}          # level_index → best score
        self.completed_levels: set = set()    # indices of boss-beaten levels

        # ── Currency / Shop ───────────────────────────
        self.coins:    int  = 0          # total saved coins
        self.run_coins: int = 0          # coins earned this run
        self.upgrades: dict = {item["id"]: 0 for item in SHOP_ITEMS}
        self._load_progress()            # restore coins + upgrades from disk

        # ── HUD text objects ──────────────────────────
        FONT_UI  = FONT_UI_DISPLAY
        FONT_NUM = FONT_NUMERIC
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
            "WASD · Mouse Aim · 1-3 Power-ups · 4 Maze Breach · 5 Reaper Special · H HUD · F11 Fullscreen · R Restart · ESC Menu",
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
        self.bullets = self.enemy_bullets = self.enemy_elec_bolts = self.powerups = None

        # ── Runtime vars ─────────────────────────────
        self.score       = 0
        self.show_hud    = True
        self._held_move_keys: set[int] = set()
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
        self._screen_transition: dict | None = None

        # ── Maze mode state ───────────────────────────
        self.maze_grid:       MazeGrid | None = None
        self.maze_cell_size:  int   = MAZE_CELL_SIZE
        self.maze_origin:     tuple = (0, 0)
        self.maze_level:      int   = 0
        self.maze_enemies:    list  = []
        self.maze_score:      int   = 0
        self.maze_exit_col:   int   = 0
        self.maze_exit_row:   int   = 0
        self.maze_exit_reached: bool = False
        # ── Maze scrolling camera (world-space bottom-left corner) ──
        self.maze_cam_x:     float = 0.0
        self.maze_cam_y:     float = 0.0
        self.maze_camera = None   # arcade.camera.Camera2D, created in setup_maze

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
        self.enemy_elec_bolts = arcade.SpriteList()
        self.powerups         = arcade.SpriteList()
        self.coins_list       = arcade.SpriteList()   # ← coin sprites on screen

        self.run_coins = 0   # reset per-run coin counter

        # ── Level counters ────────────────────────────
        lvl = LEVELS[self.selected_level]
        self.level_enemies_remaining  = lvl["regular_enemies"]
        self.level_shooting_remaining = lvl["shooting_enemies"]
        self.level_boss_spawned  = False
        self.level_complete      = False
        self._level_clear_timer  = 0.0

        self.score       = 0
        self.show_hud    = True
        self.enemy_spawn = self.shooting_spawn = self.boss_spawn = 0.0
        self.mouse_held  = False;  self.fire_timer = 0.0
        self.notif_text  = "";  self.notif_timer = 0.0
        self.notif_color = (255,255,110)
        self._clear_movement_input()
        self.damage_flash = 0.0;  self.contact_damage_timer = 0.0
        self.time_alive   = 0.0
        self.combo        = 0;  self.combo_timer = 0.0
        self.particles    = []
        self.beams        = []
        self.elec_bolts   = arcade.SpriteList()
        self.boss_on_screen = False   # lockout flag: True while any boss lives

        # Cache the active preset so AI code can read it cheaply
        self._dpreset = DIFFICULTY_PRESETS[self.selected_difficulty]

        self._pause_return_state = None
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

    @staticmethod
    def _ease_out_cubic(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return 1.0 - (1.0 - value) ** 3

    @staticmethod
    def _ease_out_back(value: float) -> float:
        value = max(0.0, min(1.0, value))
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * (value - 1.0) ** 3 + c1 * (value - 1.0) ** 2

    def _start_screen_transition(self, from_state: str, to_state: str) -> None:
        self._screen_transition = {
            "from": from_state,
            "to": to_state,
            "time": 0.0,
            "duration": 0.48,
        }

    def _update_screen_transition(self, delta: float) -> None:
        if not self._screen_transition:
            return

        self._screen_transition["time"] += delta
        if self._screen_transition["time"] >= self._screen_transition["duration"]:
            self.game_state = self._screen_transition["to"]
            self._screen_transition = None

    # ══════════════════════════════════════════════════
    #  MENU DRAWING
    # ══════════════════════════════════════════════════

    def _is_hovering(self, l, r, b, t):
        return l <= self.mouse_x <= r and b <= self.mouse_y <= t

    @staticmethod
    def _draw_stat_pips(cx: int, y: int, value: int, max_v: int,
                        c_on: tuple, c_off: tuple, max_width: int | None = None) -> None:
        spacing = 18
        if max_width is not None and max_v > 1:
            spacing = min(spacing, max(12, int(max_width / (max_v - 1))))
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

    def _draw_pause_ship_summary(self, left: int, right: int, bottom: int, top: int,
                                 theme_c: dict, t: float) -> None:
        ship = SHIPS[self.selected_ship]
        width = right - left
        height = top - bottom
        font_ui_local = FONT_UI_MENU
        header_size = 10 if height >= 86 else 9
        name_size = 17 if height >= 96 else 14
        tag_size = 10 if height >= 86 else 9
        stat_label_size = 9 if height >= 86 else 8
        preview_radius = min(32, max(22, int(height * 0.30)))
        preview_offset_top = min(48, int(height * 0.42))
        tagline_offset_top = min(70, int(height * 0.64))
        stat_y = bottom + max(20, int(height * 0.24))

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, theme_c["card_fill"])
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, theme_c["card_sel_border"], 2)

        pulse = 0.5 + 0.5 * math.sin(t * 4.0)
        arcade.draw_lrbt_rectangle_outline(
            left - 2, right + 2, bottom - 2, top + 2,
            (*ship["color"], int(45 + 35 * pulse)), 2
        )

        preview_x = left + min(58, width * 0.12)
        preview_y = bottom + height * 0.52
        arcade.draw_circle_filled(preview_x, preview_y, preview_radius, (*ship["color"], 32))

        if ship["texture"]:
            tex = load_texture_clean(ship["texture"], ship["tex_scale"])
            draw_y = preview_y + math.sin(t * 2.8) * 3
            _draw_texture_fitted(tex, preview_x, draw_y, preview_radius * 1.75, preview_radius * 1.75)

        separator_x = left + min(108, width * 0.24)
        arcade.draw_line(separator_x, bottom + 14, separator_x, top - 14, theme_c["divider"], 1)

        name_x = separator_x + 16
        arcade.draw_text("CURRENT SHIP", name_x, top - 24, theme_c["text_dim"], header_size,
                         bold=True, font_name=font_ui_local)
        arcade.draw_text(ship["name"], name_x + 1, top - preview_offset_top - 1, (0, 0, 0, 95), name_size,
                         bold=True, font_name=font_ui_local)
        arcade.draw_text(ship["name"], name_x, top - preview_offset_top, theme_c["card_sel_border"], name_size,
                         bold=True, font_name=font_ui_local)
        arcade.draw_text(ship["tagline"], name_x, top - tagline_offset_top, theme_c["text"], tag_size,
                         font_name=font_ui_local)

        stats_left = max(name_x + 20, left + width * 0.46)
        stats_right = right - 26
        stat_step = (stats_right - stats_left) / 3
        for idx, (label, value) in enumerate((
            ("SPD", ship["stat_spd"]),
            ("ATK", ship["stat_atk"]),
            ("DEF", ship["stat_def"]),
        )):
            cx = stats_left + stat_step * (idx + 0.5)
            arcade.draw_text(label, cx, stat_y + 16, theme_c["text_dim"], stat_label_size,
                             anchor_x="center", bold=True,
                             font_name=FONT_NUMERIC)
            self._draw_stat_pips(cx, stat_y, value, 5,
                                 theme_c["stat_filled"], theme_c["stat_empty"], 72)

    def _draw_menu(self, anim: dict | None = None, draw_background: bool = True):
        anim = anim or {}
        is_pause = (self.game_state == STATE_PAUSED)
        # Pause overlay always uses the dark theme for a clean dark panel look.
        # Only the main menu respects the user's light/dark preference.
        theme_c  = THEMES["dark"] if is_pause else THEMES[self.menu_theme]
        w, h = self.width, self.height
        t  = self.bg_time
        panel_scale = 1.0 if is_pause else anim.get("scale", 1.0)
        panel_offset_y = 0.0 if is_pause else anim.get("offset_y", 0.0)

        def scaled(value: float, minimum: int = 1) -> int:
            return max(minimum, int(round(value * panel_scale)))

        # ── Background ───────────────────────────────
        if draw_background:
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
        base_pw = min(int(w * (0.88 if is_pause else 0.92)), 820 if is_pause else 980)
        base_ph = min(int(h*0.95), 580 if is_pause else 620)
        pw = int(base_pw * panel_scale)
        ph = int(base_ph * panel_scale)
        pl = (w-pw)//2;  pr = pl+pw
        pb = int((h-ph)//2 + panel_offset_y);  ptop = pb+ph

        arcade.draw_lrbt_rectangle_filled(pl+7,pr+7,pb-7,ptop-7,(0,0,0,70))
        arcade.draw_lrbt_rectangle_filled(pl,pr,pb,ptop, theme_c["panel_fill"])
        arcade.draw_lrbt_rectangle_outline(pl,pr,pb,ptop, theme_c["panel_border"], 2)
        arcade.draw_lrbt_rectangle_outline(pl+5,pr-5,pb+5,ptop-5, theme_c["panel_inner"], 1)

        # corner accents
        ac = theme_c["panel_border"];  accent_size = scaled(24)
        for (ax,ay,dx,dy) in [(pl,pb,-1,-1),(pr,pb,1,-1),(pl,ptop,-1,1),(pr,ptop,1,1)]:
            arcade.draw_line(ax,ay,ax+dx*accent_size,ay,          ac,2)
            arcade.draw_line(ax,ay,ax,      ay+dy*accent_size,    ac,2)

        # ── Title ────────────────────────────────────
        font_display = FONT_UI_DISPLAY
        font_ui_local = FONT_UI_MENU
        title = "PAUSED" if is_pause else "NEON  DRIFT"
        ty    = ptop - 52
        arcade.draw_text(title, w//2+4, ty-4, theme_c["title_shadow"], scaled(42),
                         anchor_x="center", bold=True, font_name=font_display)
        arcade.draw_text(title, w//2,   ty,   theme_c["title"],        scaled(42),
                         anchor_x="center", bold=True, font_name=font_display)
        sub = "GAME SUSPENDED" if is_pause else "S P A C E   S H O O T E R"
        arcade.draw_text(sub, w//2+1, ty-31, (0,0,0,80), scaled(12),
                         anchor_x="center", font_name=font_ui_local)
        arcade.draw_text(sub, w//2, ty-30, theme_c["subtitle"], scaled(12),
                         anchor_x="center", font_name=font_ui_local)

        div_y = ptop - 97
        arcade.draw_line(pl+22, div_y, pr-22, div_y, theme_c["divider"], 1)
        self._ship_cards = {}
        self._menu_btns = {}
        self._diff_btns = {}

        if is_pause:
            pause_scale = max(0.78, min(1.0, ph / 580))
            pad_bottom = max(12, int(16 * pause_scale))
            gap_small = max(8, int(10 * pause_scale))
            gap_medium = max(10, int(12 * pause_scale))
            diff_label_gap = max(12, int(16 * pause_scale))
            info_gap = max(14, int(18 * pause_scale))
            info_top = div_y - info_gap

            tw, th2 = 190, max(26, int(32 * pause_scale))
            tx = w//2 - tw//2
            ty2 = pb + pad_bottom

            qw, qh = 196, max(32, int(40 * pause_scale))
            qx = w//2 - qw//2
            qy = ty2 + th2 + gap_small

            rw, rh = 196, max(32, int(40 * pause_scale))
            rx = w//2 - rw//2
            ry = qy + qh + gap_small

            sw, sh2 = 230, max(30, int(38 * pause_scale))
            sx2 = w//2 - sw//2
            sy2 = ry + rh + gap_small

            bw, bh = 230, max(40, int(50 * pause_scale))
            bx = w//2 - bw//2
            by = sy2 + sh2 + gap_medium

            dw, dh = max(96, int(118 * pause_scale)), max(30, int(38 * pause_scale))
            dgap = 10
            dtotal = dw * 3 + dgap * 2
            dx0 = (w - dtotal) // 2
            diff_by = by + bh + info_gap
            diff_label_y = diff_by + dh + diff_label_gap

            info_bottom = diff_label_y + info_gap
            self._draw_pause_ship_summary(pl + 22, pr - 22, info_bottom, info_top, theme_c, t)

            diff_font_size = 12 if pause_scale > 0.9 else 11
            diff_btn_font = 14 if pause_scale > 0.9 else 13

            arcade.draw_text("RUN DIFFICULTY", w//2 + 1, diff_label_y - 1, (0, 0, 0, 90), diff_font_size,
                             anchor_x="center", bold=True, font_name=font_ui_local)
            arcade.draw_text("RUN DIFFICULTY", w//2, diff_label_y,
                             theme_c["text"], diff_font_size, anchor_x="center", bold=True, font_name=font_ui_local)

            for di, dkey in enumerate(DIFFICULTY_ORDER):
                preset = DIFFICULTY_PRESETS[dkey]
                dleft = dx0 + di * (dw + dgap)
                dright = dleft + dw
                dtop = diff_by + dh
                sel_d = (dkey == self.selected_difficulty)
                hov_d = self._is_hovering(dleft, dright, diff_by, dtop)

                dc = preset["color"]
                if sel_d:
                    fill = (*dc, 210)
                    border = (*dc, 255)
                    bthk = 3
                    tcolor = (255, 255, 255)
                elif hov_d:
                    fill = (*dc[:3], 80)
                    border = (*dc, 200)
                    bthk = 2
                    tcolor = (255, 255, 255)
                else:
                    fill = (*dc[:3], 30)
                    border = (*dc[:3], 110)
                    bthk = 1
                    tcolor = (*dc[:3], 200)

                arcade.draw_lrbt_rectangle_filled(dleft, dright, diff_by, dtop, fill)
                arcade.draw_lrbt_rectangle_outline(dleft, dright, diff_by, dtop, border, bthk)
                if sel_d:
                    pulse = 0.5 + 0.5 * math.sin(t * 4.0)
                    arcade.draw_lrbt_rectangle_outline(
                        dleft - 3, dright + 3, diff_by - 3, dtop + 3, (*dc, int(50 + 45 * pulse)), 2
                    )
                sa_ = min(175, int((tcolor[3] if len(tcolor) == 4 else 255) * 0.4))
                arcade.draw_text(preset["label"], dleft + dw//2 + 1, diff_by + dh//2 - 1,
                                 (0, 0, 0, sa_), diff_btn_font, anchor_x="center", anchor_y="center",
                                 bold=True, font_name=font_ui_local)
                arcade.draw_text(preset["label"], dleft + dw//2, diff_by + dh//2,
                                 tcolor, diff_btn_font, anchor_x="center", anchor_y="center",
                                 bold=True, font_name=font_ui_local)
                self._diff_btns[dkey] = (dleft, dright, diff_by, dtop)

            hov_p = self._is_hovering(bx, bx+bw, by, by+bh)
            _draw_btn(bx, bw, by, bh,
                      theme_c["btn_hover"] if hov_p else theme_c["btn_fill"],
                      theme_c["btn_border"], theme_c["btn_text"],
                      "[ RESUME ]", 20 if pause_scale > 0.9 else 18)
            self._menu_btns["play"] = (bx, bx+bw, by, by+bh)

            hov_s = self._is_hovering(sx2, sx2+sw, sy2, sy2+sh2)
            coin_label = f"[ SHOP ]  $ {self.coins:,}"
            _draw_btn(sx2, sw, sy2, sh2,
                      theme_c["btn_hover"] if hov_s else (*theme_c["btn_fill"][:3], 200),
                      (255, 210, 30, 220), (255, 215, 40, 255),
                      coin_label, 14 if pause_scale > 0.9 else 13)
            self._menu_btns["shop"] = (sx2, sx2+sw, sy2, sy2+sh2)

            hov_r = self._is_hovering(rx, rx+rw, ry, ry+rh)
            _draw_btn(rx, rw, ry, rh,
                      theme_c["btn_hover"] if hov_r else (145, 40, 40, 145),
                      (255, 110, 110, 190), theme_c["btn_text_dim"],
                      "RESET RUN", 14 if pause_scale > 0.9 else 13)
            self._menu_btns["reset"] = (rx, rx+rw, ry, ry+rh)

            hov_q = self._is_hovering(qx, qx+qw, qy, qy+qh)
            _draw_btn(qx, qw, qy, qh,
                      theme_c["btn_hover"] if hov_q else (*theme_c["btn_fill"][:3], 145),
                      (*theme_c["btn_border"][:3], 152), theme_c["btn_text_dim"],
                      "QUIT TO MENU", 14 if pause_scale > 0.9 else 13)
            self._menu_btns["quit"] = (qx, qx+qw, qy, qy+qh)

            hov_t = self._is_hovering(tx, tx+tw, ty2, ty2+th2)
            _draw_btn(tx, tw, ty2, th2,
                      theme_c["btn_hover"] if hov_t else (*theme_c["btn_fill"][:3], 145),
                      (*theme_c["btn_border"][:3], 158),
                      theme_c["toggle_text"],
                      "[ LIGHT MODE ]" if self.menu_theme=="dark" else "[ DARK MODE ]",
                      12 if pause_scale > 0.9 else 11)
            self._menu_btns["theme"] = (tx, tx+tw, ty2, ty2+th2)
            return

        arcade.draw_text("SELECT YOUR SHIP", w//2+1, div_y-23, (0,0,0,90), scaled(13),
                         anchor_x="center", bold=True, font_name=font_ui_local)
        arcade.draw_text("SELECT YOUR SHIP", w//2, div_y-22,
                         theme_c["text"], scaled(13), anchor_x="center", bold=True, font_name=font_ui_local)

        # ── Ship cards ───────────────────────────────
        n   = len(SHIPS)
        gap = scaled(12)
        # Dynamic card width: fill panel interior (22px margin each side) exactly
        panel_inner_w = pw - 44
        cw = (panel_inner_w - gap * (n - 1)) // n
        card_height_limit = max(132, ph - 388)
        ch  = min(220, int(cw * 1.24), card_height_limit)
        total_cw = cw * n + gap * (n - 1)
        cx0  = pl + 22                   # start at panel left margin
        cy0  = div_y - 54 - ch           # card bottom y

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

            content_pad = max(10, int(cw * 0.07))
            fname_sz = max(14, min(18, cw // 9))
            if len(ship["name"]) >= 11:
                fname_sz -= 1
            if len(ship["name"]) >= 12:
                fname_sz -= 1
            ftag_sz  = max(11, min(13, cw // 12))
            fstat_sz = max(10, min(12, cw // 13))

            badge_y  = cb + int(ch * 0.05)
            def_y    = cb + int(ch * 0.14)
            atk_y    = cb + int(ch * 0.23)
            spd_y    = cb + int(ch * 0.32)
            tag_y    = cb + int(ch * 0.40)
            name_y   = cb + int(ch * 0.49)

            preview_bottom = name_y + fname_sz + 12
            preview_top = ct - content_pad
            preview_height = max(24, preview_top - preview_bottom)
            preview_width = max(24, cw - content_pad * 2)

            pcx = cl + cw // 2
            pcy = preview_bottom + preview_height * 0.55

            if avl and ship["texture"]:
                tex  = load_texture_clean(ship["texture"], ship["tex_scale"])
                draw_y = pcy + (math.sin(t*2.8)*4 if sel else 0)
                arcade.draw_circle_filled(pcx, pcy, min(30, preview_width * 0.24),
                                          (*ship["color"], 35+int(20*math.sin(t*3))))
                _draw_texture_fitted(tex, pcx, draw_y, preview_width, preview_height)
            else:
                arcade.draw_circle_outline(pcx,pcy,28, theme_c["locked_border"],2)
                arcade.draw_text("?", pcx, pcy, theme_c["locked_text"], 28,
                                 anchor_x="center", anchor_y="center", bold=True,
                                 font_name=FONT_UI_MENU)

            nc = theme_c["locked_text"] if not avl else \
                 (theme_c["card_sel_border"] if sel else theme_c["text"])
            tagline_c = theme_c["locked_text"] if not avl else (*theme_c["text"][:3], 220)
            stat_c = theme_c["locked_text"] if not avl else (*theme_c["text"][:3], 235)
            self._txt_shadow(ship["name"], pcx, name_y, nc, fname_sz, FONT_UI_MENU,
                             anchor_x="center", bold=True, ox=1, oy=-1)

            if avl:
                # tagline
                self._txt_shadow(ship["tagline"], pcx, tag_y, tagline_c, ftag_sz, FONT_UI_MENU,
                                 anchor_x="center", ox=1, oy=-1)

                # thin divider between tagline and stats
                arcade.draw_line(cl+8, tag_y-6, cr-8, tag_y-6,
                                 (*theme_c["divider"][:3], 80), 1)

                # stat rows — SPD / ATK / DEF
                pip_x = cl + int(cw * 0.68)
                pip_span = max(54, int(cw * 0.32))
                for row_y, lbl, val in [(spd_y, "SPD", ship["stat_spd"]),
                                         (atk_y, "ATK", ship["stat_atk"]),
                                         (def_y, "DEF", ship["stat_def"])]:
                    self._txt_shadow(lbl, cl + content_pad, row_y, stat_c, fstat_sz, FONT_NUMERIC,
                                     anchor_y="center", bold=True, ox=1, oy=-1)
                    self._draw_stat_pips(pip_x, row_y, val, 5,
                                         theme_c["stat_filled"], theme_c["stat_empty"], pip_span)

                # SELECTED badge
                if sel:
                    self._txt_shadow("✔ SELECTED", pcx, badge_y, theme_c["selected_badge"],
                                     fstat_sz, FONT_UI_MENU, anchor_x="center", bold=True, ox=1, oy=-1)
            else:
                self._txt_shadow("COMING SOON", pcx, tag_y, theme_c["locked_text"], ftag_sz,
                                 FONT_UI_MENU, anchor_x="center", ox=1, oy=-1)

            self._ship_cards[i] = (cl, cr, cb, ct)

        # ── Buttons ──────────────────────────────────
        btn_top = cy0 - 12

        # ── Difficulty selector ──────────────────────
        arcade.draw_text("SELECT DIFFICULTY", w//2+1, btn_top-3, (0,0,0,90), scaled(12),
                         anchor_x="center", bold=True, font_name=font_ui_local)
        arcade.draw_text("SELECT DIFFICULTY", w//2, btn_top-2,
                         theme_c["text"], scaled(12), anchor_x="center", bold=True, font_name=font_ui_local)

        dw, dh = scaled(118), scaled(38)
        dgap   = scaled(10)
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
                             (0,0,0,sa_), scaled(14), anchor_x="center", anchor_y="center",
                             bold=True, font_name=font_ui_local)
            arcade.draw_text(preset["label"], dleft+dw//2, diff_by+dh//2,
                             tcolor, scaled(14), anchor_x="center", anchor_y="center",
                             bold=True, font_name=font_ui_local)

            self._diff_btns[dkey] = (dleft, dright, diff_by, dtop)

        play_y = diff_by - 14   # play button sits below difficulty row

        bw, bh = scaled(230), scaled(50)
        bx = w//2-bw//2;  by = play_y - bh
        hov_p = self._is_hovering(bx, bx+bw, by, by+bh)
        _draw_btn(bx, bw, by, bh,
                  theme_c["btn_hover"] if hov_p else theme_c["btn_fill"],
                  theme_c["btn_border"], theme_c["btn_text"],
                  "[ RESUME ]" if is_pause else "[ PLAY GAME ]", scaled(20))
        self._menu_btns["play"] = (bx, bx+bw, by, by+bh)

        # ── Shop button (main menu only) ─────────────
        if not is_pause:
            sw, sh2 = scaled(230), scaled(38)
            sx2 = w//2 - sw//2;  sy2 = by - sh2 - 8
            hov_s = self._is_hovering(sx2, sx2+sw, sy2, sy2+sh2)
            coin_label = f"[ SHOP ]  $ {self.coins:,}"
            _draw_btn(sx2, sw, sy2, sh2,
                      theme_c["btn_hover"] if hov_s else (*theme_c["btn_fill"][:3], 200),
                      (255, 210, 30, 220), (255, 215, 40, 255),
                      coin_label, scaled(14))
            self._menu_btns["shop"] = (sx2, sx2+sw, sy2, sy2+sh2)
            _theme_ref_y = sy2
        else:
            sw, sh2 = scaled(230), scaled(38)
            sx2 = w//2 - sw//2;  sy2 = by - sh2 - 8
            hov_s = self._is_hovering(sx2, sx2+sw, sy2, sy2+sh2)
            coin_label = f"[ SHOP ]  $ {self.coins:,}"
            _draw_btn(sx2, sw, sy2, sh2,
                      theme_c["btn_hover"] if hov_s else (*theme_c["btn_fill"][:3], 200),
                      (255, 210, 30, 220), (255, 215, 40, 255),
                      coin_label, scaled(14))
            self._menu_btns["shop"] = (sx2, sx2+sw, sy2, sy2+sh2)

            rw, rh = scaled(196), scaled(40)
            rx = w//2-rw//2;  ry = sy2-rh-10
            hov_r = self._is_hovering(rx, rx+rw, ry, ry+rh)
            _draw_btn(rx, rw, ry, rh,
                      theme_c["btn_hover"] if hov_r else (145, 40, 40, 145),
                      (255, 110, 110, 190), theme_c["btn_text_dim"],
                      "RESET RUN", scaled(14))
            self._menu_btns["reset"] = (rx, rx+rw, ry, ry+rh)

            qw, qh = scaled(196), scaled(40)
            qx = w//2-qw//2;  qy = ry-qh-10
            hov_q = self._is_hovering(qx, qx+qw, qy, qy+qh)
            _draw_btn(qx, qw, qy, qh,
                      theme_c["btn_hover"] if hov_q else (*theme_c["btn_fill"][:3], 145),
                      (*theme_c["btn_border"][:3], 152), theme_c["btn_text_dim"],
                      "QUIT TO MENU", scaled(14))
            self._menu_btns["quit"] = (qx, qx+qw, qy, qy+qh)
            _theme_ref_y = qy

        # theme toggle — always a fixed gap below the lowest action button
        tw, th2 = scaled(230), scaled(32)
        tx  = w//2 - tw//2
        ty2 = max(pb + 10, _theme_ref_y - th2 - 12)
        hov_t = self._is_hovering(tx, tx+tw, ty2, ty2+th2)
        _draw_btn(tx, tw, ty2, th2,
                  theme_c["btn_hover"] if hov_t else (*theme_c["btn_fill"][:3], 145),
                  (*theme_c["btn_border"][:3], 158),
                  theme_c["toggle_text"],
                  "[ LIGHT MODE ]" if self.menu_theme=="dark" else "[ DARK MODE ]",
                  scaled(12))
        self._menu_btns["theme"] = (tx, tx+tw, ty2, ty2+th2)

    # ══════════════════════════════════════════════════
    #  LEVEL SELECT SCREEN
    # ══════════════════════════════════════════════════

    def _draw_level_select(self, anim: dict | None = None, draw_background: bool = True):
        anim = anim or {}
        w, h   = self.width, self.height
        tc     = THEMES["dark"]
        FU     = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
        FN     = ("Courier New", "Menlo", "Monaco", "monospace")
        t      = self.bg_time
        panel_scale = anim.get("scale", 1.0)
        panel_offset_y = anim.get("offset_y", 0.0)
        ui_scale = max(0.82, min(1.35, min(w / 1360, h / 920))) * panel_scale

        # ── Background ───────────────────────────────
        if draw_background:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, tc["bg"])
            off = (t * 14) % 28
            for yi in range(-30, h+30, 28):
                arcade.draw_line(0, yi+off, w, yi+off-18, (28,44,76,24), 1)
            for s in self.stars:
                tw2 = 0.55 + 0.45*math.sin(t*s["twinkle"]+s["phase"])
                al  = max(20, min(255, int(s["alpha"]*tw2)))
                arcade.draw_circle_filled(s["x"],s["y"],s["size"],(200,222,255,al))

        # ── Outer panel ──────────────────────────────
        base_ui_scale = max(0.82, min(1.35, min(w / 1360, h / 920)))
        base_pad = max(12, int(18 * base_ui_scale))
        base_pw = w - base_pad * 2
        base_ph = h - base_pad * 2
        pw   = int(base_pw * panel_scale)
        ph   = int(base_ph * panel_scale)
        pl   = (w - pw) // 2
        pr   = pl + pw
        pb   = int((h - ph) // 2 + panel_offset_y)
        ptop = pb + ph
        arcade.draw_lrbt_rectangle_filled(pl+6,pr+6,pb-6,ptop-6,(0,0,0,80))
        arcade.draw_lrbt_rectangle_filled(pl,pr,pb,ptop,tc["panel_fill"])
        arcade.draw_lrbt_rectangle_outline(pl,pr,pb,ptop,tc["panel_border"],2)
        arcade.draw_lrbt_rectangle_outline(pl+4,pr-4,pb+4,ptop-4,tc["panel_inner"],1)

        # corner accents
        ac = tc["panel_border"]; sz = 18
        for cx2,cy2,sx,sy in [(pl,ptop,1,-1),(pr,ptop,-1,-1),(pl,pb,1,1),(pr,pb,-1,1)]:
            arcade.draw_line(cx2,cy2,cx2+sx*sz,cy2,ac,2)
            arcade.draw_line(cx2,cy2,cx2,cy2+sy*sz,ac,2)

        # ── Header ───────────────────────────────────
        HEADER_H = max(54, int(58 * ui_scale))
        title_size = max(24, int(28 * ui_scale))
        coin_size = max(11, int(12 * ui_scale))
        header_y  = ptop - HEADER_H
        arcade.draw_text("SELECT LEVEL", w//2+2, ptop-int(34 * ui_scale),
                         tc["title_shadow"], title_size, anchor_x="center", bold=True,
                         font_name=FU)
        arcade.draw_text("SELECT LEVEL", w//2, ptop-int(32 * ui_scale),
                         tc["title"], title_size, anchor_x="center", bold=True,
                         font_name=FU)
        # coin balance right-aligned
        arcade.draw_text(f"$ {self.coins:,}", pr-14, ptop-int(30 * ui_scale),
                         (255,220,40,230), coin_size, anchor_x="right",
                         bold=True, font_name=FN)
        arcade.draw_line(pl+14, header_y, pr-14, header_y, tc["divider"], 1)

        # ── Bottom bar (diff + play + back) ──────────
        BOT_H = max(50, int(52 * ui_scale))
        bot_y  = pb + BOT_H         # top of bottom bar
        arcade.draw_line(pl+14, bot_y, pr-14, bot_y, tc["divider"], 1)

        bar_bottom = pb + max(8, int(9 * ui_scale))
        bar_center_y = pb + BOT_H * 0.5
        pill_h = max(24, int(26 * ui_scale))
        pill_w = max(62, int(76 * ui_scale))
        pill_gap = max(5, int(6 * ui_scale))
        diff_label_size = max(8, int(10 * ui_scale))
        diff_text_size = max(8, int(10 * ui_scale))

        # Difficulty pills
        arcade.draw_text("DIFFICULTY", pl+14, bar_center_y - diff_label_size * 0.45, tc["text_dim"],
                         diff_label_size, font_name=FU)
        dx = pl + max(92, int(108 * ui_scale))
        self._ls_diff_btns = {}
        for dkey, dlabel in [("easy","EASY"),("medium","MED"),("hard","HARD")]:
            dw2 = pill_w;  dh2 = pill_h
            sel_d = (dkey == self.selected_difficulty)
            dc = {"easy":(60,200,80),"medium":(220,180,20),"hard":(220,60,60)}[dkey]
            pill_bottom = int(bar_center_y - dh2 / 2)
            pill_top = pill_bottom + dh2
            hov_d = self._is_hovering(dx, dx+dw2, pill_bottom, pill_top)
            fill = (*dc, 190 if sel_d else (70 if hov_d else 35))
            arcade.draw_lrbt_rectangle_filled(dx, dx+dw2, pill_bottom, pill_top, fill)
            arcade.draw_lrbt_rectangle_outline(dx, dx+dw2, pill_bottom, pill_top,
                                                (*dc,255 if sel_d else 110),
                                                2 if sel_d else 1)
            arcade.draw_text(dlabel, dx+dw2//2, bar_center_y,
                             (255,255,255) if sel_d else (*dc,210),
                             diff_text_size, anchor_x="center", anchor_y="center",
                             bold=sel_d, font_name=FU)
            self._ls_diff_btns[dkey] = (dx, dx+dw2, pill_bottom, pill_top)
            dx += dw2 + pill_gap

        # Play button (centre bottom)
        bh = max(32, int(34 * ui_scale))
        bw = max(170, int(210 * ui_scale))
        bx = w//2 - bw//2
        by = int(bar_center_y - bh / 2)
        hov_p = self._is_hovering(bx, bx+bw, by, by+bh)
        arcade.draw_lrbt_rectangle_filled(bx,bx+bw,by,by+bh,
                                           tc["btn_hover"] if hov_p else tc["btn_fill"])
        arcade.draw_lrbt_rectangle_outline(bx,bx+bw,by,by+bh,tc["btn_border"],2)
        arcade.draw_text("[ PLAY LEVEL ]", bx+bw//2, bar_center_y,
                         tc["btn_text"], max(12, int(14 * ui_scale)), anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)
        self._ls_play_btn = (bx, bx+bw, by, by+bh)

        # Back button (right bottom)
        bkw = max(86, int(96 * ui_scale))
        bkh = max(30, int(32 * ui_scale))
        bkx = pr - bkw - 12
        bky = int(bar_center_y - bkh / 2)
        hov_bk = self._is_hovering(bkx, bkx+bkw, bky, bky+bkh)
        arcade.draw_lrbt_rectangle_filled(bkx,bkx+bkw,bky,bky+bkh,
                                           (*tc["btn_fill"][:3], 160 if hov_bk else 100))
        arcade.draw_lrbt_rectangle_outline(bkx,bkx+bkw,bky,bky+bkh,
                                            (*tc["btn_border"][:3],130),1)
        arcade.draw_text("[ BACK ]", bkx+bkw//2, bar_center_y,
                         tc["btn_text_dim"], max(10, int(11 * ui_scale)), anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)
        self._ls_back_btn = (bkx, bkx+bkw, bky, bky+bkh)

        # ── 2 × 5 Card Grid ──────────────────────────
        GRID_COLS  = 5
        GRID_ROWS  = 2
        CARD_GAP   = max(8, int(10 * ui_scale))
        grid_top   = ptop - HEADER_H - max(8, int(10 * ui_scale))
        grid_bot   = bot_y + max(8, int(10 * ui_scale))
        grid_h     = grid_top - grid_bot
        grid_w     = pw - max(28, int(32 * ui_scale))

        cw = (grid_w - CARD_GAP*(GRID_COLS-1)) // GRID_COLS
        ch = (grid_h - CARD_GAP*(GRID_ROWS-1)) // GRID_ROWS

        self._level_cards = {}

        for idx, lvl in enumerate(LEVELS):
            row = idx // GRID_COLS
            col = idx  % GRID_COLS
            cl  = pl + max(14, int(16 * ui_scale)) + col*(cw+CARD_GAP)
            cr  = cl + cw
            ct  = grid_top - row*(ch+CARD_GAP)
            cb_ = ct - ch
            lc  = lvl["color"]
            sel = (idx == self.selected_level)
            hov = self._is_hovering(cl, cr, cb_, ct)
            req = lvl["requires_level"]
            unlocked = (req < 0) or (req in self.completed_levels)
            completed = idx in self.completed_levels
            ccx = cl + cw//2
            ccy = cb_ + ch//2

            pulse = 0.5 + 0.5*math.sin(t*2.8 + idx*0.7)

            # ── Card background ───────────────────────
            if sel and unlocked:
                arcade.draw_lrbt_rectangle_filled(cl-3,cr+3,cb_-3,ct+3,
                                                   (*lc[:3], int(55+25*pulse)))
                arcade.draw_lrbt_rectangle_outline(cl-3,cr+3,cb_-3,ct+3,
                                                    (*lc[:3], int(180+75*pulse)), 3)
                arcade.draw_lrbt_rectangle_filled(cl,cr,cb_,ct, (*lc[:3],45))
            elif hov and unlocked:
                arcade.draw_lrbt_rectangle_filled(cl,cr,cb_,ct, (*lc[:3],28))
                arcade.draw_lrbt_rectangle_outline(cl,cr,cb_,ct, (*lc[:3],160), 2)
            elif unlocked:
                arcade.draw_lrbt_rectangle_filled(cl,cr,cb_,ct, (10,16,42,210))
                arcade.draw_lrbt_rectangle_outline(cl,cr,cb_,ct, (*lc[:3],90), 1)
            else:
                arcade.draw_lrbt_rectangle_filled(cl,cr,cb_,ct, (7,9,22,210))
                arcade.draw_lrbt_rectangle_outline(cl,cr,cb_,ct, (35,42,68,90), 1)

            # ── Completed tick (top-left) ─────────────
            if completed:
                arcade.draw_circle_filled(cl+10, ct-10, 8, (50,200,80,220))
                arcade.draw_text("✔", cl+6, ct-17, (255,255,255,255), 9,
                                 font_name=FU)

            # ── Content ───────────────────────────────
            if not unlocked:
                arcade.draw_text("🔒", ccx, ccy+8, (60,70,105,200),
                                 20, anchor_x="center", anchor_y="center")
                need = LEVELS[req]["name"] if req >= 0 else ""
                arcade.draw_text(f"Beat  {need}", ccx, ccy-18,
                                 (55,65,100,200), 7, anchor_x="center",
                                 font_name=FN)
            else:
                # Level number badge
                badge_r = max(13, min(int(18 * ui_scale), ch//7))
                badge_cy = ct - badge_r - 4
                arcade.draw_circle_filled(ccx, badge_cy, badge_r, (*lc[:3],180))
                arcade.draw_circle_outline(ccx, badge_cy, badge_r, (*lc[:3],255), 2)
                arcade.draw_text(str(lvl["number"]), ccx, badge_cy,
                                 (255,255,255), max(10, badge_r),
                                 anchor_x="center", anchor_y="center",
                                 bold=True, font_name=FU)

                # Name
                name_sz = max(8, min(int(12 * ui_scale), cw//12))
                name_y = badge_cy - badge_r - max(8, int(8 * ui_scale))
                arcade.draw_text(lvl["name"], ccx, name_y,
                                 (*lc[:3],230) if sel else (*lc[:3],180),
                                 name_sz, anchor_x="center", anchor_y="top", bold=True,
                                 font_name=FU)

                # Divider
                div_y2 = name_y - name_sz - max(8, int(8 * ui_scale))
                arcade.draw_line(cl+8, div_y2, cr-8, div_y2,
                                 (*lc[:3],50), 1)

                # Stats (compact)
                total_e = lvl["regular_enemies"]+lvl["shooting_enemies"]
                if idx == len(LEVELS) - 1:
                    boss_hp = _campaign_total_boss_hp()
                else:
                    boss_hp = _level_boss_hp(lvl["regular_enemies"],
                                              lvl["shooting_enemies"],
                                              lvl["boss_hp_mult"])
                stat_sz = max(8, min(int(10 * ui_scale), cw//15))
                sy      = div_y2 - 4
                stat_label_c = (155, 180, 225, 225)
                stat_value_c = (*lc[:3], 235)
                for lbl2, val2 in [("ENEMIES", f"{total_e}"),
                                    ("BOSS HP",  f"{boss_hp:,}"),
                                    ("REWARD",  f"${lvl['reward_coins']}")]:
                    if sy < cb_ + 26: break
                    self._txt_shadow(lbl2, cl+6, sy-stat_sz,
                                     stat_label_c, stat_sz-1, FN)
                    self._txt_shadow(val2, cr-5, sy-stat_sz,
                                     stat_value_c, stat_sz, FN,
                                     anchor_x="right", bold=True)
                    sy -= stat_sz + 6

                best_s = self.best_scores.get(idx, 0)
                boss_name_sz = max(6, min(int(8 * ui_scale), cw//17))
                boss_line_y = cb_ + 18
                portrait_left = cl + max(18, int(20 * ui_scale))
                portrait_right = cr - max(18, int(20 * ui_scale))
                portrait_bottom = boss_line_y + 14
                portrait_top = sy - 6

                if portrait_top - portrait_bottom >= max(28, int(34 * ui_scale)):
                    bob = math.sin(t * 1.9 + idx * 0.7)
                    drift = math.sin(t * 1.2 + idx * 0.45) * 2.0
                    pulse = 0.92 + 0.08 * math.sin(t * 2.4 + idx * 0.9)
                    hover_y = bob * 4.0
                    glow_w = (portrait_right - portrait_left) * (0.48 + 0.06 * pulse)
                    glow_h = max(8, (portrait_top - portrait_bottom) * 0.12)
                    glow_y = portrait_bottom + glow_h * 0.95
                    glow_alpha = 34 if sel else 22
                    arcade.draw_ellipse_filled(
                        ccx, glow_y,
                        glow_w, glow_h,
                        (*lc[:3], glow_alpha)
                    )
                    arcade.draw_ellipse_outline(
                        ccx, glow_y + 1,
                        glow_w * 0.72, glow_h * 0.55,
                        (*lc[:3], 36 if sel else 24), 1
                    )
                    boss_tex = load_texture_clean(
                        lvl["boss_texture"],
                        lvl.get("boss_portrait_scale", lvl.get("boss_texture_scale", 0.3))
                    )
                    _draw_texture_fitted(
                        boss_tex,
                        ccx + drift,
                        (portrait_bottom + portrait_top) * 0.5 + 4 + hover_y,
                        (portrait_right - portrait_left) * (0.82 * pulse),
                        (portrait_top - portrait_bottom) * (0.80 * pulse),
                    )

                arcade.draw_text(
                    f"BOSS: {lvl['boss_name']}",
                    ccx, boss_line_y,
                    (*lc[:3], 235) if sel else (*lc[:3], 190),
                    boss_name_sz,
                    anchor_x="center",
                    bold=True,
                    font_name=FN,
                )

                # Best score at bottom
                if best_s > 0:
                    arcade.draw_text(f"BEST {best_s:,}", ccx, cb_+5,
                                     (255,220,40,210), max(7, int(8 * ui_scale)), anchor_x="center",
                                     bold=True, font_name=FN)

            self._level_cards[idx] = (cl, cr, cb_, ct)

    # ══════════════════════════════════════════════════
    #  LEVEL CLEAR OVERLAY
    # ══════════════════════════════════════════════════

    def _draw_level_clear_overlay(self):
        w, h  = self.width, self.height
        lvl   = LEVELS[self.selected_level]
        lc    = lvl["color"]
        font_u = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
        font_n = ("Courier New", "Menlo", "Monaco", "monospace")

        # Dark overlay
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (0, 0, 0, 160))

        pw = 420;  ph = 240
        pl = w//2 - pw//2;  pr = pl+pw
        pb = h//2 - ph//2;  pt = pb+ph

        arcade.draw_lrbt_rectangle_filled(pl+6,pr+6,pb-6,pt-6,(0,0,0,80))
        arcade.draw_lrbt_rectangle_filled(pl,pr,pb,pt, (*lc[:3],22))
        arcade.draw_lrbt_rectangle_outline(pl,pr,pb,pt, (*lc[:3],255), 3)
        arcade.draw_lrbt_rectangle_outline(pl+5,pr-5,pb+5,pt-5,(*lc[:3],60),1)

        arcade.draw_text("LEVEL CLEAR!", w//2+2, pt-50,
                         (*lc[:3],60), 36, anchor_x="center", bold=True,
                         font_name=font_u)
        arcade.draw_text("LEVEL CLEAR!", w//2, pt-48,
                         (*lc[:3],255), 36, anchor_x="center", bold=True,
                         font_name=font_u)
        arcade.draw_text(lvl["name"], w//2, pt-78,
                         (200,220,255,210), 14, anchor_x="center",
                         font_name=font_u)
        arcade.draw_line(pl+20, h//2+20, pr-20, h//2+20, (*lc[:3],80), 1)
        arcade.draw_text(f"SCORE   {self.score:,}", w//2, h//2+8,
                         (255,255,255,240), 14, anchor_x="center",
                         bold=True, font_name=font_n)
        arcade.draw_text(f"COINS + {lvl['reward_coins']}", w//2, h//2-14,
                         (255,220,40,240), 13, anchor_x="center",
                         bold=True, font_name=font_n)
        secs = max(0, self._level_clear_timer)
        arcade.draw_text(f"Returning to level select in {secs:.0f}s ...",
                         w//2, pb+22, (160,180,215,200), 10,
                         anchor_x="center", font_name=font_u)

    # ══════════════════════════════════════════════════
    #  SHOP DRAWING
    # ══════════════════════════════════════════════════

    def _shop_layout(self):
        w, h = self.width, self.height
        pw = min(int(w * 0.92), 860)
        ph = min(int(h * 0.94), 660)
        pl = (w - pw) // 2
        pr = pl + pw
        pb = (h - ph) // 2
        ptop = pb + ph

        div_y = ptop - 102
        cols = 3
        rows = max(1, math.ceil(len(SHOP_ITEMS) / cols))
        side_pad = 28
        gap_ = 14
        cw_ = (pw - side_pad * 2 - gap_ * (cols - 1)) // cols
        grid_top = div_y - 18
        back_band = 66
        grid_bottom = pb + back_band
        available_h = max(320, grid_top - grid_bottom)
        ch_ = min(188, max(156, (available_h - gap_ * (rows - 1)) // rows))

        item_rects = {}
        for idx, item in enumerate(SHOP_ITEMS):
            col = idx % cols
            row = idx // cols
            cl = pl + side_pad + col * (cw_ + gap_)
            ct = grid_top - row * (ch_ + gap_)
            cr = cl + cw_
            cb_ = ct - ch_
            item_rects[item["id"]] = (cl, cr, cb_, ct)

        bkw, bkh = 160, 38
        bkx = w // 2 - bkw // 2
        bky = pb + 12
        back_rect = (bkx, bkx + bkw, bky, bky + bkh)

        return {
            "panel": (pl, pr, pb, ptop),
            "divider_y": div_y,
            "card_w": cw_,
            "card_h": ch_,
            "items": item_rects,
            "back": back_rect,
        }

    def _draw_shop(self):
        w, h   = self.width, self.height
        tc     = THEMES["dark"]
        font_title = FONT_UI_DISPLAY
        font_u = FONT_UI_MENU
        font_n = FONT_NUMERIC

        # Background
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, tc["bg"])
        # Subtle animated lines
        t = self.bg_time
        off = (t * 14) % 28
        for yi in range(-30, h+30, 28):
            arcade.draw_line(0, yi+off, w, yi+off-18, (28,44,76,24), 1)

        # Panel
        layout = self._shop_layout()
        pl, pr, pb, ptop = layout["panel"]
        cw_ = layout["card_w"]
        ch_ = layout["card_h"]
        div_y = layout["divider_y"]

        arcade.draw_lrbt_rectangle_filled(pl+7, pr+7, pb-7, ptop-7, (0,0,0,70))
        arcade.draw_lrbt_rectangle_filled(pl, pr, pb, ptop, tc["panel_fill"])
        arcade.draw_lrbt_rectangle_outline(pl, pr, pb, ptop, tc["panel_border"], 2)
        arcade.draw_lrbt_rectangle_outline(pl+5, pr-5, pb+5, ptop-5, tc["panel_inner"], 1)

        # Title
        ty_title = ptop - 48
        arcade.draw_text("SHOP", w//2+3, ty_title-3, tc["title_shadow"], 38,
                         anchor_x="center", bold=True, font_name=font_title)
        arcade.draw_text("SHOP", w//2, ty_title, tc["title"], 38,
                         anchor_x="center", bold=True, font_name=font_title)
        # Coin balance
        bal_str = f"$ {self.coins:,}  coins"
        arcade.draw_text(bal_str, w//2, ty_title-30,
                         (255, 220, 40, 245), 14, anchor_x="center",
                         bold=True, font_name=font_n)
        arcade.draw_text(self.shop_feedback, w//2, ty_title-54,
                         self.shop_feedback_color, 10, anchor_x="center",
                         bold=True, font_name=font_u)

        arcade.draw_line(pl+22, div_y, pr-22, div_y, tc["divider"], 1)

        # ── Item grid ────────────────────────────────
        self._shop_btns = {}

        for item in SHOP_ITEMS:
            cl, cr, cb_, ct = layout["items"][item["id"]]
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

            pad_x = max(14, int(cw_ * 0.07))
            title_size = max(13, min(16, cw_ // 15))
            icon_size = max(16, min(22, cw_ // 11))
            desc_size = max(10, min(12, cw_ // 18))
            cost_size = max(12, min(15, cw_ // 15))
            top_pad = max(14, int(ch_ * 0.08))
            title_y = ct - top_pad
            badge_cy = title_y - max(26, int(ch_ * 0.17))
            badge_w = max(54, int(cw_ * 0.22))
            badge_h = max(28, int(ch_ * 0.16))
            desc_y = badge_cy - max(24, int(ch_ * 0.16))
            dot_y = desc_y - max(26, int(ch_ * 0.16))
            price_y = cb_ + max(22, int(ch_ * 0.11))

            # Icon badge
            ic_alpha = 255 if (can_afford or maxed) else 110
            arcade.draw_lrbt_rectangle_filled(
                cl + pad_x, cl + pad_x + badge_w,
                badge_cy - badge_h // 2, badge_cy + badge_h // 2,
                (*ic[:3], 60 if can_afford else 30)
            )
            self._txt_shadow(item["icon"], cl + pad_x + badge_w // 2, badge_cy - 1,
                             (*ic[:3], ic_alpha), icon_size, font_u,
                             anchor_x="center", anchor_y="center", bold=True, ox=1, oy=-1)

            # Name
            nc = (*ic[:3], 240) if (can_afford or maxed) else (80, 90, 120, 180)
            self._txt_shadow(item["name"], cl + cw_//2, title_y,
                             nc, title_size, font_u, anchor_x="center",
                             bold=True, ox=1, oy=-1)
            # Desc
            self._txt_shadow(item["desc"], cl + cw_//2, desc_y,
                             (185, 205, 235, 210), desc_size, font_u,
                             anchor_x="center", ox=1, oy=-1)

            # Tier dots
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
            if maxed:
                self._txt_shadow("✔ MAXED", cl + cw_//2, price_y,
                                 (80, 220, 100, 230), cost_size - 1, font_u,
                                 anchor_x="center", bold=True, ox=1, oy=-1)
            else:
                cost_c = (255, 220, 40, 240) if can_afford else (130, 140, 160, 160)
                self._txt_shadow(f"$ {cost}  coins", cl + cw_//2, price_y,
                                 cost_c, cost_size, font_n, anchor_x="center",
                                 bold=True, ox=1, oy=-1)

            if not maxed:
                self._shop_btns[item["id"]] = (cl, cr, cb_, ct)

        # ── Back button ─────────────────────────────
        bkx, _, bky, _ = layout["back"]
        bkw = 160
        bkh = 38
        hov_bk = self._is_hovering(bkx, bkx+bkw, bky, bky+bkh)
        _draw_btn(bkx, bkw, bky, bkh,
                  tc["btn_hover"] if hov_bk else (*tc["btn_fill"][:3], 180),
                  tc["btn_border"], tc["btn_text"], "[ BACK ]", 14)
        self._shop_btns["__back__"] = layout["back"]

    def _open_shop(self, return_state: str) -> None:
        self._shop_return_state = return_state
        self.shop_feedback = "CLICK A CARD TO BUY OR UPGRADE"
        self.shop_feedback_color = (160, 180, 215, 180)
        self._shop_btns = {**self._shop_layout()["items"], "__back__": self._shop_layout()["back"]}
        self.game_state = STATE_SHOP
        self.set_mouse_visible(True)

    def _close_shop(self) -> None:
        self.game_state = self._shop_return_state
        if self.game_state == STATE_PLAYING:
            self.set_mouse_visible(False)
        else:
            self.set_mouse_visible(True)

    def _apply_shop_upgrade_runtime(self, item_id: str) -> None:
        if self.player is None:
            return

        if item_id == "armor":
            self.player.max_health += 25
            self.player.health = min(self.player.max_health, self.player.health + 25)
        elif item_id == "engine":
            tier = self.upgrades.get("engine", 0)
            self.player._engine_bonus = 1.0 + tier * 0.12
        elif item_id == "starter_shield":
            self.player.inventory["shield"] = max(self.player.inventory.get("shield", 0), 1)

    def _purchase_shop_item(self, item_id: str) -> None:
        item = next((shop_item for shop_item in SHOP_ITEMS if shop_item["id"] == item_id), None)
        if item is None:
            return

        tier = self.upgrades.get(item_id, 0)
        if tier >= item["max"]:
            self.shop_feedback = f"{item['name']} IS ALREADY MAXED"
            self.shop_feedback_color = (80, 220, 100, 220)
            return

        cost = item["cost"][tier]
        if self.coins < cost:
            self.shop_feedback = f"NOT ENOUGH COINS FOR {item['name']}"
            self.shop_feedback_color = (255, 110, 110, 220)
            return

        self.coins -= cost
        self.upgrades[item_id] = tier + 1
        self._save_progress()

        if self._shop_return_state == STATE_PAUSED:
            self._apply_shop_upgrade_runtime(item_id)

        new_tier = self.upgrades[item_id]
        if new_tier >= item["max"]:
            self.shop_feedback = f"{item['name']} MAXED OUT"
            self.shop_feedback_color = (80, 220, 100, 220)
        else:
            self.shop_feedback = f"{item['name']} UPGRADED TO TIER {new_tier}"
            self.shop_feedback_color = (255, 220, 40, 230)

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
            ("3", "TRP",  "TRIPLE",  inv.get("triple",   0),
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
        hud_scale = max(0.45, min(1.0, min(w / SCREEN_WIDTH, h / SCREEN_HEIGHT)))

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
        left_x = max(10, int(20 * hud_scale))
        top_y = h - max(10, int(14 * hud_scale))
        score_label_size = max(8, int(9 * hud_scale))
        score_size = max(16, int(30 * hud_scale))
        health_label_size = max(9, int(10 * hud_scale))
        health_value_size = max(10, int(13 * hud_scale))
        top_value_gap = max(6, int(10 * hud_scale))
        section_gap = max(8, int(14 * hud_scale))
        health_value_gap = max(6, int(10 * hud_scale))
        hp_bar_gap = max(8, int(12 * hud_scale))
        hp_bar_w = max(120, min(230, int(w * 0.33)))
        hp_bar_h = max(7, int(10 * hud_scale))

        # ── SCORE ──────────────────────────────────
        self._txt_shadow("SCORE", left_x, top_y, (120,165,230,180), score_label_size, font_ui,
                         anchor_y="top")
        score_y = top_y - score_label_size - top_value_gap
        self._txt_shadow(f"{self.score:,}", left_x, score_y, (255,255,255,240), score_size,
                         font_ui, anchor_y="top", bold=True)

        # ── Level progress bar (top-centre) ──────────
        lvl  = LEVELS[self.selected_level]
        lc   = lvl["color"]
        total_e = lvl["regular_enemies"] + lvl["shooting_enemies"]
        sent_e  = total_e - self.level_enemies_remaining - self.level_shooting_remaining
        sent_e  = max(0, min(total_e, sent_e))
        prog_ratio = sent_e / max(1, total_e)

        bar_w = 220;  bar_h = 8
        bar_x = w//2 - bar_w//2;  bar_y = h - 18
        # track
        arcade.draw_lrbt_rectangle_filled(bar_x, bar_x+bar_w, bar_y, bar_y+bar_h,
                                           (20, 26, 60, 180))
        arcade.draw_lrbt_rectangle_outline(bar_x, bar_x+bar_w, bar_y, bar_y+bar_h,
                                            (*lc[:3], 120), 1)
        # fill
        fill_w = int(bar_w * prog_ratio)
        if fill_w > 0:
            arcade.draw_lrbt_rectangle_filled(bar_x, bar_x+fill_w, bar_y, bar_y+bar_h,
                                               (*lc[:3], 210))
        # label
        if self.level_boss_spawned:
            prog_label = f"LVL {lvl['number']}  ⚠ BOSS"
        else:
            remaining = self.level_enemies_remaining + self.level_shooting_remaining
            prog_label = f"LVL {lvl['number']}  {sent_e}/{total_e}"
        self._txt_shadow(prog_label, w//2, h-30, (*lc[:3], 230), 10,
                         font_ui, anchor_x="center", bold=True)

        # ── HP section ─────────────────────────────
        # Row positions (all from h, spaced so nothing overlaps):
        #   h-46 : "HEALTH" small label
        #   h-60 : "100 / 100" numbers
        #   h-76 to h-68 : segmented bar  (8px below numbers)
        #   h-66 : neon glow line on top of bar
        hr   = max(0.0, p.health/p.max_health)
        hc   = (60,235,110) if hr>0.55 else (255,195,55) if hr>0.28 else (255,60,60)

        health_label_y = score_y - score_size - section_gap
        self._txt_shadow("HEALTH", left_x, health_label_y, (120,165,230,200),
                         health_label_size, font_ui, anchor_y="top")

        # HP numbers row — drawn BEFORE bar so bar doesn't cover them
        hp_str = f"{int(max(0, p.health))}  /  {p.max_health}"
        health_value_y = health_label_y - health_label_size - health_value_gap
        self._txt_shadow(hp_str, left_x, health_value_y, (*hc[:3], 230), health_value_size,
                         font_num, anchor_y="top", bold=True)

        # Segmented bar — sits below the HP numbers with a scale-aware gap.
        hp_bar_y = health_value_y - health_value_size - hp_bar_gap
        self._draw_seg_bar(left_x, hp_bar_y, hp_bar_w, hp_bar_h, hr, hc, segs=23, gap=2)
        # Neon glow highlight line
        if hr > 0:
            gw = int(hp_bar_w * hr)
            arcade.draw_lrbt_rectangle_filled(left_x, left_x + gw,
                                               hp_bar_y + hp_bar_h - 1, hp_bar_y + hp_bar_h,
                                               (*hc[:3], int(155*hr)))

        # ══ POWER-UP PANEL (bottom-left) ══════════════
        self._draw_powerup_panel(p, t, font_ui, font_num)

        # ══ TOP-RIGHT ════════════════════════════════

        right_x = w - max(10, int(16 * hud_scale))
        top_y = h - max(10, int(14 * hud_scale))
        label_gap = max(6, int(10 * hud_scale))
        value_gap = max(6, int(10 * hud_scale))
        section_gap = max(8, int(12 * hud_scale))
        badge_h = max(16, int(20 * hud_scale))
        badge_pad = max(9, int(12 * hud_scale))
        badge_text_size = max(9, int(10 * hud_scale))
        small_label_size = max(8, int(9 * hud_scale))
        timer_size = max(10, int(13 * hud_scale))
        coin_size = max(11, int(14 * hud_scale))

        # ── Timer ──────────────────────────────────
        self._txt_shadow("TIME", right_x, top_y, (120,165,230,175), small_label_size,
                         font_ui, anchor_x="right", anchor_y="top")
        timer_y = top_y - small_label_size - label_gap
        self._txt_shadow(f"{self.time_alive:06.1f}s", right_x, timer_y, (165,200,255,215),
                         timer_size, font_num, anchor_x="right", anchor_y="top", bold=True)

        # ── Difficulty badge ────────────────────────
        dp  = self._dpreset
        dc  = dp["color"]
        dlbl = dp["label"]
        badge_text_w = max(60, int(len(dlbl) * badge_text_size * 0.78))
        badge_w = badge_text_w + badge_pad * 2
        badge_y = timer_y - timer_size - section_gap - badge_h
        badge_left = right_x - badge_w
        arcade.draw_lrbt_rectangle_filled(badge_left, right_x, badge_y, badge_y + badge_h,
                                           (*dc, 55))
        arcade.draw_lrbt_rectangle_outline(badge_left, right_x, badge_y, badge_y + badge_h,
                                            (*dc, 185), 1)
        self._txt_shadow(dlbl, badge_left + badge_w // 2, badge_y + badge_h // 2,
                         (*dc, 240), badge_text_size, font_ui,
                         anchor_x="center", anchor_y="center", bold=True, ox=1, oy=-1)

        # ── Coin counter (top-right, below difficulty) ───
        coin_c = (255, 220, 40, 245)
        coin_value_y = badge_y - coin_size - section_gap
        coin_label_y = coin_value_y - small_label_size - value_gap
        self._txt_shadow(f"$ {self.coins:,}", right_x, coin_value_y, coin_c, coin_size,
                         font_num, anchor_x="right", anchor_y="top", bold=True)
        self._txt_shadow("COINS", right_x, coin_label_y, (200, 170, 30, 160),
                         small_label_size, font_ui, anchor_x="right", anchor_y="top")

        # ══ COMBO (top-right below difficulty) ═══════
        if self.combo > 1 and self.combo_timer > 0:
            pulse = 0.75 + 0.25*math.sin(t*8)
            combo_y = coin_label_y - max(16, int(20 * hud_scale)) - section_gap
            self._txt_shadow(f"×{self.combo}  COMBO", right_x, combo_y,
                             (255, 220, 60, int(230*pulse)),
                             max(16, int(20 * hud_scale)), font_ui,
                             anchor_x="right", anchor_y="top", bold=True)

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

    def _draw_menu_to_level_transition(self) -> None:
        if not self._screen_transition:
            return

        p = min(1.0, self._screen_transition["time"] / self._screen_transition["duration"])
        out_ease = self._ease_out_cubic(p)
        in_ease = self._ease_out_back(p)

        menu_anim = {
            "scale": 1.0 - 0.13 * out_ease,
            "offset_y": -28 * out_ease,
        }
        level_anim = {
            "scale": 0.86 + 0.14 * in_ease,
            "offset_y": 72 * (1.0 - out_ease) - 10 * math.sin(p * math.pi),
        }

        self._draw_menu(anim=menu_anim, draw_background=True)
        shade_alpha = int(34 + 56 * out_ease)
        arcade.draw_lrbt_rectangle_filled(0, self.width, 0, self.height, (4, 8, 20, shade_alpha))
        self._draw_level_select(anim=level_anim, draw_background=False)

    # ══════════════════════════════════════════════════
    #  ON DRAW
    # ══════════════════════════════════════════════════

    def on_draw(self):
        w, h = self.width, self.height
        self.clear()

        if self._screen_transition:
            self._draw_menu_to_level_transition()
            return

        if self.game_state == STATE_MODE_SELECT:
            self._draw_mode_select()
            return

        if self.game_state == STATE_MENU:
            self._draw_menu()
            return

        if self.game_state == STATE_SHOP:
            self._draw_shop()
            return

        if self.game_state == STATE_LEVEL_SELECT:
            self._draw_level_select()
            return

        if self.game_state == STATE_MAZE_SELECT:
            self._draw_maze_select()
            return

        if self.game_state == STATE_MAZE:
            self._draw_maze_world()
            return

        if self.game_state == STATE_MAZE_OVER:
            self._draw_maze_over()
            return

        if self.game_state == STATE_PAUSED and self._pause_return_state == STATE_MAZE:
            self._draw_maze_world()
            self._draw_menu()
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
        for bolt in self.enemy_elec_bolts:
            bolt.draw_bolt()

        # Final boss electric danger radius
        for boss in self.bosses:
            if getattr(boss, "is_final_boss", False):
                pulse = 0.65 + 0.35 * math.sin(self.bg_time * 6.5)
                rr = FINAL_BOSS_ELECTRIC_RANGE + 6 * math.sin(self.bg_time * 5.0)
                arcade.draw_circle_outline(
                    boss.center_x, boss.center_y, rr,
                    (130, 90, 255, int(95 * pulse)), 4
                )
                arcade.draw_circle_outline(
                    boss.center_x, boss.center_y, rr + 4,
                    (220, 180, 255, int(45 * pulse)), 1
                )

        # ── 360° electric aura ring while elec360 is active ──────────
        if self.player.elec360_active:
            t_pulse = self.bg_time
            ring_r  = ELECTRIC_360_RADIUS + 8*math.sin(t_pulse*8)
            for layer, (col, width) in enumerate([
                    ((80,  50, 255, 30), 22),
                    ((140, 90, 255, 72), 9),
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

        if self.level_complete:
            self._draw_level_clear_overlay()

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
        self._update_screen_transition(delta)

        if self.notif_timer  > 0: self.notif_timer  -= delta
        if self.damage_flash > 0: self.damage_flash = max(0.0, self.damage_flash-2.6*delta)
        if self.contact_damage_timer > 0: self.contact_damage_timer -= delta
        if self.combo_timer > 0: self.combo_timer -= delta
        elif self.combo > 0:     self.combo = 0

        if self.game_state == STATE_MAZE:
            self._update_maze(delta)
            return

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

        firing = True
        if firing:
            if is_electric_ship and p.elec360_active:
                rate = ELECTRIC_360_FIRE_RATE
            else:
                rate = ELECTRIC_FIRE_RATE if is_electric_ship else AUTO_FIRE_RATE
            self.fire_timer += delta
            while self.fire_timer >= rate:
                if is_beam_ship:
                    self._fire_beam(p.beam360_active)
                elif is_electric_ship:
                    if p.elec360_active:
                        self._fire_electric(full_360=True)
                    else:
                        self._fire_electric(full_360=False)
                else:
                    self._shoot_toward(self.mouse_x, self.mouse_y)
                self.fire_timer -= rate

        # Update beams
        self.beams = [b for b in self.beams if b.life > 0]
        for beam in self.beams:
            beam.update(delta)

        # Update electric bolts
        self.elec_bolts.update(delta)
        self.enemy_elec_bolts.update(delta)
        for bolt in list(self.elec_bolts):
            if bolt.life <= 0:
                bolt.remove_from_sprite_lists()
        for bolt in list(self.enemy_elec_bolts):
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
        for b in list(self.enemy_elec_bolts):
            if b.life<=0 or b.right<-40 or b.left>ww+40 or b.top<-40 or b.bottom>hh+40:
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

        dp  = self._dpreset
        lvl = LEVELS[self.selected_level]

        # ── Boss lockout: while any boss lives, freeze all other spawns ──
        self.boss_on_screen = len(self.bosses) > 0

        reg_on_screen = len(self.enemies) + len(self.shooting_enemies)

        if not self.boss_on_screen and not self.level_boss_spawned:
            # ── Regular enemy spawning (quota-based) ─────────────────────
            self.enemy_spawn += delta
            if (self.enemy_spawn >= lvl["spawn_rate"]
                    and self.level_enemies_remaining > 0
                    and reg_on_screen < dp["max_regular_enemies"]):
                self.spawn_enemy(difficulty)
                self.level_enemies_remaining -= 1
                self.enemy_spawn = 0.0

            # ── Shooting enemy spawning ───────────────────────────────────
            self.shooting_spawn += delta
            if (self.shooting_spawn >= lvl["shoot_rate"]
                    and self.level_shooting_remaining > 0
                    and reg_on_screen < dp["max_regular_enemies"]):
                self.spawn_shooting_enemy(difficulty)
                self.level_shooting_remaining -= 1
                self.shooting_spawn = 0.0

            # ── Boss spawns only when ALL enemies have been sent AND screen clear ──
            all_sent = (self.level_enemies_remaining == 0
                        and self.level_shooting_remaining == 0)
            if all_sent and reg_on_screen == 0:
                self.spawn_level_boss()
                self.level_boss_spawned = True
                self.boss_on_screen = True  # prevent same-frame false clear trigger

        # ── Level clear detection ─────────────────────────────────────────
        if (self.level_boss_spawned
                and not self.boss_on_screen
                and not self.level_complete):
            self.level_complete = True
            self._level_clear_timer = 4.5
            self.completed_levels.add(self.selected_level)   # unlock next
            reward = lvl["reward_coins"]
            self.coins     += reward
            self.run_coins += reward
            # record best score
            prev = self.best_scores.get(self.selected_level, 0)
            if self.score > prev:
                self.best_scores[self.selected_level] = self.score
            self._save_progress()
            self.notif_text  = f"LEVEL CLEAR!  +{reward} coins"
            self.notif_color = (120, 255, 130)
            self.notif_timer = 3.5

        if self.level_complete:
            self._level_clear_timer -= delta
            if self._level_clear_timer <= 0:
                self.game_state = STATE_LEVEL_SELECT

        self.update_enemies(delta, difficulty)
        self.check_collisions()
        self._check_auto_triggers()

    # ──────────────────────────────────────────────────
    #  ENEMY AI
    # ──────────────────────────────────────────────────

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
            base = math.atan2(self.mouse_y - py, self.mouse_x - px)
            for ang in ([base - 0.18, base, base + 0.18]
                        if self.player.triple_active else [base]):
                self.beams.append(BeamRay(px, py, ang, color=bc))
                # Small muzzle flash along each beam
                for _ in range(5):
                    off = random.uniform(-0.15, 0.15)
                    spd = random.uniform(150, 320)
                    self._add_particle(
                        px + math.cos(ang)*random.uniform(8, 20),
                        py + math.sin(ang)*random.uniform(8, 20),
                        math.cos(ang+off)*spd, math.sin(ang+off)*spd,
                        random.uniform(1.6, 2.8), random.uniform(0.06, 0.14),
                        (255, 160, 80), 0.85)

    def _fire_electric(self, full_360: bool = False, aim_x=None, aim_y=None) -> None:
        """Fire electric bolt(s) from the Reaper ship."""
        px, py = self.player.center_x, self.player.center_y

        if full_360:
            # Short-range 360° storm around the ship.
            for i in range(ELECTRIC_360_COUNT):
                ang  = i * (math.tau / ELECTRIC_360_COUNT)
                bolt = ElectricBolt(
                    px, py, ang,
                    damage=ELECTRIC_360_DAMAGE,
                    boss_damage=ELECTRIC_360_BOSS_DAMAGE,
                    max_range=ELECTRIC_360_RADIUS
                )
                self.elec_bolts.append(bolt)
            # Dense local storm effect
            self._burst(px, py, 44, (130, 90, 255), 100, 330, 2.0, 4.5, .12, .35)
            self._burst(px, py, 20, (210, 180, 255), 50, 180, 1.2, 2.8, .08, .22)
            # Screen flash
            self.damage_flash = max(self.damage_flash, 0.45)
            self.notif_text   = "⚡ 360° ELECTRIC STORM!"
            self.notif_color  = (150, 100, 255)
            self.notif_timer  = 1.4
        else:
            tx = self.mouse_x if aim_x is None else aim_x
            ty = self.mouse_y if aim_y is None else aim_y
            base = math.atan2(ty - py, tx - px)
            for ang in ([base - 0.18, base, base + 0.18]
                        if self.player.triple_active else [base]):
                self.elec_bolts.append(ElectricBolt(px, py, ang))
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

    def _fire_final_boss_electric_storm(self, boss: BossEnemy) -> None:
        px, py = boss.center_x, boss.center_y
        for i in range(FINAL_BOSS_ELECTRIC_COUNT):
            ang = i * (math.tau / FINAL_BOSS_ELECTRIC_COUNT)
            self.enemy_elec_bolts.append(
                ElectricBolt(
                    px, py, ang,
                    damage=FINAL_BOSS_ELECTRIC_DAMAGE,
                    boss_damage=0,
                    max_range=FINAL_BOSS_ELECTRIC_RADIUS
                )
            )
        self._burst(px, py, 56, (150, 95, 255), 110, 360, 2.1, 4.8, .12, .34)
        self._burst(px, py, 24, (220, 200, 255), 60, 200, 1.3, 2.8, .08, .20)

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
            boss.electric_timer += delta

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

            if getattr(boss, "is_final_boss", False):
                dist = math.hypot(p.center_x - boss.center_x, p.center_y - boss.center_y)
                if dist <= FINAL_BOSS_ELECTRIC_RANGE and boss.electric_timer >= FINAL_BOSS_ELECTRIC_FIRE_RATE:
                    self._fire_final_boss_electric_storm(boss)
                    boss.electric_timer = 0.0

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
                enemy.health -= bolt.damage
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
                boss.health -= bolt.boss_damage
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

        for bolt in list(self.enemy_elec_bolts):
            if not arcade.check_for_collision(bolt, p):
                continue
            hx, hy = bolt.center_x, bolt.center_y
            bolt.remove_from_sprite_lists()
            if p.shield_active:
                self._burst(hx, hy, 12, (120, 220, 255), 90, 240, 1.3, 2.8, .08, .20)
            else:
                p.health -= bolt.damage
                self.combo = 0
                self.damage_flash = max(self.damage_flash, 1.0)
                self._burst(hx, hy, 22, (160, 110, 255), 95, 280, 1.7, 3.8, .12, .26)

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
        storage_limit = MAZE_BREACH_MAX_STORAGE if kind == "breach" else MAX_POWERUP_STORAGE
        if p.inventory[kind] < storage_limit:
            p.inventory[kind] += 1
            self.notif_text  = f"{POWERUP_LABELS[kind]} STORED  [{p.inventory[kind]}/{storage_limit}]"
            self.notif_color = _notif_color(kind);  self.notif_timer = 1.0
        else:
            if kind in ("elec360", "breach"):
                self.notif_text  = f"{POWERUP_LABELS[kind]} STORAGE FULL!"
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
                "speed":    ("SPEED BOOST!",          (255, 220, 120)),
                "triple":   ("TRIPLE SHOT!",          (255, 180, 120)),
                "beam360":  ("360° BEAM BURST!",      (255, 120,  50)),
                "elec360":  ("⚡ 360° ELECTRIC MODE!", (160, 110, 255)),
                "breach":   ("BREACH ROUNDS ARMED!",  (255, 205,  80))}
        text, color = msgs.get(kind, (kind.upper() + "!", (255, 255, 255)))
        self.notif_text  = ("STORAGE FULL - " + text) if immediate else text
        self.notif_color = color;  self.notif_timer = 1.6
        setattr(p, f"{kind}_active", True)
        if kind == "elec360":
            duration = ELECTRIC_360_DURATION
        elif kind == "breach":
            duration = MAZE_BREACH_DURATION
        else:
            duration = POWERUP_DURATION
        setattr(p, f"{kind}_timer", duration)

    def _try_drop_powerup(self, x, y, boss=False):
        lucky_bonus = self.upgrades.get("lucky", 0) * 15
        threshold   = (100 if boss else DROP_CHANCE) + lucky_bonus
        if random.randint(1, 100) > threshold:
            return
        # Build pool: universal powerups + ship-specific if applicable
        pool = [k for k in POWERUP_TYPES
                if k not in BEAM_ONLY_POWERUPS
                and k not in ELECTRIC_ONLY_POWERUPS
                and k not in BREACH_ONLY_POWERUPS]
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
            data = {
                "coins":            self.coins,
                "upgrades":         self.upgrades,
                "best_scores":      {str(k): v for k, v in self.best_scores.items()},
                "completed_levels": list(self.completed_levels),
            }
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
                self.upgrades[iid] = min(int(saved_upg.get(iid, 0)), item["max"])
            self.best_scores      = {int(k): v for k, v in
                                     data.get("best_scores", {}).items()}
            self.completed_levels = set(data.get("completed_levels", []))
        except (OSError, ValueError, KeyError):
            pass

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

    def spawn_level_boss(self):
        """Spawn the level boss whose HP equals the combined HP of all level enemies."""
        lvl  = LEVELS[self.selected_level]
        dp   = self._dpreset
        difficulty = min(3.0, self.time_alive / 90.0)
        mult = dp["boss_health_mult"] * (1 + 0.2 * difficulty)
        if self.selected_level == len(LEVELS) - 1:
            boss_hp = _campaign_total_boss_hp(mult)
        else:
            # Combined HP of every enemy in the level
            boss_hp = _level_boss_hp(
                lvl["regular_enemies"],
                lvl["shooting_enemies"],
                lvl["boss_hp_mult"] * mult
            )
        boss = BossEnemy(
            self.width // 2,
            self.height + 55,
            boss_hp,
            texture_path=lvl.get("boss_texture", "image/boss.png"),
            texture_scale=lvl.get("boss_texture_scale", 0.2),
            boss_name=lvl.get("boss_name", "BOSS"),
        )
        if self.selected_level == len(LEVELS) - 1:
            boss.is_final_boss = True
        self.bosses.append(boss)
        lc = lvl["color"]
        self.notif_text  = f"⚠  {boss.boss_name} INBOUND  —  {boss_hp:,} HP!"
        self.notif_color = lc
        self.notif_timer = 3.0

    # ══════════════════════════════════════════════════
    #  INPUT
    # ══════════════════════════════════════════════════

    def _update_mouse_pos(self, x: float, y: float) -> None:
        self.mouse_x = max(0, min(self.width, x))
        self.mouse_y = max(0, min(self.height, y))

    def on_mouse_motion(self, x, y, dx, dy):
        self._update_mouse_pos(x, y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self._update_mouse_pos(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        self._update_mouse_pos(x, y)
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self._screen_transition:
            return

        # ── Maze mode: left-click starts firing ──────
        if self.game_state == STATE_MAZE:
            self.mouse_held = True
            return

        if self.game_state == STATE_MODE_SELECT:
            for name, rect in self._mode_btns.items():
                l, r, b, t = rect
                if l <= x <= r and b <= y <= t:
                    if name == "__enter__":
                        if self.selected_mode == "normal":
                            self.game_state = STATE_MENU
                        elif self.selected_mode == "maze":
                            self.game_state = STATE_MAZE_SELECT
                    elif name in ("normal", "maze"):
                        self.selected_mode = name
                    return
            return

        if self.game_state == STATE_MAZE_SELECT:
            for name, rect in self._maze_preset_btns.items():
                l, r, b, t = rect
                if l <= x <= r and b <= y <= t:
                    if name == "__play__":
                        self._start_maze_with_preset()
                    elif name == "__back__":
                        self.game_state = STATE_MODE_SELECT
                    else:
                        self.selected_maze_preset = name
                    return
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
                            self._start_screen_transition(STATE_MENU, STATE_LEVEL_SELECT)
                        else:
                            self._resume_from_pause()
                    elif name == "shop":
                        self._open_shop(self.game_state)
                    elif name == "reset":
                        if self.game_state == STATE_PAUSED:
                            self._reset_from_pause()
                        else:
                            self.setup()
                    elif name == "quit":
                        if self.game_state == STATE_PAUSED:
                            self._quit_from_pause()
                        else:
                            self.game_state = STATE_MENU
                            self.set_mouse_visible(True)
                    elif name == "theme":
                        self.menu_theme = "light" if self.menu_theme=="dark" else "dark"
                    return
            return

        if self.game_state == STATE_SHOP:
            for name, rect in self._shop_btns.items():
                l, r, b, t = rect
                if l<=x<=r and b<=y<=t:
                    if name == "__back__":
                        self._close_shop()
                    else:
                        self._purchase_shop_item(name)
                    return
            return

        # ── Level select clicks ───────────────────────────────────────────
        if self.game_state == STATE_LEVEL_SELECT:
            for idx, (cl, cr, cb_, ct) in getattr(self, "_level_cards", {}).items():
                if cl<=x<=cr and cb_<=y<=ct:
                    req = LEVELS[idx]["requires_level"]
                    unlocked = (req < 0) or (req in self.completed_levels)
                    if unlocked:
                        self.selected_level = idx
                    return
            # Difficulty buttons
            for dkey, (l, r, b, t) in getattr(self, "_ls_diff_btns", {}).items():
                if l<=x<=r and b<=y<=t:
                    self.selected_difficulty = dkey
                    self._dpreset = DIFFICULTY_PRESETS[dkey]
                    return
            # Play level
            if hasattr(self, "_ls_play_btn"):
                l, r, b, t = self._ls_play_btn
                if l<=x<=r and b<=y<=t:
                    self.setup()
                    return
            # Back
            if hasattr(self, "_ls_back_btn"):
                l, r, b, t = self._ls_back_btn
                if l<=x<=r and b<=y<=t:
                    self.game_state = STATE_MENU
                    return
            return

        if self.game_state == STATE_PLAYING:
            self._update_mouse_pos(x, y)

    def on_mouse_release(self, x, y, button, modifiers):
        self._update_mouse_pos(x, y)
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.mouse_held = False

    def _sync_movement_flags(self):
        self.up        = any(k in self._held_move_keys for k in (arcade.key.W, arcade.key.UP))
        self.down      = any(k in self._held_move_keys for k in (arcade.key.S, arcade.key.DOWN))
        self.left_key  = any(k in self._held_move_keys for k in (arcade.key.A, arcade.key.LEFT))
        self.right_key = any(k in self._held_move_keys for k in (arcade.key.D, arcade.key.RIGHT))

    def _clear_movement_input(self):
        self._held_move_keys.clear()
        self.up = self.down = self.left_key = self.right_key = False
        if self.player is not None:
            self.player.change_x = 0.0
            self.player.change_y = 0.0

    def _enter_pause(self, return_state: str) -> None:
        self._pause_return_state = return_state
        self.game_state = STATE_PAUSED
        self._clear_movement_input()
        self.mouse_held = False
        self.set_mouse_visible(True)

    def _resume_from_pause(self) -> None:
        resume_state = self._pause_return_state or STATE_PLAYING
        self._pause_return_state = None
        self.game_state = resume_state
        self.mouse_held = False
        self.set_mouse_visible(False)

    def _quit_from_pause(self) -> None:
        paused_from = self._pause_return_state or STATE_PLAYING
        self._pause_return_state = None
        self._clear_movement_input()
        self.mouse_held = False
        self.game_state = STATE_MAZE_SELECT if paused_from == STATE_MAZE else STATE_MENU
        self.set_mouse_visible(True)

    def _reset_from_pause(self) -> None:
        paused_from = self._pause_return_state or STATE_PLAYING
        self._pause_return_state = None
        self.mouse_held = False
        if paused_from == STATE_MAZE:
            self._start_maze_with_preset()
        else:
            self.setup()

    def on_key_press(self, key, modifiers):
        if self._screen_transition and key != arcade.key.F11:
            return

        if key in {arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
                   arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT}:
            self._held_move_keys.add(key)
            self._sync_movement_flags()
            return

        if key == arcade.key.ESCAPE:
            if self.game_state == STATE_MODE_SELECT:
                pass  # nothing to go back to on the first screen
            elif self.game_state == STATE_MENU:
                self.game_state = STATE_MODE_SELECT
                self.set_mouse_visible(True)
            elif self.game_state == STATE_MAZE_SELECT:
                self.game_state = STATE_MODE_SELECT
            elif self.game_state == STATE_MAZE:
                self._enter_pause(STATE_MAZE)
            elif self.game_state == STATE_MAZE_OVER:
                self.game_state = STATE_MAZE_SELECT
                self.set_mouse_visible(True)
            elif self.game_state == STATE_PLAYING:
                self._enter_pause(STATE_PLAYING)
            elif self.game_state == STATE_PAUSED:
                self._resume_from_pause()
            elif self.game_state == STATE_SHOP:
                self._close_shop()
            elif self.game_state == STATE_LEVEL_SELECT:
                self.game_state = STATE_MENU

        elif key == arcade.key.H:
            if self.game_state in (STATE_PLAYING, STATE_PAUSED):
                self.show_hud = not self.show_hud

        elif key == arcade.key.R and self.game_state == STATE_GAMEOVER:
            self.setup()

        elif key == arcade.key.R and self.game_state == STATE_MAZE_OVER:
            self._start_maze_with_preset()

        elif key == arcade.key.F11:
            self._toggle_fullscreen()

        elif key in POWERUP_KEYS:
            if self.game_state == STATE_PLAYING:
                self._use_stored_powerup(POWERUP_KEYS[key])
            elif self.game_state == STATE_MAZE and POWERUP_KEYS[key] == "breach":
                self._use_stored_powerup("breach")

    def on_key_release(self, key, modifiers):
        if key in {arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
                   arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT}:
            self._held_move_keys.discard(key)
            self._sync_movement_flags()

    def on_deactivate(self):
        self._clear_movement_input()

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
        if kind == "elec360":
            self._activate_powerup(kind)
            self._fire_electric(full_360=True)
            self.fire_timer = 0.0
            return
        self._activate_powerup(kind)
