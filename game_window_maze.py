from game_support import *

import arcade
import math
import random


FONT_UI_MENU = ("Avenir Next", "Verdana", "Trebuchet MS", "Arial")
FONT_NUMERIC = ("SF Mono", "Menlo", "Monaco", "Courier New", "monospace")


class MazeModeMixin:

    # ══════════════════════════════════════════════════
    #  MAZE MODE — SETUP
    # ══════════════════════════════════════════════════

    def setup_maze(self, keep_player: bool = False):
        """Generate a new maze level.  Call with keep_player=True to retain HP between floors."""
        w, h  = self.width, self.height
        lvl   = self.maze_level
        cs    = MAZE_CELL_SIZE
        preset = getattr(self, "maze_preset", None) or MAZE_PRESETS[0]

        # Maze dimensions grow each floor — NOT capped by the screen size
        cols = MAZE_BASE_COLS + preset["cols_bonus"] + lvl * 3
        rows = MAZE_BASE_ROWS + preset["rows_bonus"] + lvl * 2
        cols = max(9, cols)
        rows = max(7, rows)
        # Keep odd dimensions (nicer-looking mazes)
        if cols % 2 == 0: cols -= 1
        if rows % 2 == 0: rows -= 1

        # Place maze at world origin — camera scrolls to show the player's area
        ox = 0
        oy = 0

        self.maze_grid      = MazeGrid(cols, rows, seed=random.randint(0, 999999))
        self.maze_grid.open_start_area()
        self.maze_cell_size = cs
        self.maze_origin    = (float(ox), float(oy))
        self.maze_exit_col  = cols - 1
        self.maze_exit_row  = 0           # bottom-right cell

        # ── Player ──────────────────────────────────
        ship = SHIPS[self.selected_ship]
        if self.player is None or not keep_player:
            self.player = Player()
            armor_tier   = self.upgrades.get("armor", 0)
            base_hp      = int(PLAYER_HEALTH * ship["hp_mult"]) + armor_tier * 25
            self.player.max_health = base_hp
            self.player.health     = base_hp
        tex = load_texture_clean(ship["texture"], ship["tex_scale"])
        self.player.texture  = tex
        # Spawn at top-left cell
        player_start_x = ox + 0.5 * cs
        player_start_y = oy + (rows - 0.5) * cs
        self.player.center_x = player_start_x
        self.player.center_y = player_start_y
        self.player.change_x = 0.0;  self.player.change_y = 0.0
        self.player.angle    = -90.0   # face RIGHT (90° clockwise from default up)

        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)

        # ── Sprite lists ────────────────────────────
        self.bullets       = arcade.SpriteList()
        self.enemy_bullets = arcade.SpriteList()
        self.powerups      = arcade.SpriteList()
        self.coins_list    = arcade.SpriteList()

        # ── Maze combat state ────────────────────────
        self.maze_enemies       = arcade.SpriteList()   # MazeEnemy sprites
        self.maze_bullets       = arcade.SpriteList()   # player bullets (wall-blocked)
        self.maze_enemy_bullets = arcade.SpriteList()   # enemy bullets  (wall-blocked)
        self.maze_spawn_timer   = 3.0                   # first enemy after 3 s

        # ── Initialise camera centred on player spawn ──
        total_w = cols * cs
        total_h = rows * cs
        self.maze_cam_x = max(ox, min(ox + total_w - w, player_start_x - w / 2))
        self.maze_cam_y = max(oy, min(oy + total_h - h, player_start_y - h / 2))

        # Create / reset the arcade 3 camera (position = centre of viewport in world space)
        self.maze_camera = arcade.camera.Camera2D()
        self.maze_camera.position = (
            self.maze_cam_x + w / 2,
            self.maze_cam_y + h / 2,
        )

        # ── Runtime reset ───────────────────────────
        self.score              = getattr(self, "score", 0)
        self.fire_timer         = 0.0
        self.notif_text         = f"MAZE  LEVEL  {lvl + 1}"
        self.notif_color        = (120, 255, 160)
        self.notif_timer        = 2.0
        self.damage_flash       = 0.0
        self.contact_damage_timer = 0.0
        self.particles          = []
        self.maze_exit_reached  = False
        self.boss_on_screen     = False

        self._pause_return_state = None
        self.game_state = STATE_MAZE
        self.set_mouse_visible(False)

    # ══════════════════════════════════════════════════
    #  MAZE MODE — DRAW
    # ══════════════════════════════════════════════════

    def _maze_can_move_to(self, x: float, y: float, radius: float) -> bool:
        """True if a circle (x,y,radius) fits at that position without hitting walls."""
        maze = self.maze_grid
        cs   = self.maze_cell_size
        ox, oy = self.maze_origin
        wt2  = MAZE_WALL_THICK // 2 + 2   # +2 px safety

        if x - radius < ox or x + radius > ox + maze.cols * cs:
            return False
        if y - radius < oy or y + radius > oy + maze.rows * cs:
            return False

        col = max(0, min(maze.cols - 1, int((x - ox) / cs)))
        row = max(0, min(maze.rows - 1, int((y - oy) / cs)))

        cell_l = ox + col * cs;  cell_r = cell_l + cs
        cell_b = oy + row * cs;  cell_t = cell_b + cs

        if x + radius > cell_r - wt2 and not maze.is_open(col, row, MazeGrid.E):
            return False
        if x - radius < cell_l + wt2 and not maze.is_open(col, row, MazeGrid.W):
            return False
        if y + radius > cell_t - wt2 and not maze.is_open(col, row, MazeGrid.N):
            return False
        if y - radius < cell_b + wt2 and not maze.is_open(col, row, MazeGrid.S):
            return False
        return True

    def _maze_player_cell(self) -> tuple[int, int]:
        ox, oy = self.maze_origin
        cs = self.maze_cell_size
        col = max(0, min(self.maze_grid.cols - 1, int((self.player.center_x - ox) / cs)))
        row = max(0, min(self.maze_grid.rows - 1, int((self.player.center_y - oy) / cs)))
        return col, row

    def _draw_maze_world(self):
        w, h   = self.width, self.height
        t      = self.bg_time
        maze   = self.maze_grid
        cs     = self.maze_cell_size
        ox, oy = self.maze_origin
        wt     = MAZE_WALL_THICK
        wt2    = wt // 2
        FU     = FONT_UI_MENU
        FN     = FONT_NUMERIC

        WALL_C  = (30, 220, 140)   # neon green
        FLOOR_C = (6,  14,  20)    # near-black floor
        EXIT_C  = (80, 255, 190)   # cyan-green exit
        ENTRY_C = (90, 198, 255)   # blue entry

        # ── Apply scrolling camera viewport ─────────
        # Activate the maze camera so all world-space drawing is offset correctly.
        cam_x = self.maze_cam_x
        cam_y = self.maze_cam_y
        if self.maze_camera is not None:
            self.maze_camera.use()

        # ── Background (fill the whole world) ───────
        arcade.draw_lrbt_rectangle_filled(
            ox, ox + maze.cols * cs, oy, oy + maze.rows * cs, (4, 8, 14))
        # Also fill outside-maze areas visible at edges
        arcade.draw_lrbt_rectangle_filled(
            cam_x - 10, cam_x + w + 10, cam_y - 10, cam_y + h + 10, (2, 4, 8))

        # ── Floor tiles ─────────────────────────────
        # Culling: only draw cells visible in the viewport
        col_min = max(0, int((cam_x - ox) / cs) - 1)
        col_max = min(maze.cols - 1, int((cam_x - ox + w) / cs) + 1)
        row_min = max(0, int((cam_y - oy) / cs) - 1)
        row_max = min(maze.rows - 1, int((cam_y - oy + h) / cs) + 1)

        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                fl = ox + col * cs
                fb = oy + row * cs
                arcade.draw_lrbt_rectangle_filled(fl, fl + cs, fb, fb + cs, FLOOR_C)

        # Subtle floor grid
        gc = (0, 35, 22, 35)
        for row in range(row_min, row_max + 2):
            yy = oy + row * cs
            arcade.draw_line(ox + col_min * cs, yy, ox + (col_max + 1) * cs, yy, gc, 1)
        for col in range(col_min, col_max + 2):
            xx = ox + col * cs
            arcade.draw_line(xx, oy + row_min * cs, xx, oy + (row_max + 1) * cs, gc, 1)

        # ── Walls ───────────────────────────────────
        p2 = 0.5 + 0.5 * math.sin(t * 1.8)
        wc = (int(25 + 25 * p2), int(210 + 25 * p2), int(130 + 25 * p2), 255)
        gw = (*wc[:3], 60)

        # Outer border (always solid)
        bx = ox - wt2;  by = oy - wt2
        bw2 = maze.cols * cs + wt;  bh2 = maze.rows * cs + wt
        arcade.draw_lrbt_rectangle_filled(bx, bx + bw2, by, by + wt, wc)
        arcade.draw_lrbt_rectangle_filled(bx, bx + bw2, by + bh2 - wt, by + bh2, wc)
        arcade.draw_lrbt_rectangle_filled(bx, bx + wt,  by, by + bh2, wc)
        arcade.draw_lrbt_rectangle_filled(bx + bw2 - wt, bx + bw2, by, by + bh2, wc)

        # Internal walls — only visible cells, only closed passages
        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                cl2 = ox + col * cs;  cr2 = cl2 + cs
                cb2 = oy + row * cs;  ct2 = cb2 + cs
                if row < maze.rows - 1 and not maze.is_open(col, row, MazeGrid.N):
                    arcade.draw_lrbt_rectangle_filled(cl2, cr2, ct2 - wt2, ct2 + wt2, wc)
                    arcade.draw_lrbt_rectangle_filled(cl2 + wt2, cr2 - wt2, ct2 - wt2 - 2, ct2 + wt2 + 2, gw)
                if col < maze.cols - 1 and not maze.is_open(col, row, MazeGrid.E):
                    arcade.draw_lrbt_rectangle_filled(cr2 - wt2, cr2 + wt2, cb2, ct2, wc)
                    arcade.draw_lrbt_rectangle_filled(cr2 - wt2 - 2, cr2 + wt2 + 2, cb2 + wt2, ct2 - wt2, gw)

        # ── Exit portal ─────────────────────────────
        ec2, er2 = self.maze_exit_col, self.maze_exit_row
        ex2 = ox + (ec2 + 0.5) * cs
        ey2 = oy + (er2 + 0.5) * cs
        pr  = cs * 0.33
        ep  = 0.5 + 0.5 * math.sin(t * 4.8)
        arcade.draw_circle_filled(ex2, ey2, pr + 10 * ep, (0, 100, 60, 50))
        arcade.draw_circle_filled(ex2, ey2, pr,            (*EXIT_C, 130))
        arcade.draw_circle_outline(ex2, ey2, pr,            EXIT_C, 3)
        arcade.draw_circle_outline(ex2, ey2, pr + 10 * ep, (*EXIT_C[:3], int(70 * ep)), 2)
        arcade.draw_text("EXIT", ex2, ey2,
                         (80, 255, 180, 210), 9, anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)

        # ── Entry glow ──────────────────────────────
        enx = ox + 0.5 * cs
        eny = oy + (maze.rows - 0.5) * cs
        arcade.draw_circle_filled(enx, eny, 14, (*ENTRY_C[:3], 45))

        # ── Particles (world space) ──────────────────
        self._draw_particles()

        # ── Enemies ──────────────────────────────────
        for enemy in self.maze_enemies:
            # Glow ring
            arcade.draw_circle_filled(
                enemy.center_x, enemy.center_y, 26, (255, 70, 70, 45))
            arcade.draw_sprite(enemy)
            # Health bar (only when damaged)
            if enemy.health < enemy.max_health:
                bar_w  = cs * 0.68
                bx_    = enemy.center_x - bar_w / 2
                by_    = enemy.center_y + 24
                ratio_ = max(0.0, enemy.health / enemy.max_health)
                arcade.draw_lrbt_rectangle_filled(
                    bx_, bx_ + bar_w, by_, by_ + 5, (60, 0, 0, 200))
                arcade.draw_lrbt_rectangle_filled(
                    bx_, bx_ + bar_w * ratio_, by_, by_ + 5, (255, 55, 55, 230))

        # ── Bullets ──────────────────────────────────
        self.maze_bullets.draw()
        self.maze_enemy_bullets.draw()

        # ── Player ──────────────────────────────────
        if self.player:
            p  = self.player
            pg = (95, 200, 255, 68)
            arcade.draw_circle_filled(p.center_x, p.center_y, 34, pg)
            if p.shield_active:
                rr = 34 + 2.5 * math.sin(t * 9)
                arcade.draw_circle_outline(p.center_x, p.center_y, rr, (90, 235, 255, 230), 3)
            self.player_list.draw()

        # ── Damage flash (covers visible screen area while camera is active) ──
        if self.damage_flash > 0:
            arcade.draw_lrbt_rectangle_filled(
                cam_x, cam_x + w, cam_y, cam_y + h,
                (255, 55, 55, int(165 * self.damage_flash)))

        # ── Crosshair (drawn in world space at mouse pos) ──
        # Convert mouse screen coords → world coords
        mx_world = cam_x + self.mouse_x
        my_world = cam_y + self.mouse_y
        cc = (130, 220, 255, 185)
        arcade.draw_circle_outline(mx_world, my_world, 13, cc, 2)
        for x1, y1, x2, y2 in [
            (mx_world - 20, my_world, mx_world - 8, my_world),
            (mx_world + 8,  my_world, mx_world + 20, my_world),
            (mx_world, my_world - 20, mx_world, my_world - 8),
            (mx_world, my_world + 8,  mx_world, my_world + 20),
        ]:
            arcade.draw_line(x1, y1, x2, y2, cc, 2)

        # ── Reset to screen viewport for HUD ────────
        self.default_camera.use()

        # ── HUD (screen space) ──────────────────────
        self._draw_maze_hud()

    def _draw_maze_hud(self):
        w, h   = self.width, self.height
        t      = self.bg_time
        p      = self.player
        FU     = FONT_UI_MENU
        FN     = FONT_NUMERIC

        # ── Health bar ──────────────────────────────
        hp_ratio = max(0.0, p.health / p.max_health)
        bar_w = min(220, int(w * 0.28));  bar_h = 14
        bx2 = 16;  by2 = h - 36
        arcade.draw_lrbt_rectangle_filled(bx2, bx2 + bar_w, by2, by2 + bar_h, (22, 30, 48, 220))
        fill_w = int(bar_w * hp_ratio)
        hp_c = (60, 225, 100) if hp_ratio > 0.5 else (255, 210, 30) if hp_ratio > 0.25 else (255, 55, 55)
        arcade.draw_lrbt_rectangle_filled(bx2, bx2 + fill_w, by2, by2 + bar_h, (*hp_c, 220))
        arcade.draw_lrbt_rectangle_outline(bx2, bx2 + bar_w, by2, by2 + bar_h, (80, 130, 190, 180), 1)
        self._txt_shadow(f"HP  {p.health} / {p.max_health}",
                         bx2 + bar_w // 2, by2 + 1, (200, 225, 255, 215),
                         8, FN, anchor_x="center")

        # ── Score ───────────────────────────────────
        self._txt_shadow(f"SCORE  {self.score:,}", w - 16, h - 28,
                         (210, 235, 255, 240), 18, FU, anchor_x="right", bold=True)

        # ── Maze floor badge ────────────────────────
        lbl = f"FLOOR  {self.maze_level + 1}"
        self._txt_shadow(lbl, w // 2, h - 28, (100, 255, 160, 230),
                         14, FU, anchor_x="center", bold=True)

        # ── Timer ───────────────────────────────────
        self._txt_shadow(f"{self.time_alive:06.1f}s", w - 16, h - 52,
                         (165, 200, 255, 210), 11, FN, anchor_x="right", bold=True)

        # ── Hint ────────────────────────────────────
        arcade.draw_text("WASD Move · Hold LMB to Fire · Find the EXIT · ESC Pause · H Hide HUD",
                         w // 2, 12, (70, 100, 155, 130), 8,
                         anchor_x="center", font_name=FN)

        # ── Notification ────────────────────────────
        if self.notif_timer > 0:
            a = min(255, int(self.notif_timer * 300))
            self._txt_shadow(self.notif_text, w // 2, h // 2 + 90,
                             (*self.notif_color[:3], a), 26, FU,
                             anchor_x="center", bold=True)

        # ── Minimap ─────────────────────────────────
        self._draw_maze_minimap()

    def _draw_maze_minimap(self):
        maze   = self.maze_grid
        mm_cs  = max(4, min(9, 90 // max(maze.cols, maze.rows)))
        mx     = 16
        my     = self.height - 110 - maze.rows * mm_cs
        mw     = maze.cols * mm_cs
        mh     = maze.rows * mm_cs

        # Panel
        arcade.draw_lrbt_rectangle_filled(mx - 4, mx + mw + 4, my - 4, my + mh + 4, (0, 0, 0, 170))
        arcade.draw_lrbt_rectangle_outline(mx - 4, mx + mw + 4, my - 4, my + mh + 4,
                                            (0, 170, 90, 160), 1)

        MWTT = max(1, mm_cs // 5)
        wc2  = (0, 200, 110, 200)

        # Floors
        for row in range(maze.rows):
            for col in range(maze.cols):
                fx = mx + col * mm_cs;  fy = my + row * mm_cs
                arcade.draw_lrbt_rectangle_filled(fx, fx + mm_cs, fy, fy + mm_cs, (10, 26, 20))

        # Walls
        for row in range(maze.rows):
            for col in range(maze.cols):
                fx = mx + col * mm_cs;  fy = my + row * mm_cs
                if row < maze.rows - 1 and not maze.is_open(col, row, MazeGrid.N):
                    arcade.draw_lrbt_rectangle_filled(
                        fx, fx + mm_cs,
                        fy + mm_cs - MWTT, fy + mm_cs + MWTT, wc2)
                if col < maze.cols - 1 and not maze.is_open(col, row, MazeGrid.E):
                    arcade.draw_lrbt_rectangle_filled(
                        fx + mm_cs - MWTT, fx + mm_cs + MWTT,
                        fy, fy + mm_cs, wc2)

        # Border
        arcade.draw_lrbt_rectangle_outline(mx, mx + mw, my, my + mh, wc2, MWTT)

        # Exit marker
        ex2 = mx + (self.maze_exit_col + 0.5) * mm_cs
        ey2 = my + (self.maze_exit_row + 0.5) * mm_cs
        arcade.draw_circle_filled(ex2, ey2, mm_cs * 0.45, (0, 255, 155, 210))

        # Player marker
        pc2, pr2 = self._maze_player_cell()
        px3 = mx + (pc2 + 0.5) * mm_cs
        py3 = my + (pr2 + 0.5) * mm_cs
        arcade.draw_circle_filled(px3, py3, mm_cs * 0.46, (90, 200, 255, 245))

    def _draw_maze_over(self):
        """Overlay shown on maze death."""
        w, h  = self.width, self.height
        FU    = FONT_UI_MENU
        FN    = FONT_NUMERIC

        self._draw_maze_world()
        # default_camera is already active after _draw_maze_world returns

        # Dim overlay
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (3, 5, 14, 180))

        # Card
        cw2 = min(480, int(w * 0.65));  ch2 = 260
        cx2 = (w - cw2) // 2;           cy2 = h // 2 - ch2 // 2
        arcade.draw_lrbt_rectangle_filled(cx2 + 6, cx2 + cw2 + 6, cy2 - 6, cy2 + ch2 - 6, (0, 0, 0, 70))
        arcade.draw_lrbt_rectangle_filled(cx2, cx2 + cw2, cy2, cy2 + ch2, (7, 10, 26, 240))
        arcade.draw_lrbt_rectangle_outline(cx2, cx2 + cw2, cy2, cy2 + ch2, (200, 35, 35, 200), 2)

        mid = w // 2
        self._txt_shadow("MAZE OVER", mid, cy2 + ch2 - 58, (255, 50, 50, 255),
                         50, FU, anchor_x="center", bold=True)
        arcade.draw_line(cx2 + 24, cy2 + ch2 - 78, cx2 + cw2 - 24, cy2 + ch2 - 78, (200, 35, 35, 130), 1)
        self._txt_shadow(f"FLOOR  {self.maze_level + 1}",
                         mid, cy2 + ch2 - 112, (120, 155, 215, 210), 12, FU, anchor_x="center")
        self._txt_shadow(f"SCORE  {self.score:,}", mid, cy2 + ch2 - 148,
                         (210, 235, 255, 245), 30, FN, anchor_x="center", bold=True)
        self._txt_shadow("R  —  RETRY  MAZE       ESC  —  BACK TO MENU",
                         mid, cy2 + 30, (130, 165, 215, 200), 13, FU, anchor_x="center")

    # ══════════════════════════════════════════════════
    #  MAZE MODE — UPDATE
    # ══════════════════════════════════════════════════

    def _update_maze(self, delta: float):
        """Full game-logic tick for maze mode."""
        self.time_alive += delta
        w, h   = self.width, self.height
        p      = self.player
        maze   = self.maze_grid
        cs     = self.maze_cell_size
        ox, oy = self.maze_origin

        # ── Player movement ──────────────────────────
        ix = float(self.right_key) - float(self.left_key)
        iy = float(self.up) - float(self.down)
        if ix and iy:
            ix *= 0.70710678;  iy *= 0.70710678
        ship_spd = p.get_speed() * SHIPS[self.selected_ship]["spd_mult"]
        sm = min(1.0, 14.0 * delta)
        p.change_x += (ix * ship_spd - p.change_x) * sm
        p.change_y += (iy * ship_spd - p.change_y) * sm

        PLAYER_R = cs * 0.30
        new_x = p.center_x + p.change_x * delta
        new_y = p.center_y + p.change_y * delta

        if self._maze_can_move_to(new_x, p.center_y, PLAYER_R):
            p.center_x = new_x
        else:
            p.change_x = 0.0
        if self._maze_can_move_to(p.center_x, new_y, PLAYER_R):
            p.center_y = new_y
        else:
            p.change_y = 0.0

        # Ship faces RIGHT (-90°) and tilts slightly based on vertical speed
        tilt = max(-20, min(20, p.change_y * 0.06))
        p.angle = -90.0 + tilt
        p.update_powerups(delta)

        # Engine trail — particles stream from the LEFT side (behind a rightward ship)
        mv = abs(p.change_x) + abs(p.change_y)
        if mv > 60 and random.random() < 0.50:
            ang = math.atan2(-p.change_y, -p.change_x) + random.uniform(-0.35, 0.35)
            self._add_particle(
                p.center_x + random.uniform(-4, 4),
                p.center_y + random.uniform(-4, 4),
                math.cos(ang) * random.uniform(55, 130),
                math.sin(ang) * random.uniform(55, 130),
                random.uniform(1.2, 2.2), random.uniform(0.10, 0.22),
                (90, 200, 255), 0.88)

        # ── Exit check ───────────────────────────────
        pc2, pr2 = self._maze_player_cell()
        if (pc2 == self.maze_exit_col and pr2 == self.maze_exit_row
                and not self.maze_exit_reached):
            self.maze_exit_reached = True
            bonus = max(0, 2000 - int(self.time_alive * 5))
            self.score += bonus
            self.maze_level += 1
            self.notif_text  = f"EXIT FOUND!  +{bonus} TIME BONUS  →  FLOOR {self.maze_level + 1}"
            self.notif_color = (120, 255, 160)
            self.notif_timer = 1.8
            self.setup_maze(keep_player=True)

        self._update_particles(delta)

        # ── Player shooting (hold left-mouse to fire) ────────────────
        if self.mouse_held:
            self.fire_timer += delta
            while self.fire_timer >= NORMAL_FIRE_RATE:
                self.fire_timer -= NORMAL_FIRE_RATE
                # Convert screen-space mouse → world coords
                mx_w = self.maze_cam_x + self.mouse_x
                my_w = self.maze_cam_y + self.mouse_y
                ang  = math.atan2(my_w - p.center_y, mx_w - p.center_x)
                b    = Bullet(p.center_x, p.center_y, ang)
                self.maze_bullets.append(b)
                self._spawn_muzzle(p.center_x, p.center_y, ang)
        else:
            self.fire_timer = 0.0

        # ── Move player bullets + wall collision ─────────────────────
        self.maze_bullets.update(delta)
        for b in list(self.maze_bullets):
            if b.life <= 0 or not self._maze_can_move_to(b.center_x, b.center_y, 5):
                self._burst(b.center_x, b.center_y, 5,
                            (180, 220, 255), 35, 110, 0.7, 1.6, .04, .12)
                b.remove_from_sprite_lists()

        # ── Move enemy bullets + wall collision ──────────────────────
        self.maze_enemy_bullets.update(delta)
        for b in list(self.maze_enemy_bullets):
            if b.life <= 0 or not self._maze_can_move_to(b.center_x, b.center_y, 5):
                self._burst(b.center_x, b.center_y, 5,
                            (255, 140, 80), 35, 110, 0.7, 1.6, .04, .12)
                b.remove_from_sprite_lists()

        max_enemies = min(12, 3 + self.maze_level * 2)

        # ── Enemy AI (move + shoot) ───────────────────────────────────
        pc, pr = self._maze_player_cell()
        for enemy in list(self.maze_enemies):
            enemy.maze_update(delta, pc, pr, maze, cs, ox, oy)

            enemy.shoot_timer -= delta
            if enemy.shoot_timer <= 0:
                enemy.shoot_timer = (MAZE_ENEMY_FIRE_RATE
                                     + random.uniform(-0.6, 0.6))
                ang = math.atan2(p.center_y - enemy.center_y,
                                 p.center_x  - enemy.center_x)
                eb = EnemyBullet(enemy.center_x, enemy.center_y,
                                 angle_rad=ang,
                                 speed=MAZE_ENEMY_BULLET_SPEED)
                eb.life = MAZE_ENEMY_BULLET_LIFE
                self.maze_enemy_bullets.append(eb)

        # ── Bullet → enemy collision ─────────────────────────────────
        for b in list(self.maze_bullets):
            hits = arcade.check_for_collision_with_list(b, self.maze_enemies)
            if hits:
                b.remove_from_sprite_lists()
                enemy = hits[0]
                enemy.health -= 20
                self._burst(b.center_x, b.center_y, 8,
                            (255, 220, 100), 55, 180, 1.0, 2.2, .07, .18)
                if enemy.health <= 0:
                    self.score += 20
                    self.notif_text  = f"+20  ENEMY DOWN!"
                    self.notif_color = (120, 255, 160)
                    self.notif_timer = 0.8
                    self._burst(enemy.center_x, enemy.center_y, 22,
                                (255, 130, 70), 65, 240, 1.5, 3.2, .12, .32)
                    enemy.remove_from_sprite_lists()

        # ── Enemy splitting ─────────────────────────────────────────
        for enemy in list(self.maze_enemies):
            enemy.split_timer -= delta
            if enemy.split_timer <= 0:
                enemy.split_timer += MAZE_ENEMY_SPLIT_TIME
                self._split_maze_enemy(enemy, max_enemies)

        # ── Enemy bullet → player collision ─────────────────────────
        for b in list(self.maze_enemy_bullets):
            if arcade.check_for_collision(b, p):
                b.remove_from_sprite_lists()
                if p.shield_active:
                    self._burst(b.center_x, b.center_y, 7,
                                (90, 220, 255), 50, 160, 0.9, 2.0, .06, .14)
                else:
                    p.health -= MAZE_ENEMY_BULLET_DAMAGE
                    self.damage_flash = max(self.damage_flash, 0.75)
                    self._burst(b.center_x, b.center_y, 12,
                                (255, 75, 75), 60, 200, 1.0, 2.2, .08, .20)
                    if p.health <= 0:
                        self._maze_gameover()
                        return

        # ── Enemy spawn timer ────────────────────────────────────────
        self.maze_spawn_timer -= delta
        if (self.maze_spawn_timer <= 0
                and len(self.maze_enemies) < max_enemies):
            spawn_interval = max(2.0, MAZE_ENEMY_SPAWN_INTERVAL
                                 - self.maze_level * 0.4)
            self.maze_spawn_timer = spawn_interval
            self._spawn_maze_enemy()

        # ── Smooth camera follow (Among Us style) ───────
        total_w = maze.cols * cs
        total_h = maze.rows * cs
        target_cam_x = p.center_x - w / 2
        target_cam_y = p.center_y - h / 2
        # Clamp so camera never shows outside the maze boundary
        target_cam_x = max(ox, min(ox + total_w - w, target_cam_x))
        target_cam_y = max(oy, min(oy + total_h - h, target_cam_y))
        lerp = min(1.0, 9.0 * delta)
        self.maze_cam_x += (target_cam_x - self.maze_cam_x) * lerp
        self.maze_cam_y += (target_cam_y - self.maze_cam_y) * lerp

        # Push updated position to the arcade 3 camera (position = centre of viewport)
        if self.maze_camera is not None:
            self.maze_camera.position = (
                self.maze_cam_x + w / 2,
                self.maze_cam_y + h / 2,
            )

    def _spawn_maze_enemy(self) -> None:
        """Pick a random cell far from the player and place a MazeEnemy there."""
        maze   = self.maze_grid
        cs     = self.maze_cell_size
        ox, oy = self.maze_origin
        pc, pr = self._maze_player_cell()

        for _ in range(40):          # up to 40 attempts to find a valid cell
            col = random.randint(0, maze.cols - 1)
            row = random.randint(0, maze.rows - 1)
            # Must be far from player, not on the exit
            if (abs(col - pc) + abs(row - pr) >= 7
                    and not (col == self.maze_exit_col and row == self.maze_exit_row)):
                enemy = MazeEnemy(col, row, cs, ox, oy)
                self.maze_enemies.append(enemy)
                return

    def _split_maze_enemy(self, enemy: MazeEnemy, max_enemies: int) -> bool:
        """Duplicate a surviving maze enemy into a nearby open cell."""
        if len(self.maze_enemies) >= max_enemies or enemy.health <= 1:
            return False

        maze = self.maze_grid
        cs = self.maze_cell_size
        ox, oy = self.maze_origin
        occupied = {
            (other.maze_col, other.maze_row)
            for other in self.maze_enemies
            if other is not enemy
        }
        options = []
        for direction in (MazeGrid.N, MazeGrid.E, MazeGrid.S, MazeGrid.W):
            if not maze.is_open(enemy.maze_col, enemy.maze_row, direction):
                continue
            col = enemy.maze_col + MazeGrid.DX[direction]
            row = enemy.maze_row + MazeGrid.DY[direction]
            if ((col, row) == (self.maze_exit_col, self.maze_exit_row)
                    or (col, row) in occupied):
                continue
            options.append((col, row))

        if not options:
            return False

        col, row = random.choice(options)
        child = MazeEnemy(col, row, cs, ox, oy)
        split_health = max(1, enemy.health // 2)
        if enemy.health - split_health < 1:
            return False
        enemy.health -= split_health
        child.health = split_health
        enemy.split_timer = MAZE_ENEMY_SPLIT_TIME
        child.split_timer = MAZE_ENEMY_SPLIT_TIME
        self.maze_enemies.append(child)
        self.notif_text = "ENEMY SPLIT!"
        self.notif_color = (255, 170, 110)
        self.notif_timer = max(self.notif_timer, 0.45)
        self._burst(enemy.center_x, enemy.center_y, 10,
                    (255, 120, 90), 45, 140, 0.8, 1.8, .05, .14)
        return True

    def _maze_gameover(self):
        self.player.health = 0
        self.game_state = STATE_MAZE_OVER
        self.set_mouse_visible(True)

    def _draw_mode_select(self):
        """Full-screen mode selection lobby shown before the main menu."""
        w, h = self.width, self.height
        t    = self.bg_time
        tc   = THEMES["dark"]
        FU   = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
        FN   = ("Courier New", "Menlo", "Monaco", "monospace")

        # ── Animated background ─────────────────────────────────────────
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, tc["bg"])
        p = (math.sin(t * 0.55) + 1) * 0.5
        arcade.draw_circle_filled(w * 0.12, h * 0.85, 240 + 20 * p,       (38, 75, 185, 45))
        arcade.draw_circle_filled(w * 0.88, h * 0.18, 270 + 28 * (1 - p), (130, 40, 165, 38))
        arcade.draw_circle_filled(w * 0.50, h * 1.08, 290,                  (28, 150, 200, 22))
        off = (t * 14) % 28
        for yi in range(-30, h + 30, 28):
            arcade.draw_line(0, yi + off, w, yi + off - 18, (28, 44, 76, 24), 1)
        for s in self.stars:
            tw2 = 0.55 + 0.45 * math.sin(t * s["twinkle"] + s["phase"])
            al  = max(20, min(255, int(s["alpha"] * tw2)))
            arcade.draw_circle_filled(s["x"], s["y"], s["size"], (200, 222, 255, al))

        # ── Title ───────────────────────────────────────────────────────
        title_pulse = 0.5 + 0.5 * math.sin(t * 2.2)
        title_color = (int(90 + 30 * title_pulse), int(195 + 30 * title_pulse), 255, 255)
        arcade.draw_text("SPACE SHOOTER", w // 2 + 3, h - 62,
                         (0, 0, 0, 90), 36, anchor_x="center", bold=True, font_name=FU)
        arcade.draw_text("SPACE SHOOTER", w // 2, h - 60,
                         title_color, 36, anchor_x="center", bold=True, font_name=FU)
        arcade.draw_text("NEON DRIFT", w // 2 + 2, h - 100,
                         (0, 0, 0, 75), 20, anchor_x="center", bold=True, font_name=FU)
        arcade.draw_text("NEON DRIFT", w // 2, h - 98,
                         (90, 198, 255, 210), 20, anchor_x="center", bold=True, font_name=FU)

        arcade.draw_text("SELECT YOUR GAME MODE", w // 2, h - 134,
                         (120, 155, 215, 190), 13, anchor_x="center", font_name=FU)
        arcade.draw_line(w // 2 - 160, h - 148, w // 2 + 160, h - 148,
                         (70, 112, 205, 90), 1)

        # ── Three mode cards ────────────────────────────────────────────
        modes = [
            {
                "key":     "normal",
                "label":   "NORMAL",
                "icon":    "◈",
                "desc":    "Classic space combat",
                "detail":  "10 levels · Shop · Boss fights",
                "color":   (90, 198, 255),
                "available": True,
            },
            {
                "key":     "maze",
                "label":   "MAZE MODE",
                "icon":    "⬡",
                "desc":    "Navigate & survive",
                "detail":  "Procedural maze arenas",
                "color":   (120, 255, 160),
                "available": True,
            },
            {
                "key":     "multiplayer",
                "label":   "MULTIPLAYER",
                "icon":    "⚔",
                "desc":    "Battle with others",
                "detail":  "Co-op & PvP online",
                "color":   (255, 140, 80),
                "available": False,
            },
        ]

        n_cards = len(modes)
        card_w  = min(210, int((w - 80) / n_cards - 20))
        card_h  = min(260, int(h * 0.48))
        total_w = n_cards * card_w + (n_cards - 1) * 24
        start_x = (w - total_w) // 2
        card_y  = h // 2 - card_h // 2 - 20

        self._mode_btns = {}

        for i, mode in enumerate(modes):
            cl = start_x + i * (card_w + 24)
            cr = cl + card_w
            cb = card_y
            ct = card_y + card_h
            cx_ = cl + card_w // 2

            avail  = mode["available"]
            mc     = mode["color"]
            hov    = avail and self._is_hovering(cl, cr, cb, ct)
            sel    = (self.selected_mode == mode["key"])

            # Shadow
            arcade.draw_lrbt_rectangle_filled(cl + 6, cr + 6, cb - 6, ct - 6, (0, 0, 0, 70))

            # Card body
            if not avail:
                fill   = (12, 16, 40, 210)
                border = (38, 46, 80, 130)
            elif hov:
                fill   = (14, 32, 80, 220)
                border = (*mc, 255)
            elif sel:
                fill   = (11, 22, 58, 228)
                border = (*mc[:3], 180)
            else:
                fill   = (9, 18, 50, 220)
                border = (*mc[:3], 110)

            arcade.draw_lrbt_rectangle_filled(cl, cr, cb, ct, fill)
            arcade.draw_lrbt_rectangle_outline(cl, cr, cb, ct, border, 2 if (sel or hov) else 1)

            # Only hovered cards get the outer glow; selected cards stay calm
            if hov:
                pulse2 = 0.5 + 0.5 * math.sin(t * 4.5)
                glow_a = int(30 + 35 * pulse2)
                arcade.draw_lrbt_rectangle_outline(cl - 3, cr + 3, cb - 3, ct + 3,
                                                    (*mc, glow_a), 3)

            # Corner accents
            sz = 12
            ac2 = border
            for (px2, py2, sx2, sy2) in [(cl, ct, 1, -1), (cr, ct, -1, -1),
                                          (cl, cb, 1,  1), (cr, cb, -1,  1)]:
                arcade.draw_line(px2, py2, px2 + sx2 * sz, py2, ac2, 2)
                arcade.draw_line(px2, py2, px2, py2 + sy2 * sz, ac2, 2)

            # Icon
            icon_c = mc if avail else (55, 65, 100, 180)
            icon_a = int(200 + 55 * math.sin(t * 3.0 + i)) if avail else 100
            arcade.draw_text(mode["icon"], cx_, ct - 62,
                             (*icon_c[:3], icon_a), 34,
                             anchor_x="center", anchor_y="center", font_name=FU)

            # Divider
            div_c = (*mc[:3], 80) if avail else (38, 46, 80, 60)
            arcade.draw_line(cl + 18, ct - 90, cr - 18, ct - 90, div_c, 1)

            # Mode label
            lbl_c = (*mc, 255) if avail else (55, 65, 105, 180)
            arcade.draw_text(mode["label"], cx_ + 1, ct - 118,
                             (0, 0, 0, 80), 15, anchor_x="center", bold=True, font_name=FU)
            arcade.draw_text(mode["label"], cx_, ct - 116,
                             lbl_c, 15, anchor_x="center", bold=True, font_name=FU)

            # Short description
            desc_c = (180, 205, 245, 210) if avail else (60, 72, 110, 160)
            arcade.draw_text(mode["desc"], cx_, ct - 148,
                             desc_c, 11, anchor_x="center", font_name=FU)

            # Detail line
            det_c = (110, 140, 195, 160) if avail else (45, 55, 85, 120)
            arcade.draw_text(mode["detail"], cx_, ct - 168,
                             det_c, 9, anchor_x="center", font_name=FN)

            # COMING SOON badge
            if not avail:
                bw2 = card_w - 28;  bh2 = 24
                bx2 = cl + 14;      by2 = cb + 18
                arcade.draw_lrbt_rectangle_filled(bx2, bx2 + bw2, by2, by2 + bh2,
                                                   (22, 28, 62, 220))
                arcade.draw_lrbt_rectangle_outline(bx2, bx2 + bw2, by2, by2 + bh2,
                                                    (60, 75, 130, 180), 1)
                arcade.draw_text("COMING SOON", bx2 + bw2 // 2, by2 + bh2 // 2,
                                 (100, 120, 185, 200), 9, anchor_x="center",
                                 anchor_y="center", bold=True, font_name=FU)
            else:
                # SELECT button at bottom of card
                btn_bw = card_w - 28;  btn_bh = 28
                btn_bx = cl + 14;      btn_by = cb + 14
                btn_hov = self._is_hovering(btn_bx, btn_bx + btn_bw, btn_by, btn_by + btn_bh)
                btn_fill   = (*mc, 220) if (sel or btn_hov) else (*mc[:3], 50)
                btn_border = (*mc, 255)
                btn_tc     = (10, 10, 20, 255) if (sel or btn_hov) else (*mc, 210)
                arcade.draw_lrbt_rectangle_filled(btn_bx, btn_bx + btn_bw,
                                                   btn_by, btn_by + btn_bh, btn_fill)
                arcade.draw_lrbt_rectangle_outline(btn_bx, btn_bx + btn_bw,
                                                    btn_by, btn_by + btn_bh, btn_border, 1)
                btn_label = "▶  SELECTED" if sel else "SELECT"
                arcade.draw_text(btn_label, btn_bx + btn_bw // 2, btn_by + btn_bh // 2,
                                 btn_tc, 10, anchor_x="center", anchor_y="center",
                                 bold=True, font_name=FU)
                self._mode_btns[mode["key"]] = (cl, cr, cb, ct)

        # ── ENTER button ────────────────────────────────────────────────
        if self.selected_mode:
            enter_w = 240;  enter_h = 48
            enter_x = w // 2 - enter_w // 2
            enter_y = card_y - enter_h - 24
            enter_hov = self._is_hovering(enter_x, enter_x + enter_w, enter_y, enter_y + enter_h)
            ep = 0.5 + 0.5 * math.sin(t * 3.5)
            e_fill   = (int(28 + 24 * ep), int(88 + 30 * ep), int(215 + 20 * ep), 245)
            e_border = (90, 198, 255, 255) if enter_hov else (70, 162, 255, 220)
            e_tc     = (255, 255, 255, 255)
            if enter_hov:
                arcade.draw_lrbt_rectangle_filled(enter_x - 2, enter_x + enter_w + 2,
                                                   enter_y - 2, enter_y + enter_h + 2,
                                                   (90, 198, 255, 28))
            arcade.draw_lrbt_rectangle_filled(enter_x, enter_x + enter_w,
                                               enter_y, enter_y + enter_h, e_fill)
            arcade.draw_lrbt_rectangle_outline(enter_x, enter_x + enter_w,
                                                enter_y, enter_y + enter_h, e_border, 2)
            arcade.draw_text("[ ENTER GAME ]", w // 2 + 1, enter_y + enter_h // 2 - 1,
                             (0, 0, 0, 90), 18, anchor_x="center", anchor_y="center",
                             bold=True, font_name=FU)
            arcade.draw_text("[ ENTER GAME ]", w // 2, enter_y + enter_h // 2,
                             e_tc, 18, anchor_x="center", anchor_y="center",
                             bold=True, font_name=FU)
            self._mode_btns["__enter__"] = (enter_x, enter_x + enter_w, enter_y, enter_y + enter_h)

        # ── Footer hint ─────────────────────────────────────────────────
        arcade.draw_text("Click a mode card, then press ENTER GAME  ·  F11 Fullscreen",
                         w // 2, 16, (80, 108, 165, 140), 9,
                         anchor_x="center", font_name=FN)

    # ══════════════════════════════════════════════════
    #  MAZE SELECT SCREEN
    # ══════════════════════════════════════════════════

    def _draw_maze_select(self):
        """Full-screen maze preset picker shown after choosing MAZE MODE."""
        w, h = self.width, self.height
        t    = self.bg_time
        tc   = THEMES["dark"]
        FU   = ("Futura", "Century Gothic", "Trebuchet MS", "Arial")
        FN   = ("Courier New", "Menlo", "Monaco", "monospace")

        def wrap_words(text: str, max_chars: int) -> list[str]:
            words = text.split()
            lines: list[str] = []
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if current and len(candidate) > max_chars:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                lines.append(current)
            return lines

        # Animated background
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, tc["bg"])
        p2 = (math.sin(t * 0.55) + 1) * 0.5
        arcade.draw_circle_filled(w * 0.10, h * 0.82, 220 + 18 * p2,       (28, 148, 90,  42))
        arcade.draw_circle_filled(w * 0.90, h * 0.22, 250 + 24 * (1 - p2), (40,  90, 175, 38))
        off = (t * 14) % 28
        for yi in range(-30, h + 30, 28):
            arcade.draw_line(0, yi + off, w, yi + off - 18, (20, 50, 34, 22), 1)
        for s in self.stars:
            tw2 = 0.55 + 0.45 * math.sin(t * s["twinkle"] + s["phase"])
            al  = max(20, min(255, int(s["alpha"] * tw2)))
            arcade.draw_circle_filled(s["x"], s["y"], s["size"], (180, 255, 210, al))

        # Title
        arcade.draw_text("MAZE MODE", w // 2 + 2, h - 56,
                         (0, 0, 0, 80), 32, anchor_x="center", bold=True, font_name=FU)
        arcade.draw_text("MAZE MODE", w // 2, h - 54,
                         (120, 255, 160, 255), 32, anchor_x="center", bold=True, font_name=FU)
        arcade.draw_text("SELECT MAZE TYPE", w // 2, h - 92,
                         (100, 200, 130, 190), 13, anchor_x="center", font_name=FU)
        arcade.draw_line(w // 2 - 180, h - 106, w // 2 + 180, h - 106,
                         (60, 180, 100, 80), 1)

        # Preset cards
        n_cards = len(MAZE_PRESETS)
        card_w  = min(250, int((w - 120) / n_cards - 18))
        card_h  = min(260, int(h * 0.46))
        total_w = n_cards * card_w + (n_cards - 1) * 18
        start_x = (w - total_w) // 2
        card_y  = h // 2 - card_h // 2 - 10

        self._maze_preset_btns = {}

        for i, preset in enumerate(MAZE_PRESETS):
            cl  = start_x + i * (card_w + 18)
            cr  = cl + card_w
            cb  = card_y
            ct  = card_y + card_h
            cx_ = cl + card_w // 2
            mc  = preset["color"]
            sel = (self.selected_maze_preset == preset["key"])
            hov = self._is_hovering(cl, cr, cb, ct)

            arcade.draw_lrbt_rectangle_filled(cl + 5, cr + 5, cb - 5, ct - 5, (0, 0, 0, 60))
            if sel:
                fill   = (10, 24, 18, 235); border = (*mc[:3], 195); bthk = 2
            elif hov:
                fill   = (14, 32, 22, 220); border = (*mc, 230); bthk = 2
            else:
                fill   = (9, 18, 14, 220); border = (*mc[:3], 100); bthk = 1
            arcade.draw_lrbt_rectangle_filled(cl, cr, cb, ct, fill)
            arcade.draw_lrbt_rectangle_outline(cl, cr, cb, ct, border, bthk)
            if hov:
                pulse2 = 0.5 + 0.5 * math.sin(t * 4.5)
                arcade.draw_lrbt_rectangle_outline(
                    cl - 3, cr + 3, cb - 3, ct + 3, (*mc, int(28 + 30 * pulse2)), 3)

            # Corner accents
            sz = 10
            for (px2, py2, sx2, sy2) in [(cl, ct, 1, -1), (cr, ct, -1, -1),
                                          (cl, cb, 1,  1), (cr, cb, -1,  1)]:
                arcade.draw_line(px2, py2, px2 + sx2 * sz, py2, border, 2)
                arcade.draw_line(px2, py2, px2, py2 + sy2 * sz, border, 2)

            # Icon
            icon_a = int(200 + 55 * math.sin(t * 3.0 + i)) if not sel else 255
            arcade.draw_text(preset["icon"], cx_, ct - 54,
                             (*mc[:3], icon_a), 30,
                             anchor_x="center", anchor_y="center", font_name=FU)

            arcade.draw_line(cl + 14, ct - 80, cr - 14, ct - 80,
                             (*mc[:3], 75 if not sel else 130), 1)

            # Name
            lbl_c = (225, 255, 235, 255) if sel else (*mc, 255)
            self._txt_shadow(preset["name"], cx_, ct - 106,
                             lbl_c, 13, FU, anchor_x="center", bold=True)

            # Desc + detail
            wrap_limit = 22 if card_w < 190 else 28
            desc_lines = wrap_words(preset["desc"], wrap_limit)
            detail_lines = wrap_words(preset["detail"], wrap_limit + 2)
            desc_c = (215, 245, 225, 235) if sel else (190, 225, 205, 220)
            det_c = (130, 195, 155, 215) if sel else (105, 165, 130, 190)

            line_y = ct - 138
            for line in desc_lines[:2]:
                self._txt_shadow(line, cx_, line_y, desc_c, 8 if card_w < 200 else 9,
                                 FU, anchor_x="center", bold=True, ox=1, oy=-1)
                line_y -= 16

            line_y -= 6
            for line in detail_lines[:2]:
                self._txt_shadow(line, cx_, line_y, det_c, 7 if card_w < 200 else 8,
                                 FN, anchor_x="center", ox=1, oy=-1)
                line_y -= 14

            # SELECT button at bottom of card
            btn_bw = card_w - 24;  btn_bh = 26
            btn_bx = cl + 12;      btn_by = cb + 12
            btn_hov = self._is_hovering(btn_bx, btn_bx + btn_bw, btn_by, btn_by + btn_bh)
            btn_fill   = (*mc, 220) if (sel or btn_hov) else (*mc[:3], 45)
            btn_tc     = (10, 10, 20, 255) if (sel or btn_hov) else (*mc, 200)
            arcade.draw_lrbt_rectangle_filled(btn_bx, btn_bx + btn_bw,
                                               btn_by, btn_by + btn_bh, btn_fill)
            arcade.draw_lrbt_rectangle_outline(btn_bx, btn_bx + btn_bw,
                                                btn_by, btn_by + btn_bh, (*mc, 255), 1)
            arcade.draw_text("▶  SELECTED" if sel else "SELECT",
                             btn_bx + btn_bw // 2, btn_by + btn_bh // 2,
                             btn_tc, 9, anchor_x="center", anchor_y="center",
                             bold=True, font_name=FU)

            self._maze_preset_btns[preset["key"]] = (cl, cr, cb, ct)

        # ENTER MAZE button
        play_w = 240;  play_h = 48
        play_x = w // 2 - play_w // 2
        play_y = card_y - play_h - 22
        play_hov = self._is_hovering(play_x, play_x + play_w, play_y, play_y + play_h)
        ep = 0.5 + 0.5 * math.sin(t * 3.5)
        e_fill   = (int(20 + 20 * ep), int(160 + 40 * ep), int(90 + 30 * ep), 245)
        e_border = (120, 255, 160, 255) if play_hov else (80, 210, 120, 220)
        if play_hov:
            arcade.draw_lrbt_rectangle_filled(play_x - 2, play_x + play_w + 2,
                                               play_y - 2, play_y + play_h + 2,
                                               (120, 255, 160, 26))
        arcade.draw_lrbt_rectangle_filled(play_x, play_x + play_w,
                                           play_y, play_y + play_h, e_fill)
        arcade.draw_lrbt_rectangle_outline(play_x, play_x + play_w,
                                            play_y, play_y + play_h, e_border, 2)
        arcade.draw_text("[ ENTER MAZE ]", w // 2 + 1, play_y + play_h // 2 - 1,
                         (0, 0, 0, 85), 18, anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)
        arcade.draw_text("[ ENTER MAZE ]", w // 2, play_y + play_h // 2,
                         (255, 255, 255, 255), 18, anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)
        self._maze_preset_btns["__play__"] = (play_x, play_x + play_w, play_y, play_y + play_h)

        # Back button
        back_w = 130;  back_h = 36
        back_x = w // 2 - back_w // 2
        back_y = play_y - back_h - 12
        back_hov = self._is_hovering(back_x, back_x + back_w, back_y, back_y + back_h)
        arcade.draw_lrbt_rectangle_filled(back_x, back_x + back_w, back_y, back_y + back_h,
                                           tc["btn_hover"] if back_hov else (*tc["btn_fill"][:3], 180))
        arcade.draw_lrbt_rectangle_outline(back_x, back_x + back_w, back_y, back_y + back_h,
                                            tc["btn_border"], 1)
        arcade.draw_text("[ BACK ]", w // 2, back_y + back_h // 2,
                         (255, 255, 255, 220), 13, anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)
        self._maze_preset_btns["__back__"] = (back_x, back_x + back_w, back_y, back_y + back_h)

        arcade.draw_text("Select a maze type, then press ENTER MAZE  ·  ESC to go back",
                         w // 2, 16, (70, 130, 95, 140), 9,
                         anchor_x="center", font_name=FN)

    def _start_maze_with_preset(self):
        """Reset all maze run state and start a fresh maze with the chosen preset."""
        self.maze_preset = next(
            (p for p in MAZE_PRESETS if p["key"] == self.selected_maze_preset),
            MAZE_PRESETS[0]
        )
        self.maze_level = 0
        self.score      = 0
        self.time_alive = 0.0
        self.run_coins  = 0
        self.setup_maze(keep_player=False)
