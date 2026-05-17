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

        maze_seed = random.randint(0, 999999)
        self.maze_grid      = MazeGrid(cols, rows, seed=maze_seed)
        self.maze_grid.open_start_area()
        protected_cells = {
            (0, rows - 1), (1, rows - 1), (0, rows - 2),
            (cols - 1, 0), (cols - 2, 0), (cols - 1, 1),
        }
        self.maze_grid.configure_breakable_walls(
            seed=maze_seed + 97,
            protected_cells={
                (c, r) for c, r in protected_cells
                if 0 <= c < cols and 0 <= r < rows
            },
        )
        self.maze_cell_size = cs
        self.maze_origin    = (float(ox), float(oy))
        self.maze_exit_col  = cols - 1
        self.maze_exit_row  = 0           # bottom-right cell
        self.maze_start_to_exit_steps = 1
        self.maze_progress_best = 0.0
        self.maze_map_open = False
        self.maze_enemies_created = 0
        self.maze_keys_collected = 0
        self.maze_key_relocate_timer = MAZE_KEY_RELOCATE_TIME
        self.maze_corner_wave_timer = MAZE_CORNER_WAVE_INTERVAL
        self.maze_potion_spawn_timer = MAZE_POTION_SPAWN_INTERVAL
        self.maze_exit_lock_notice_timer = 0.0

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
        self.player.angle    = 90.0   # art points up by default; rotate nose to face RIGHT
        self.maze_start_to_exit_steps = max(
            1,
            len(self.maze_grid.bfs(0, rows - 1, self.maze_exit_col, self.maze_exit_row)),
        )

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
        self.maze_spawn_timer   = 1.2                   # first enemy arrives quickly

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
        self._place_maze_keys()
        self._spawn_maze_potion("maze_health")
        self._spawn_maze_potion("maze_speed")

        self._pause_return_state = None
        self.game_state = STATE_MAZE
        self.set_mouse_visible(False)

    def _maze_player_angle_from_motion(self, vx: float, vy: float) -> float:
        """Return sprite angle with the plane nose leading its movement."""
        raw = math.degrees(math.atan2(vx, vy))
        return (raw + 180.0) % 360.0 - 180.0

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

    def _maze_wall_at_point(self, x: float, y: float, radius: float) -> tuple[int, int, int] | None:
        """Return the closed wall touched by a circular object, if any."""
        maze = self.maze_grid
        cs   = self.maze_cell_size
        ox, oy = self.maze_origin
        wt2  = MAZE_WALL_THICK // 2 + 2

        if x - radius < ox or x + radius > ox + maze.cols * cs:
            return None
        if y - radius < oy or y + radius > oy + maze.rows * cs:
            return None

        col = max(0, min(maze.cols - 1, int((x - ox) / cs)))
        row = max(0, min(maze.rows - 1, int((y - oy) / cs)))

        cell_l = ox + col * cs;  cell_r = cell_l + cs
        cell_b = oy + row * cs;  cell_t = cell_b + cs

        checks = [
            (x + radius > cell_r - wt2, MazeGrid.E),
            (x - radius < cell_l + wt2, MazeGrid.W),
            (y + radius > cell_t - wt2, MazeGrid.N),
            (y - radius < cell_b + wt2, MazeGrid.S),
        ]
        for touched, direction in checks:
            if touched and not maze.is_open(col, row, direction):
                return (col, row, direction)
        return None

    @staticmethod
    def _draw_round_lrbt(left: float, right: float, bottom: float, top: float,
                         color: tuple, radius: float | None = None) -> None:
        """Draw a rounded rectangle using primitives available in Arcade."""
        if right <= left or top <= bottom:
            return
        width = right - left
        height = top - bottom
        r = min(radius if radius is not None else min(width, height) * 0.28,
                width / 2, height / 2)
        if r <= 0:
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)
            return

        arcade.draw_lrbt_rectangle_filled(left + r, right - r, bottom, top, color)
        arcade.draw_lrbt_rectangle_filled(left, right, bottom + r, top - r, color)
        arcade.draw_circle_filled(left + r, bottom + r, r, color)
        arcade.draw_circle_filled(right - r, bottom + r, r, color)
        arcade.draw_circle_filled(left + r, top - r, r, color)
        arcade.draw_circle_filled(right - r, top - r, r, color)

    def _draw_maze_wall_segment(self, left: float, right: float, bottom: float, top: float,
                                col: int, row: int, direction: int,
                                wall_color: tuple, glow_color: tuple) -> None:
        """Draw permanent walls and fragile breach walls with distinct material colors."""
        maze = self.maze_grid
        horizontal = (right - left) >= (top - bottom)
        length = (right - left) if horizontal else (top - bottom)
        thick = (top - bottom) if horizontal else (right - left)
        cx = (left + right) / 2
        cy = (bottom + top) / 2
        if maze.is_breakable_wall(col, row, direction):
            hp = maze.wall_hp(col, row, direction)
            ratio = max(0.0, min(1.0, hp / max(1, maze.breakable_wall_max_hp)))
            pulse = 0.65 + 0.35 * math.sin(self.bg_time * 4.0 + col * 0.7 + row * 0.4)
            theme_rgb = tuple(
                int(c) for c in (glow_color[:3] if len(glow_color) >= 3 else (255, 72, 20))
            )
            glow_strength = 0.62 + 0.22 * pulse + 0.16 * ratio
            basalt = (
                max(18, int(theme_rgb[0] * 0.18)),
                max(18, int(theme_rgb[1] * 0.18)),
                max(20, int(theme_rgb[2] * 0.18)),
                255,
            )
            ember = (
                min(255, int(theme_rgb[0] * glow_strength)),
                min(255, int(theme_rgb[1] * glow_strength)),
                min(255, int(theme_rgb[2] * glow_strength)),
                245,
            )
            ember_dim = (
                max(20, int(theme_rgb[0] * 0.52)),
                max(20, int(theme_rgb[1] * 0.52)),
                max(20, int(theme_rgb[2] * 0.52)),
                235,
            )
            themed_glow = (*theme_rgb, int(70 + 65 * pulse))
            corner_r = min(thick * 0.28, 18)
            self._draw_round_lrbt(left - 4, right + 4, bottom - 4, top + 4, themed_glow, corner_r + 4)
            self._draw_round_lrbt(left, right, bottom, top, basalt, corner_r)

            rim = max(5, int(thick * 0.18))
            vein = max(4, int(thick * 0.11))
            if horizontal:
                arcade.draw_lrbt_rectangle_filled(left + corner_r, right - corner_r,
                                                   top - rim, top, ember)
                arcade.draw_lrbt_rectangle_filled(left + corner_r, right - corner_r,
                                                   bottom, bottom + rim, ember_dim)
                wave_y = cy + math.sin(self.bg_time * 3.0 + col) * thick * 0.10
                arcade.draw_lrbt_rectangle_filled(left + 14, right - 14,
                                                   wave_y - vein / 2, wave_y + vein / 2, ember)
                crack = (22, 9, 7, 210)
                arcade.draw_line(cx - 23, cy + 7, cx - 7, cy - 5, crack, 4)
                arcade.draw_line(cx - 7, cy - 5, cx + 11, cy + 8, crack, 4)
                arcade.draw_line(cx + 11, cy + 8, cx + 25, cy - 4, crack, 4)
            else:
                arcade.draw_lrbt_rectangle_filled(left, left + rim,
                                                   bottom + corner_r, top - corner_r,
                                                   ember_dim)
                arcade.draw_lrbt_rectangle_filled(right - rim, right,
                                                   bottom + corner_r, top - corner_r, ember)
                wave_x = cx + math.sin(self.bg_time * 3.0 + row) * thick * 0.10
                arcade.draw_lrbt_rectangle_filled(wave_x - vein / 2, wave_x + vein / 2,
                                                   bottom + 14, top - 14, ember)
                crack = (22, 9, 7, 210)
                arcade.draw_line(cx - 8, cy + 27, cx + 6, cy + 9, crack, 4)
                arcade.draw_line(cx + 6, cy + 9, cx - 7, cy - 8, crack, 4)
                arcade.draw_line(cx - 7, cy - 8, cx + 7, cy - 26, crack, 4)
            return

        shadow = (2, 4, 8, 170)
        edge_dark = (16, 18, 25, 255)
        facet = (48, 53, 66, 245)
        highlight = (78, 86, 104, 180)
        mark = (142, 149, 160, 145)

        corner_r = min(thick * 0.30, 20)
        self._draw_round_lrbt(left + 6, right + 6, bottom - 6, top - 6, shadow, corner_r)
        self._draw_round_lrbt(left, right, bottom, top, wall_color, corner_r)
        bevel = max(7, int(thick * 0.18))
        inset = max(10, int(thick * 0.28))

        if horizontal:
            arcade.draw_lrbt_rectangle_filled(left + corner_r, right - corner_r,
                                               top - bevel, top, highlight)
            arcade.draw_lrbt_rectangle_filled(left + corner_r, right - corner_r,
                                               bottom, bottom + bevel, edge_dark)
            arcade.draw_lrbt_rectangle_filled(left + inset, right - inset,
                                               cy - thick * 0.18, cy + thick * 0.18, facet)
            if length >= 74:
                arcade.draw_circle_filled(cx, cy + 1, thick * 0.08, mark)
                arcade.draw_circle_filled(cx - thick * 0.03, cy + thick * 0.02,
                                          thick * 0.018, edge_dark)
                arcade.draw_circle_filled(cx + thick * 0.03, cy + thick * 0.02,
                                          thick * 0.018, edge_dark)
        else:
            arcade.draw_lrbt_rectangle_filled(left, left + bevel,
                                               bottom + corner_r, top - corner_r, edge_dark)
            arcade.draw_lrbt_rectangle_filled(right - bevel, right,
                                               bottom + corner_r, top - corner_r, highlight)
            arcade.draw_lrbt_rectangle_filled(cx - thick * 0.18, cx + thick * 0.18,
                                               bottom + inset, top - inset, facet)
            if length >= 74:
                arcade.draw_circle_filled(cx - 1, cy, thick * 0.08, mark)
                arcade.draw_circle_filled(cx - thick * 0.02, cy + thick * 0.03,
                                          thick * 0.018, edge_dark)
                arcade.draw_circle_filled(cx - thick * 0.02, cy - thick * 0.03,
                                          thick * 0.018, edge_dark)

    def _maze_player_cell(self) -> tuple[int, int]:
        ox, oy = self.maze_origin
        cs = self.maze_cell_size
        col = max(0, min(self.maze_grid.cols - 1, int((self.player.center_x - ox) / cs)))
        row = max(0, min(self.maze_grid.rows - 1, int((self.player.center_y - oy) / cs)))
        return col, row

    def _maze_completion_ratio(self) -> float:
        pc, pr = self._maze_player_cell()
        if (pc, pr) == (self.maze_exit_col, self.maze_exit_row):
            return 1.0
        remaining = len(self.maze_grid.bfs(pc, pr, self.maze_exit_col, self.maze_exit_row))
        total = max(1, getattr(self, "maze_start_to_exit_steps", 1))
        return max(0.0, min(1.0, 1.0 - remaining / total))

    def _maze_key_world(self, col: int, row: int) -> tuple[float, float]:
        cs = self.maze_cell_size
        ox, oy = self.maze_origin
        return ox + (col + 0.5) * cs, oy + (row + 0.5) * cs

    def _maze_key_reserved_cells(self) -> set[tuple[int, int]]:
        maze = self.maze_grid
        reserved = {
            (0, maze.rows - 1),
            (self.maze_exit_col, self.maze_exit_row),
        }
        if self.player is not None:
            reserved.add(self._maze_player_cell())
        for key in getattr(self, "maze_keys", []):
            if not key.get("collected", False):
                reserved.add((key["col"], key["row"]))
        for enemy in getattr(self, "maze_enemies", []):
            reserved.add((enemy.maze_col, enemy.maze_row))
        return reserved

    def _random_maze_key_cell(self, reserved: set[tuple[int, int]]) -> tuple[int, int]:
        maze = self.maze_grid
        start = (0, maze.rows - 1)
        exit_cell = (self.maze_exit_col, self.maze_exit_row)
        for _ in range(500):
            col = random.randint(0, maze.cols - 1)
            row = random.randint(0, maze.rows - 1)
            if (col, row) in reserved:
                continue
            if abs(col - start[0]) + abs(row - start[1]) < 5:
                continue
            if abs(col - exit_cell[0]) + abs(row - exit_cell[1]) < 4:
                continue
            return col, row

        for row in range(maze.rows):
            for col in range(maze.cols):
                if (col, row) not in reserved:
                    return col, row
        return start

    def _place_maze_keys(self) -> None:
        """Place the three glowing exit keys for this floor."""
        self.maze_keys = []
        reserved = self._maze_key_reserved_cells()
        for idx in range(MAZE_KEYS_REQUIRED):
            col, row = self._random_maze_key_cell(reserved)
            reserved.add((col, row))
            self.maze_keys.append({
                "id": idx,
                "col": col,
                "row": row,
                "collected": False,
                "phase": random.uniform(0.0, math.tau),
            })

    def _relocate_maze_keys(self) -> None:
        """Move any uncollected keys to fresh cells."""
        reserved = self._maze_key_reserved_cells()
        for key in getattr(self, "maze_keys", []):
            if key.get("collected", False):
                continue
            reserved.discard((key["col"], key["row"]))
            col, row = self._random_maze_key_cell(reserved)
            key["col"] = col
            key["row"] = row
            key["phase"] = random.uniform(0.0, math.tau)
            reserved.add((col, row))

        self.maze_key_relocate_timer = MAZE_KEY_RELOCATE_TIME
        self.notif_text = "KEYS SHIFTED!"
        self.notif_color = (255, 220, 90)
        self.notif_timer = 1.2

    def _collect_maze_key_at_player(self) -> None:
        pc, pr = self._maze_player_cell()
        for key in getattr(self, "maze_keys", []):
            if key.get("collected", False):
                continue
            if (key["col"], key["row"]) != (pc, pr):
                continue
            key["collected"] = True
            self.maze_keys_collected = min(MAZE_KEYS_REQUIRED, self.maze_keys_collected + 1)
            kx, ky = self._maze_key_world(pc, pr)
            self.notif_text = f"KEY {self.maze_keys_collected}/{MAZE_KEYS_REQUIRED} ACQUIRED"
            self.notif_color = (255, 230, 95)
            self.notif_timer = 1.4
            self._burst(kx, ky, 34, (255, 220, 90), 70, 260, 1.7, 3.5, .10, .28)
            break

    def _maze_pickup_reserved_cells(self) -> set[tuple[int, int]]:
        reserved = self._maze_key_reserved_cells()
        for pu in getattr(self, "powerups", []):
            col = max(0, min(self.maze_grid.cols - 1,
                             int((pu.center_x - self.maze_origin[0]) / self.maze_cell_size)))
            row = max(0, min(self.maze_grid.rows - 1,
                             int((pu.center_y - self.maze_origin[1]) / self.maze_cell_size)))
            reserved.add((col, row))
        return reserved

    def _maze_random_pickup_cell(self) -> tuple[int, int]:
        reserved = self._maze_pickup_reserved_cells()
        return self._random_maze_key_cell(reserved)

    def _maze_potion_count(self) -> int:
        return sum(
            1 for pu in getattr(self, "powerups", [])
            if getattr(pu, "kind", "") in ("maze_health", "maze_speed")
        )

    def _spawn_maze_potion(self, kind: str | None = None) -> bool:
        if self._maze_potion_count() >= MAZE_MAX_POTIONS:
            return False
        if kind is None:
            need_health = self.player.health < self.player.max_health * 0.70
            kind = "maze_health" if need_health or random.random() < 0.55 else "maze_speed"

        col, row = self._maze_random_pickup_cell()
        x, y = self._maze_key_world(col, row)
        pu = Powerup(x, y, kind)
        pu.change_y = 0
        pu.life = 42.0
        pu.scale = 1.25
        self.powerups.append(pu)
        glow = (30, 255, 105) if kind == "maze_health" else (255, 215, 35)
        self._burst(x, y, 18, glow, 36, 140, 0.8, 2.2, .06, .18)
        return True

    def _collect_maze_potion(self, pu: Powerup) -> bool:
        p = self.player
        if pu.kind == "maze_health":
            healed = min(45, p.max_health - p.health)
            p.health = min(p.max_health, p.health + 45)
            self.notif_text = (
                f"+{int(healed)} HEALTH POTION!" if healed > 0 else "HEALTH ALREADY FULL!"
            )
            self.notif_color = (95, 255, 135)
            self.notif_timer = 1.3
            self._burst(pu.center_x, pu.center_y, 26,
                        (35, 255, 120), 70, 240, 1.4, 3.0, .08, .24)
            return True

        if pu.kind == "maze_speed":
            p.speed_active = True
            p.speed_timer = max(getattr(p, "speed_timer", 0.0), POWERUP_DURATION + 2.0)
            self.notif_text = "BLITZ SPEED!"
            self.notif_color = (255, 225, 80)
            self.notif_timer = 1.4
            self._burst(pu.center_x, pu.center_y, 30,
                        (255, 220, 45), 85, 285, 1.5, 3.4, .08, .24)
            return True

        return False

    def _maze_enemy_spawn_interval(self) -> float:
        progress = max(getattr(self, "maze_progress_best", 0.0), self._maze_completion_ratio())
        pressure = max(0.0, min(1.0, progress)) ** 0.85
        slow = MAZE_ENEMY_SPAWN_INTERVAL
        fast = MAZE_ENEMY_SPAWN_MIN_INTERVAL
        return slow + (fast - slow) * pressure

    def _maze_minimap_layout(self) -> tuple[int, int, int, int, int, int]:
        maze = self.maze_grid
        mm_cs = max(4, min(9, 90 // max(maze.cols, maze.rows)))
        mx = 16
        my = self.height - 185 - maze.rows * mm_cs
        mw = maze.cols * mm_cs
        mh = maze.rows * mm_cs
        return mx, my, mw, mh, mm_cs, 8

    def _maze_minimap_hit(self, x: float, y: float) -> bool:
        mx, my, mw, mh, _mm_cs, pad = self._maze_minimap_layout()
        return mx - pad <= x <= mx + mw + pad and my - pad <= y <= my + mh + pad

    def _open_maze_map_overlay(self) -> None:
        self.maze_map_open = True
        self.mouse_held = False
        if hasattr(self, "_clear_movement_input"):
            self._clear_movement_input()
        self.set_mouse_visible(True)

    def _close_maze_map_overlay(self) -> None:
        self.maze_map_open = False
        self.mouse_held = False
        self.set_mouse_visible(False)

    def _draw_maze_key(self, col: int, row: int, phase: float) -> None:
        x, y = self._maze_key_world(col, row)
        t = self.bg_time + phase
        pulse = 0.5 + 0.5 * math.sin(t * 4.2)
        y += math.sin(t * 2.6) * 5

        glow = int(70 + 75 * pulse)
        arcade.draw_circle_filled(x, y, 42 + 8 * pulse, (255, 205, 65, glow))
        arcade.draw_circle_filled(x, y, 24 + 4 * pulse, (255, 240, 120, 80))
        arcade.draw_circle_outline(x, y, 34 + 5 * pulse, (255, 245, 170, 155), 2)

        head_r = 10
        arcade.draw_circle_filled(x - 9, y + 7, head_r + 5, (255, 174, 38, 255))
        arcade.draw_circle_filled(x - 9, y + 7, head_r - 1, (38, 24, 36, 245))
        arcade.draw_circle_outline(x - 9, y + 7, head_r + 5, (255, 248, 180, 255), 3)
        arcade.draw_lrbt_rectangle_filled(x + 1, x + 32, y + 1, y + 10, (255, 202, 58, 255))
        arcade.draw_lrbt_rectangle_filled(x + 18, x + 24, y - 9, y + 2, (255, 202, 58, 255))
        arcade.draw_lrbt_rectangle_filled(x + 28, x + 35, y - 12, y + 2, (255, 202, 58, 255))
        arcade.draw_lrbt_rectangle_filled(x + 1, x + 32, y + 7, y + 10, (255, 250, 165, 225))
        arcade.draw_circle_filled(x - 14, y + 12, 3, (255, 255, 210, 245))

    def _draw_maze_keys(self) -> None:
        for key in getattr(self, "maze_keys", []):
            if key.get("collected", False):
                continue
            self._draw_maze_key(key["col"], key["row"], key.get("phase", 0.0))

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

        mode_c = tuple((getattr(self, "maze_preset", None) or MAZE_PRESETS[0])["color"][:3])
        bg_c = (
            max(4, int(mode_c[0] * 0.10)),
            max(6, int(mode_c[1] * 0.10)),
            max(12, int(mode_c[2] * 0.12)),
        )
        floor_c = (
            max(8, int(mode_c[0] * 0.16)),
            max(10, int(mode_c[1] * 0.16)),
            max(18, int(mode_c[2] * 0.18)),
        )
        WALL_BASE_C = (31, 35, 45)
        FLOOR_C = floor_c
        EXIT_C  = (112, 255, 188)
        ENTRY_C = mode_c

        # ── Apply scrolling camera viewport ─────────
        # Activate the maze camera so all world-space drawing is offset correctly.
        cam_x = self.maze_cam_x
        cam_y = self.maze_cam_y
        if self.maze_camera is not None:
            self.maze_camera.use()

        # ── Background (fill the whole world) ───────
        arcade.draw_lrbt_rectangle_filled(
            ox, ox + maze.cols * cs, oy, oy + maze.rows * cs, bg_c)
        # Also fill outside-maze areas visible at edges
        arcade.draw_lrbt_rectangle_filled(
            cam_x - 10, cam_x + w + 10, cam_y - 10, cam_y + h + 10,
            tuple(max(0, c - 8) for c in bg_c))

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
        gc = (*mode_c, 30)
        for row in range(row_min, row_max + 2):
            yy = oy + row * cs
            arcade.draw_line(ox + col_min * cs, yy, ox + (col_max + 1) * cs, yy, gc, 1)
        for col in range(col_min, col_max + 2):
            xx = ox + col * cs
            arcade.draw_line(xx, oy + row_min * cs, xx, oy + (row_max + 1) * cs, gc, 1)

        # ── Walls ───────────────────────────────────
        p2 = 0.5 + 0.5 * math.sin(t * 1.8)
        wc = (
            int(WALL_BASE_C[0] + 12 * p2),
            int(WALL_BASE_C[1] + 12 * p2),
            int(WALL_BASE_C[2] + 12 * p2),
            255,
        )
        gw = (*mode_c, 85)

        # Outer border (always solid)
        bx = ox - wt2;  by = oy - wt2
        bw2 = maze.cols * cs + wt;  bh2 = maze.rows * cs + wt
        border_r = min(wt * 0.30, 20)
        self._draw_round_lrbt(bx, bx + bw2, by, by + wt, wc, border_r)
        self._draw_round_lrbt(bx, bx + bw2, by + bh2 - wt, by + bh2, wc, border_r)
        self._draw_round_lrbt(bx, bx + wt, by, by + bh2, wc, border_r)
        self._draw_round_lrbt(bx + bw2 - wt, bx + bw2, by, by + bh2, wc, border_r)
        arcade.draw_lrbt_rectangle_outline(bx, bx + bw2, by, by + bh2, (90, 96, 105, 220), 4)

        # Internal walls — only visible cells, only closed passages
        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                cl2 = ox + col * cs;  cr2 = cl2 + cs
                cb2 = oy + row * cs;  ct2 = cb2 + cs
                if row < maze.rows - 1 and not maze.is_open(col, row, MazeGrid.N):
                    self._draw_maze_wall_segment(
                        cl2, cr2, ct2 - wt2, ct2 + wt2,
                        col, row, MazeGrid.N, wc, gw)
                if col < maze.cols - 1 and not maze.is_open(col, row, MazeGrid.E):
                    self._draw_maze_wall_segment(
                        cr2 - wt2, cr2 + wt2, cb2, ct2,
                        col, row, MazeGrid.E, wc, gw)

        # ── Exit portal ─────────────────────────────
        ec2, er2 = self.maze_exit_col, self.maze_exit_row
        ex2 = ox + (ec2 + 0.5) * cs
        ey2 = oy + (er2 + 0.5) * cs
        pr  = min(34, cs * 0.20)
        ep  = 0.5 + 0.5 * math.sin(t * 4.8)
        exit_unlocked = self.maze_keys_collected >= MAZE_KEYS_REQUIRED
        exit_c = EXIT_C if exit_unlocked else (255, 165, 60)
        exit_label = "EXIT" if exit_unlocked else "LOCK"
        arcade.draw_circle_filled(ex2, ey2, pr + 6 * ep, (*exit_c[:3], 55))
        arcade.draw_circle_filled(ex2, ey2, pr,            (*exit_c[:3], 130))
        arcade.draw_circle_outline(ex2, ey2, pr,            exit_c, 3)
        arcade.draw_circle_outline(ex2, ey2, pr + 6 * ep, (*exit_c[:3], int(70 * ep)), 2)
        arcade.draw_text(exit_label, ex2, ey2,
                         (180, 255, 220, 220), 8, anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)

        # ── Entry glow ──────────────────────────────
        enx = ox + 0.5 * cs
        eny = oy + (maze.rows - 0.5) * cs
        arcade.draw_circle_filled(enx, eny, 14, (*ENTRY_C[:3], 45))

        # ── Exit keys ───────────────────────────────
        self._draw_maze_keys()

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

        # ── Breach cells ─────────────────────────────
        for pu in self.powerups:
            if pu.kind not in ("maze_health", "maze_speed"):
                continue
            color = (30, 255, 105) if pu.kind == "maze_health" else (255, 215, 35)
            pulse = 0.5 + 0.5 * math.sin(t * 5.5 + pu.wobble_phase)
            arcade.draw_circle_filled(
                pu.center_x, pu.center_y,
                28 + 7 * pulse,
                (*color, int(58 + 55 * pulse)),
            )
            arcade.draw_circle_outline(
                pu.center_x, pu.center_y,
                33 + 5 * pulse,
                (*color, int(150 + 55 * pulse)),
                2,
            )
        self.powerups.draw()

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

        # ── Health readout: classic stacked number + segmented bar ──
        hp_ratio = max(0.0, min(1.0, p.health / max(1, p.max_health)))
        hp_c = (70, 225, 105) if hp_ratio > 0.35 else (255, 70, 80)
        low_flash = hp_ratio <= 0.25 and math.sin(t * 11.0) > 0
        if low_flash:
            hp_c = (255, 235, 120)

        hx = 24
        hy = h - 14
        self._txt_shadow(str(int(max(0, p.health))), hx, hy,
                         (190, 255, 205, 245), 32, FU, anchor_y="top", bold=True,
                         ox=3, oy=-3)
        self._txt_shadow("HEALTH", hx + 2, hy - 34,
                         (120, 255, 160, 190), 11, FU, anchor_y="top", bold=True)

        hp_text_y = hy - 58
        self._txt_shadow(f"{int(max(0, p.health))}  /  {p.max_health}", hx, hp_text_y,
                         (*hp_c[:3], 235), 15, FN, anchor_y="top", bold=True)

        segs = 22
        gap = 3
        seg_w = 9
        seg_h = 12
        bar_x = hx
        bar_y = hp_text_y - 19
        filled = int(hp_ratio * segs + 0.5)
        for i in range(segs):
            lx = bar_x + i * (seg_w + gap)
            rx = lx + seg_w
            if i < filled:
                arcade.draw_lrbt_rectangle_filled(lx, rx, bar_y, bar_y + seg_h, (*hp_c[:3], 238))
                arcade.draw_lrbt_rectangle_filled(lx, rx, bar_y + seg_h - 4, bar_y + seg_h,
                                                   (155, 255, 175, 160))
            else:
                arcade.draw_lrbt_rectangle_filled(lx, rx, bar_y, bar_y + seg_h, (35, 20, 34, 52))

        glow_w = int((segs * seg_w + (segs - 1) * gap) * hp_ratio)
        if glow_w > 0:
            arcade.draw_lrbt_rectangle_filled(bar_x, bar_x + glow_w, bar_y - 3, bar_y - 1,
                                               (*hp_c[:3], 95))

        # ── Score ───────────────────────────────────
        self._txt_shadow(f"SCORE  {self.score:,}", w - 16, h - 28,
                         (210, 235, 255, 240), 18, FU, anchor_x="right", bold=True)

        # ── Maze floor badge ────────────────────────
        lbl = f"FLOOR  {self.maze_level + 1}/{MAZE_MAX_LEVELS}"
        self._txt_shadow(lbl, w // 2, h - 28, (100, 255, 160, 230),
                         14, FU, anchor_x="center", bold=True)

        # ── Maze completion line ─────────────────────
        progress = max(getattr(self, "maze_progress_best", 0.0), self._maze_completion_ratio())
        progress = max(0.0, min(1.0, progress))
        line_w = min(430, max(240, int(w * 0.34)))
        line_h = 6
        line_x = w // 2 - line_w // 2
        line_y = h - 57
        fill_w = int(line_w * progress)
        track_c = (35, 48, 70, 150)
        fill_c = (105, 255, 170, 230)
        glow_c = (105, 255, 170, 70)
        arcade.draw_lrbt_rectangle_filled(line_x, line_x + line_w, line_y, line_y + line_h, track_c)
        if fill_w > 0:
            arcade.draw_lrbt_rectangle_filled(line_x, line_x + fill_w, line_y, line_y + line_h, fill_c)
            arcade.draw_lrbt_rectangle_filled(line_x, line_x + fill_w, line_y - 3, line_y - 1, glow_c)
        arcade.draw_circle_filled(line_x, line_y + line_h / 2, 4, (90, 155, 220, 210))
        arcade.draw_circle_filled(line_x + line_w, line_y + line_h / 2, 5, (105, 255, 170, 230))
        self._txt_shadow(f"MAZE  {int(progress * 100):02d}%",
                         w // 2, line_y - 9, (170, 230, 210, 210),
                         9, FN, anchor_x="center", anchor_y="top", bold=True)

        # ── Timer ───────────────────────────────────
        self._txt_shadow(f"{self.time_alive:06.1f}s", w - 16, h - 52,
                         (165, 200, 255, 210), 11, FN, anchor_x="right", bold=True)
        enemy_cap = min(
            MAZE_ENEMY_BASE_CAP + self.maze_level * MAZE_ENEMY_CAP_PER_FLOOR,
            MAZE_ENEMY_MAX_CAP,
        )
        self._txt_shadow(f"ENEMIES  {len(self.maze_enemies)}/{enemy_cap}",
                         w - 16, h - 72, (255, 145, 120, 190),
                         10, FN, anchor_x="right", bold=True)
        keys_left = max(0, MAZE_KEYS_REQUIRED - self.maze_keys_collected)
        key_time = max(0, int(math.ceil(getattr(self, "maze_key_relocate_timer", 0.0))))
        self._txt_shadow(f"KEYS  {self.maze_keys_collected}/{MAZE_KEYS_REQUIRED}   SHIFT {key_time:03d}s",
                         w - 16, h - 90, (255, 220, 95, 215 if keys_left else 170),
                         10, FN, anchor_x="right", bold=True)

        # ── Breach-cell storage ─────────────────────
        breach_count = p.inventory.get("breach", 0)
        active = getattr(p, "breach_active", False)
        panel_x = 16
        panel_y = h - 118
        panel_w = 210
        panel_h = 28
        amber = (255, 190, 55)
        fill_a = 110 if active else 55
        arcade.draw_lrbt_rectangle_filled(
            panel_x, panel_x + panel_w, panel_y - panel_h, panel_y,
            (*amber, fill_a))
        arcade.draw_lrbt_rectangle_outline(
            panel_x, panel_x + panel_w, panel_y - panel_h, panel_y,
            (*amber, 180 if breach_count else 85), 1)
        label = f"[4] BREACH  {breach_count}/{MAZE_BREACH_MAX_STORAGE}"
        if active:
            label += f"  {p.breach_timer:.0f}s"
        self._txt_shadow(label, panel_x + 10, panel_y - 20,
                         (*amber, 230 if breach_count or active else 130),
                         10, FN, bold=True)

        # ── Hint ────────────────────────────────────
        arcade.draw_text("WASD Move · Hold LMB to Fire · [4] Breach Walls · Find the EXIT · ESC Pause · H Hide HUD",
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
        if getattr(self, "maze_map_open", False):
            self._draw_maze_map_overlay()

    def _draw_maze_minimap(self):
        maze   = self.maze_grid
        mode_c = tuple((getattr(self, "maze_preset", None) or MAZE_PRESETS[0])["color"][:3])
        mx, my, mw, mh, mm_cs, pad = self._maze_minimap_layout()
        mini_bg = (
            max(4, int(mode_c[0] * 0.10)),
            max(6, int(mode_c[1] * 0.10)),
            max(12, int(mode_c[2] * 0.12)),
        )

        # Panel: glassy and mostly transparent so the maze stays visible underneath.
        arcade.draw_lrbt_rectangle_filled(mx - pad, mx + mw + pad, my - pad, my + mh + pad, (*mini_bg, 58))
        arcade.draw_lrbt_rectangle_outline(mx - pad, mx + mw + pad, my - pad, my + mh + pad,
                                            (*mode_c, 185), 2)
        arcade.draw_lrbt_rectangle_outline(mx - 2, mx + mw + 2, my - 2, my + mh + 2,
                                            (220, 232, 240, 96), 1)

        MWTT = max(1, mm_cs // 5)
        wc2  = (58, 64, 72, 220)

        # Floors
        for row in range(maze.rows):
            for col in range(maze.cols):
                fx = mx + col * mm_cs;  fy = my + row * mm_cs
                arcade.draw_lrbt_rectangle_filled(fx, fx + mm_cs, fy, fy + mm_cs, (*mini_bg, 80))

        # Walls
        for row in range(maze.rows):
            for col in range(maze.cols):
                fx = mx + col * mm_cs;  fy = my + row * mm_cs
                if row < maze.rows - 1 and not maze.is_open(col, row, MazeGrid.N):
                    wall_c = (255, 118, 108, 220) if maze.is_breakable_wall(col, row, MazeGrid.N) else wc2
                    arcade.draw_lrbt_rectangle_filled(
                        fx, fx + mm_cs,
                        fy + mm_cs - MWTT, fy + mm_cs + MWTT, wall_c)
                if col < maze.cols - 1 and not maze.is_open(col, row, MazeGrid.E):
                    wall_c = (255, 118, 108, 220) if maze.is_breakable_wall(col, row, MazeGrid.E) else wc2
                    arcade.draw_lrbt_rectangle_filled(
                        fx + mm_cs - MWTT, fx + mm_cs + MWTT,
                        fy, fy + mm_cs, wall_c)

        # Border
        arcade.draw_lrbt_rectangle_outline(mx, mx + mw, my, my + mh, wc2, MWTT)

        # Exit marker
        ex2 = mx + (self.maze_exit_col + 0.5) * mm_cs
        ey2 = my + (self.maze_exit_row + 0.5) * mm_cs
        exit_mini_c = (0, 255, 155, 210) if self.maze_keys_collected >= MAZE_KEYS_REQUIRED else (255, 165, 60, 210)
        arcade.draw_circle_filled(ex2, ey2, mm_cs * 0.45, exit_mini_c)

        # Key markers
        for key in getattr(self, "maze_keys", []):
            if key.get("collected", False):
                continue
            kx = mx + (key["col"] + 0.5) * mm_cs
            ky = my + (key["row"] + 0.5) * mm_cs
            arcade.draw_circle_filled(kx, ky, max(2, mm_cs * 0.36), (255, 220, 70, 235))
            arcade.draw_circle_outline(kx, ky, max(3, mm_cs * 0.55), (255, 245, 160, 160), 1)

        # Player marker
        pc2, pr2 = self._maze_player_cell()
        px3 = mx + (pc2 + 0.5) * mm_cs
        py3 = my + (pr2 + 0.5) * mm_cs
        arcade.draw_circle_filled(px3, py3, mm_cs * 0.46, (90, 200, 255, 245))

        enemy_count = len(self.maze_enemies)
        for enemy in self.maze_enemies:
            ex3 = mx + (enemy.maze_col + 0.5) * mm_cs
            ey3 = my + (enemy.maze_row + 0.5) * mm_cs
            arcade.draw_circle_filled(ex3, ey3, max(2, mm_cs * 0.34), (255, 70, 70, 230))
            arcade.draw_circle_outline(ex3, ey3, max(3, mm_cs * 0.48), (255, 150, 120, 150), 1)

        self._txt_shadow(f"ENEMY {enemy_count}", mx + mw + pad, my - 14,
                         (255, 135, 115, 210), 8, FONT_NUMERIC,
                         anchor_x="right", anchor_y="top", bold=True)

    def _draw_maze_map_overlay(self):
        maze = self.maze_grid
        mode_c = tuple((getattr(self, "maze_preset", None) or MAZE_PRESETS[0])["color"][:3])
        w, h = self.width, self.height
        FU = FONT_UI_MENU
        FN = FONT_NUMERIC

        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (2, 4, 12, 168))

        max_map_w = w * 0.82
        max_map_h = h * 0.72
        mm_cs = max(3.0, min(max_map_w / maze.cols, max_map_h / maze.rows))
        mw = maze.cols * mm_cs
        mh = maze.rows * mm_cs
        mx = (w - mw) / 2
        my = (h - mh) / 2 - 8

        bg_c = (
            max(5, int(mode_c[0] * 0.12)),
            max(7, int(mode_c[1] * 0.12)),
            max(15, int(mode_c[2] * 0.14)),
        )
        wall_c = (82, 90, 110, 215)
        break_c = (255, 105, 85, 218)

        arcade.draw_lrbt_rectangle_filled(mx - 18, mx + mw + 18, my - 18, my + mh + 18, (*bg_c, 104))
        arcade.draw_lrbt_rectangle_outline(mx - 18, mx + mw + 18, my - 18, my + mh + 18, (*mode_c, 210), 3)
        arcade.draw_lrbt_rectangle_outline(mx - 8, mx + mw + 8, my - 8, my + mh + 8, (220, 235, 245, 80), 1)

        for row in range(maze.rows):
            for col in range(maze.cols):
                fx = mx + col * mm_cs
                fy = my + row * mm_cs
                arcade.draw_lrbt_rectangle_filled(fx, fx + mm_cs, fy, fy + mm_cs, (*bg_c, 96))

        wt = max(1.5, mm_cs * 0.20)
        for row in range(maze.rows):
            for col in range(maze.cols):
                fx = mx + col * mm_cs
                fy = my + row * mm_cs
                if row < maze.rows - 1 and not maze.is_open(col, row, MazeGrid.N):
                    c = break_c if maze.is_breakable_wall(col, row, MazeGrid.N) else wall_c
                    arcade.draw_lrbt_rectangle_filled(fx, fx + mm_cs, fy + mm_cs - wt, fy + mm_cs + wt, c)
                if col < maze.cols - 1 and not maze.is_open(col, row, MazeGrid.E):
                    c = break_c if maze.is_breakable_wall(col, row, MazeGrid.E) else wall_c
                    arcade.draw_lrbt_rectangle_filled(fx + mm_cs - wt, fx + mm_cs + wt, fy, fy + mm_cs, c)

        arcade.draw_lrbt_rectangle_outline(mx, mx + mw, my, my + mh, wall_c, max(2, int(wt)))

        ex = mx + (self.maze_exit_col + 0.5) * mm_cs
        ey = my + (self.maze_exit_row + 0.5) * mm_cs
        exit_map_c = (105, 255, 170, 225) if self.maze_keys_collected >= MAZE_KEYS_REQUIRED else (255, 165, 60, 225)
        arcade.draw_circle_filled(ex, ey, max(5, mm_cs * 0.34), exit_map_c)
        arcade.draw_circle_outline(ex, ey, max(8, mm_cs * 0.56), (*exit_map_c[:3], 160), 2)

        for key in getattr(self, "maze_keys", []):
            if key.get("collected", False):
                continue
            kx = mx + (key["col"] + 0.5) * mm_cs
            ky = my + (key["row"] + 0.5) * mm_cs
            arcade.draw_circle_filled(kx, ky, max(4, mm_cs * 0.30), (255, 220, 70, 240))
            arcade.draw_circle_outline(kx, ky, max(7, mm_cs * 0.52), (255, 245, 160, 170), 2)

        pc, pr = self._maze_player_cell()
        px = mx + (pc + 0.5) * mm_cs
        py = my + (pr + 0.5) * mm_cs
        arcade.draw_circle_filled(px, py, max(5, mm_cs * 0.36), (90, 200, 255, 245))
        arcade.draw_circle_outline(px, py, max(8, mm_cs * 0.58), (180, 235, 255, 190), 2)

        enemy_count = len(self.maze_enemies)
        for enemy in self.maze_enemies:
            ex3 = mx + (enemy.maze_col + 0.5) * mm_cs
            ey3 = my + (enemy.maze_row + 0.5) * mm_cs
            arcade.draw_circle_filled(ex3, ey3, max(4, mm_cs * 0.28), (255, 72, 72, 232))
            arcade.draw_circle_outline(ex3, ey3, max(7, mm_cs * 0.50), (255, 145, 115, 150), 2)

        progress = int(max(getattr(self, "maze_progress_best", 0.0), self._maze_completion_ratio()) * 100)
        self._txt_shadow("MAZE MAP", w // 2, my + mh + 52, (190, 255, 220, 245),
                         22, FU, anchor_x="center", bold=True)
        self._txt_shadow(f"FLOOR {self.maze_level + 1}   {progress:02d}% COMPLETE   ENEMIES {enemy_count}",
                         w // 2, my + mh + 28, (150, 210, 230, 220),
                         11, FN, anchor_x="center", bold=True)
        self._txt_shadow("CLICK ANYWHERE OR PRESS ESC TO CLOSE",
                         w // 2, max(20, my - 42), (135, 170, 210, 185),
                         10, FN, anchor_x="center", bold=True)

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
        complete = getattr(self, "maze_run_complete", False)
        accent = (120, 255, 160, 220) if complete else (200, 35, 35, 200)
        title = "MAZE CLEAR" if complete else "MAZE OVER"
        title_color = (120, 255, 160, 255) if complete else (255, 50, 50, 255)

        arcade.draw_lrbt_rectangle_outline(cx2, cx2 + cw2, cy2, cy2 + ch2, accent, 2)

        mid = w // 2
        self._txt_shadow(title, mid, cy2 + ch2 - 58, title_color,
                         50, FU, anchor_x="center", bold=True)
        arcade.draw_line(cx2 + 24, cy2 + ch2 - 78, cx2 + cw2 - 24, cy2 + ch2 - 78, (*accent[:3], 130), 1)
        self._txt_shadow(f"FLOOR  {min(self.maze_level + 1, MAZE_MAX_LEVELS)}/{MAZE_MAX_LEVELS}",
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
        if getattr(self, "maze_map_open", False):
            self.mouse_held = False
            return

        self.time_alive += delta
        self.maze_exit_lock_notice_timer = max(
            0.0, getattr(self, "maze_exit_lock_notice_timer", 0.0) - delta)
        self.maze_key_relocate_timer -= delta
        if (self.maze_key_relocate_timer <= 0
                and self.maze_keys_collected < MAZE_KEYS_REQUIRED):
            self._relocate_maze_keys()
        self.maze_potion_spawn_timer -= delta
        if self.maze_potion_spawn_timer <= 0:
            self.maze_potion_spawn_timer += MAZE_POTION_SPAWN_INTERVAL
            self._spawn_maze_potion("maze_health")
            self._spawn_maze_potion("maze_speed")
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

        # Keep the ship hitbox small even when maze cells are large, so it can
        # slide through corridors and pass beside walls without feeling stuck.
        PLAYER_R = max(18, min(28, getattr(p, "width", 72) * 0.32))
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

        # Maze ship art has its nose at the top and wings on the sides.
        # Rotate the nose into the direction the ship is actually moving.
        speed_len = math.hypot(p.change_x, p.change_y)
        if speed_len > 4.0:
            target_angle = self._maze_player_angle_from_motion(p.change_x, p.change_y)
            diff = (target_angle - p.angle + 180.0) % 360.0 - 180.0
            p.angle += diff * min(1.0, 18.0 * delta)
        p.update_powerups(delta)

        # Engine trail comes from the right-side tail, opposite the movement direction.
        if speed_len > 60 and random.random() < 0.50:
            move_ang = math.atan2(p.change_y, p.change_x)
            tail_dist = max(12.0, min(24.0, getattr(p, "width", 72) * 0.22))
            side_ang = move_ang + math.pi / 2
            tail_spread = random.uniform(-5.0, 5.0)
            tail_x = p.center_x - math.cos(move_ang) * tail_dist + math.cos(side_ang) * tail_spread
            tail_y = p.center_y - math.sin(move_ang) * tail_dist + math.sin(side_ang) * tail_spread
            ang = move_ang + math.pi + random.uniform(-0.35, 0.35)
            self._add_particle(
                tail_x,
                tail_y,
                math.cos(ang) * random.uniform(55, 130),
                math.sin(ang) * random.uniform(55, 130),
                random.uniform(1.2, 2.2), random.uniform(0.10, 0.22),
                (90, 200, 255), 0.88)

        # ── Key collection ───────────────────────────
        self._collect_maze_key_at_player()

        # ── Exit check ───────────────────────────────
        pc2, pr2 = self._maze_player_cell()
        self.maze_progress_best = max(
            getattr(self, "maze_progress_best", 0.0),
            self._maze_completion_ratio(),
        )
        if (pc2 == self.maze_exit_col and pr2 == self.maze_exit_row
                and not self.maze_exit_reached):
            if self.maze_keys_collected < MAZE_KEYS_REQUIRED:
                if self.maze_exit_lock_notice_timer <= 0:
                    needed = MAZE_KEYS_REQUIRED - self.maze_keys_collected
                    self.notif_text = f"EXIT LOCKED!  {needed} KEY{'S' if needed != 1 else ''} NEEDED"
                    self.notif_color = (255, 190, 70)
                    self.notif_timer = 1.1
                    self.maze_exit_lock_notice_timer = 1.25
            else:
                self.maze_exit_reached = True
                bonus = max(0, 2000 - int(self.time_alive * 5))
                self.score += bonus
                if self.maze_level + 1 >= MAZE_MAX_LEVELS:
                    self.maze_run_complete = True
                    self.notif_text = f"MAZE COMPLETE!  +{bonus} TIME BONUS"
                    self.notif_color = (120, 255, 160)
                    self.notif_timer = 1.8
                    self.game_state = STATE_MAZE_OVER
                    self.set_mouse_visible(True)
                    return
                self.maze_level += 1
                self.notif_text  = f"EXIT FOUND!  +{bonus} TIME BONUS  →  FLOOR {self.maze_level + 1}"
                self.notif_color = (120, 255, 160)
                self.notif_timer = 1.8
                self.setup_maze(keep_player=True)

        self._update_particles(delta)

        # ── Maze-only breach powerups ───────────────────────────────
        self.powerups.update(delta)
        for pu in list(self.powerups):
            if pu.life <= 0:
                pu.remove_from_sprite_lists()
                continue
            if arcade.check_for_collision(pu, p):
                if not self._collect_maze_potion(pu):
                    self._collect_powerup(pu.kind)
                    self._burst(pu.center_x, pu.center_y, 12,
                                (255, 195, 65), 45, 150, 0.9, 2.1, .06, .18)
                pu.remove_from_sprite_lists()

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
            wall_hit = self._maze_wall_at_point(b.center_x, b.center_y, 5)
            blocked = not self._maze_can_move_to(b.center_x, b.center_y, 5)
            if b.life <= 0:
                self._burst(b.center_x, b.center_y, 5,
                            (180, 220, 255), 35, 110, 0.7, 1.6, .04, .12)
                b.remove_from_sprite_lists()
            elif wall_hit:
                col, row, direction = wall_hit
                if getattr(p, "breach_active", False):
                    damaged, broken, hp_left = maze.damage_wall(col, row, direction)
                    if broken:
                        self.notif_text = "BREACH OPENED!"
                        self.notif_color = (255, 205, 80)
                        self.notif_timer = 0.9
                        self._burst(b.center_x, b.center_y, 26,
                                    (255, 190, 65), 70, 260, 1.4, 3.4, .12, .32)
                    elif damaged:
                        self.notif_text = f"WALL CRACKED  {hp_left} HP"
                        self.notif_color = (255, 195, 80)
                        self.notif_timer = max(self.notif_timer, 0.45)
                        self._burst(b.center_x, b.center_y, 12,
                                    (255, 185, 55), 55, 180, 0.9, 2.2, .06, .18)
                    else:
                        self._burst(b.center_x, b.center_y, 7,
                                    (95, 230, 155), 35, 120, 0.6, 1.5, .04, .10)
                else:
                    self._burst(b.center_x, b.center_y, 5,
                                (180, 220, 255), 35, 110, 0.7, 1.6, .04, .12)
                b.remove_from_sprite_lists()
            elif blocked:
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

        max_enemies = min(
            MAZE_ENEMY_MAX_CAP,
            MAZE_ENEMY_BASE_CAP + self.maze_level * MAZE_ENEMY_CAP_PER_FLOOR,
        )

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
                    if random.randint(1, 100) <= MAZE_BREACH_DROP_CHANCE:
                        self._drop_maze_breach_powerup(enemy.center_x, enemy.center_y)
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
            self.maze_spawn_timer = self._maze_enemy_spawn_interval()
            self._spawn_maze_enemy()

        # ── Five-enemy ambush wave every 10 seconds ─────────────────
        self.maze_corner_wave_timer -= delta
        if self.maze_corner_wave_timer <= 0:
            self.maze_corner_wave_timer += MAZE_CORNER_WAVE_INTERVAL
            self._spawn_maze_corner_wave(max_enemies)

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

    def _spawn_maze_enemy(self) -> bool:
        """Pick a random cell far from the player and place a MazeEnemy there."""
        maze   = self.maze_grid
        pc, pr = self._maze_player_cell()
        key_cells = {
            (key["col"], key["row"])
            for key in getattr(self, "maze_keys", [])
            if not key.get("collected", False)
        }

        for _ in range(40):          # up to 40 attempts to find a valid cell
            col = random.randint(0, maze.cols - 1)
            row = random.randint(0, maze.rows - 1)
            # Must be far from player, not on the exit
            if (abs(col - pc) + abs(row - pr) >= 7
                    and not (col == self.maze_exit_col and row == self.maze_exit_row)
                    and (col, row) not in key_cells):
                return self._spawn_maze_enemy_at(col, row)
        return False

    def _spawn_maze_enemy_at(self, col: int, row: int) -> bool:
        enemy = MazeEnemy(col, row, self.maze_cell_size, *self.maze_origin)
        self.maze_enemies.append(enemy)
        self.maze_enemies_created += 1
        return True

    def _spawn_maze_corner_wave(self, max_enemies: int) -> int:
        """Spawn a five-enemy wave from a random maze corner when there is room."""
        if len(self.maze_enemies) >= max_enemies:
            return 0

        maze = self.maze_grid
        pc, pr = self._maze_player_cell()
        corners = [
            (0, 0),
            (maze.cols - 1, 0),
            (0, maze.rows - 1),
            (maze.cols - 1, maze.rows - 1),
        ]
        random.shuffle(corners)
        occupied = {
            (enemy.maze_col, enemy.maze_row)
            for enemy in self.maze_enemies
        }
        blocked = {
            (0, maze.rows - 1),
            (self.maze_exit_col, self.maze_exit_row),
            (pc, pr),
        }
        for key in getattr(self, "maze_keys", []):
            if not key.get("collected", False):
                blocked.add((key["col"], key["row"]))

        for corner_col, corner_row in corners:
            candidates = []
            col_range = range(0, min(5, maze.cols)) if corner_col == 0 else range(max(0, maze.cols - 5), maze.cols)
            row_range = range(0, min(5, maze.rows)) if corner_row == 0 else range(max(0, maze.rows - 5), maze.rows)
            for col in col_range:
                for row in row_range:
                    cell = (col, row)
                    if cell in occupied or cell in blocked:
                        continue
                    if abs(col - pc) + abs(row - pr) < 6:
                        continue
                    candidates.append(cell)

            random.shuffle(candidates)
            spawned = 0
            for col, row in candidates:
                if spawned >= MAZE_CORNER_WAVE_SIZE or len(self.maze_enemies) >= max_enemies:
                    break
                self._spawn_maze_enemy_at(col, row)
                occupied.add((col, row))
                spawned += 1

            if spawned:
                self.notif_text = f"CORNER WAVE!  +{spawned}"
                self.notif_color = (255, 120, 90)
                self.notif_timer = max(self.notif_timer, 0.9)
                return spawned

        return 0

    def _drop_maze_breach_powerup(self, x: float, y: float) -> None:
        """Drop a stationary breach cell that can arm wall-breaking rounds."""
        pu = Powerup(x, y, "breach")
        pu.change_y = 0
        pu.life = 10.0
        self.powerups.append(pu)
        self._burst(x, y, 14, (255, 195, 65), 40, 150, 0.8, 2.0, .05, .16)

    def _split_maze_enemy(self, enemy: MazeEnemy, max_enemies: int) -> bool:
        """Duplicate a surviving maze enemy into a nearby open cell."""
        if (len(self.maze_enemies) >= max_enemies
                or enemy.health <= 1):
            return False

        maze = self.maze_grid
        cs = self.maze_cell_size
        ox, oy = self.maze_origin
        occupied = {
            (other.maze_col, other.maze_row)
            for other in self.maze_enemies
            if other is not enemy
        }
        key_cells = {
            (key["col"], key["row"])
            for key in getattr(self, "maze_keys", [])
            if not key.get("collected", False)
        }
        options = []
        for direction in (MazeGrid.N, MazeGrid.E, MazeGrid.S, MazeGrid.W):
            if not maze.is_open(enemy.maze_col, enemy.maze_row, direction):
                continue
            col = enemy.maze_col + MazeGrid.DX[direction]
            row = enemy.maze_row + MazeGrid.DY[direction]
            if ((col, row) == (self.maze_exit_col, self.maze_exit_row)
                    or (col, row) in occupied
                    or (col, row) in key_cells):
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
        self.maze_enemies_created += 1
        self.notif_text = "ENEMY SPLIT!"
        self.notif_color = (255, 170, 110)
        self.notif_timer = max(self.notif_timer, 0.45)
        self._burst(enemy.center_x, enemy.center_y, 10,
                    (255, 120, 90), 45, 140, 0.8, 1.8, .05, .14)
        return True

    def _maze_gameover(self):
        self.maze_run_complete = False
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
                "label":   "CLASSIC",
                "icon":    "◈",
                "desc":    "Classic space combat",
                "detail":  "10 levels · Shop · Boss fights",
                "color":   (90, 198, 255),
                "available": True,
            },
            {
                "key":     "maze",
                "label":   "MAZE",
                "icon":    "⬡",
                "desc":    "Navigate & survive",
                "detail":  f"{MAZE_MAX_LEVELS} floors · Procedural arenas",
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

        reset_w = 118
        reset_h = 32
        reset_x = w - reset_w - 22
        reset_y = 22
        reset_hov = self._is_hovering(reset_x, reset_x + reset_w, reset_y, reset_y + reset_h)
        reset_fill = (130, 32, 48, 230) if reset_hov else (70, 24, 38, 190)
        reset_border = (255, 110, 125, 230) if reset_hov else (210, 85, 105, 150)
        reset_text = (255, 225, 230, 255) if reset_hov else (255, 160, 172, 215)
        arcade.draw_lrbt_rectangle_filled(reset_x, reset_x + reset_w,
                                           reset_y, reset_y + reset_h, reset_fill)
        arcade.draw_lrbt_rectangle_outline(reset_x, reset_x + reset_w,
                                            reset_y, reset_y + reset_h, reset_border, 1)
        arcade.draw_text("RESET", reset_x + reset_w // 2, reset_y + reset_h // 2,
                         reset_text, 12, anchor_x="center", anchor_y="center",
                         bold=True, font_name=FU)
        self._mode_btns["__reset_save__"] = (
            reset_x, reset_x + reset_w, reset_y, reset_y + reset_h
        )

        mode_feedback = getattr(self, "mode_feedback", "")
        if mode_feedback:
            arcade.draw_text(mode_feedback, w // 2, h - 164,
                             getattr(self, "mode_feedback_color", (160, 180, 215, 180)),
                             11, anchor_x="center", bold=True, font_name=FU)

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

        self._reset_confirm_btns = {}
        if getattr(self, "reset_confirm_open", False):
            elapsed = max(0.0, self.bg_time - getattr(self, "reset_confirm_started", self.bg_time))
            raw = min(1.0, elapsed / 0.32)
            c1 = 1.70158
            c3 = c1 + 1.0
            pop = 1.0 + c3 * (raw - 1.0) ** 3 + c1 * (raw - 1.0) ** 2
            fade = 1.0 - (1.0 - raw) ** 3
            scale = 0.72 + 0.28 * pop

            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (0, 0, 0, int(155 * fade)))

            popup_w = min(max(430, int(w * 0.58)), w - 52)
            popup_h = min(max(260, int(h * 0.44)), h - 70)
            draw_w = popup_w * scale
            draw_h = popup_h * scale
            cx = w / 2
            cy = h / 2
            popup_l = cx - draw_w / 2
            popup_r = cx + draw_w / 2
            popup_b = cy - draw_h / 2
            popup_t = cy + draw_h / 2

            panel_alpha = int(246 * fade)
            border_alpha = int(210 * fade)
            inner_alpha = int(90 * fade)
            text_alpha = int(255 * fade)
            shadow_alpha = int(95 * fade)

            arcade.draw_lrbt_rectangle_filled(popup_l + 8 * scale, popup_r + 8 * scale,
                                               popup_b - 8 * scale, popup_t - 8 * scale,
                                               (0, 0, 0, int(105 * fade)))
            arcade.draw_lrbt_rectangle_filled(popup_l, popup_r, popup_b, popup_t,
                                               (9, 18, 48, panel_alpha))
            arcade.draw_lrbt_rectangle_outline(popup_l, popup_r, popup_b, popup_t,
                                                (90, 198, 255, border_alpha), max(1, int(2 * scale)))
            arcade.draw_lrbt_rectangle_outline(popup_l + 8 * scale, popup_r - 8 * scale,
                                                popup_b + 8 * scale, popup_t - 8 * scale,
                                                (70, 112, 205, inner_alpha), 1)

            accent = (90, 198, 255, int(170 * fade))
            accent_len = 30 * scale
            for ax, ay, sx, sy in ((popup_l, popup_t, 1, -1), (popup_r, popup_t, -1, -1),
                                   (popup_l, popup_b, 1, 1), (popup_r, popup_b, -1, 1)):
                arcade.draw_line(ax, ay, ax + sx * accent_len, ay, accent, 2)
                arcade.draw_line(ax, ay, ax, ay + sy * accent_len, accent, 2)

            title_size = max(18, int(30 * scale))
            title_y = popup_t - draw_h * 0.30
            arcade.draw_text("Reset The Game?", cx + 2 * scale, title_y - 2 * scale,
                             (0, 0, 0, shadow_alpha), title_size, anchor_x="center",
                             anchor_y="center", bold=True, font_name=FU)
            arcade.draw_text("Reset The Game?", cx, title_y,
                             (235, 245, 255, text_alpha), title_size, anchor_x="center",
                             anchor_y="center", bold=True, font_name=FU)

            btn_w = max(118, int(draw_w * 0.24))
            btn_h = max(38, int(draw_h * 0.15))
            gap = max(20, int(draw_w * 0.06))
            yes_x = w // 2 - gap // 2 - btn_w
            no_x = w // 2 + gap // 2
            btn_y = popup_b + draw_h * 0.23

            yes_hov = self._is_hovering(yes_x, yes_x + btn_w, btn_y, btn_y + btn_h)
            no_hov = self._is_hovering(no_x, no_x + btn_w, btn_y, btn_y + btn_h)

            yes_fill = (55, 220, 100, int(245 * fade)) if yes_hov else (35, 168, 78, int(230 * fade))
            no_fill = (255, 82, 92, int(245 * fade)) if no_hov else (185, 45, 56, int(230 * fade))

            arcade.draw_lrbt_rectangle_filled(yes_x, yes_x + btn_w, btn_y, btn_y + btn_h, yes_fill)
            arcade.draw_lrbt_rectangle_outline(yes_x, yes_x + btn_w, btn_y, btn_y + btn_h,
                                                (140, 255, 170, text_alpha), 2)
            arcade.draw_text("YES", yes_x + btn_w // 2, btn_y + btn_h // 2,
                             (8, 18, 12, text_alpha), max(14, int(16 * scale)), anchor_x="center",
                             anchor_y="center", bold=True, font_name=FU)

            arcade.draw_lrbt_rectangle_filled(no_x, no_x + btn_w, btn_y, btn_y + btn_h, no_fill)
            arcade.draw_lrbt_rectangle_outline(no_x, no_x + btn_w, btn_y, btn_y + btn_h,
                                                (255, 155, 165, text_alpha), 2)
            arcade.draw_text("NO", no_x + btn_w // 2, btn_y + btn_h // 2,
                             (255, 245, 245, text_alpha), max(14, int(16 * scale)), anchor_x="center",
                             anchor_y="center", bold=True, font_name=FU)

            self._reset_confirm_btns["confirm"] = (yes_x, yes_x + btn_w, btn_y, btn_y + btn_h)
            self._reset_confirm_btns["cancel"] = (no_x, no_x + btn_w, btn_y, btn_y + btn_h)

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
        arcade.draw_text("SELECT MAZE PLAN", w // 2, h - 92,
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
        selected_preset = next(
            (p for p in MAZE_PRESETS if p["key"] == self.selected_maze_preset),
            MAZE_PRESETS[0],
        )

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
            desc_c = (238, 255, 244, 255) if sel else (222, 242, 230, 245)
            det_c = (190, 238, 205, 245) if sel else (164, 214, 178, 225)

            line_y = ct - 138
            for line in desc_lines[:2]:
                self._txt_shadow(line, cx_, line_y, desc_c, 9 if card_w < 200 else 10,
                                 FU, anchor_x="center", bold=True, ox=2, oy=-2)
                line_y -= 16

            line_y -= 6
            for line in detail_lines[:2]:
                self._txt_shadow(line, cx_, line_y, det_c, 8 if card_w < 200 else 9,
                                 FN, anchor_x="center", bold=True, ox=2, oy=-2)
                line_y -= 14

            # SELECT button at bottom of card
            btn_bw = card_w - 24;  btn_bh = 26
            btn_bx = cl + 12;      btn_by = cb + 12
            btn_hov = self._is_hovering(btn_bx, btn_bx + btn_bw, btn_by, btn_by + btn_bh)
            btn_fill   = (*mc, 230) if (sel or btn_hov) else (*mc[:3], 82)
            btn_tc     = (8, 12, 18, 255) if (sel or btn_hov) else (235, 255, 240, 235)
            arcade.draw_lrbt_rectangle_filled(btn_bx, btn_bx + btn_bw,
                                               btn_by, btn_by + btn_bh, btn_fill)
            arcade.draw_lrbt_rectangle_outline(btn_bx, btn_bx + btn_bw,
                                                btn_by, btn_by + btn_bh, (*mc, 255), 1)
            self._txt_shadow("▶  SELECTED" if sel else "SELECT",
                             btn_bx + btn_bw // 2, btn_by + btn_bh // 2 - 1,
                             btn_tc, 10, FU, anchor_x="center", anchor_y="center",
                             bold=True, ox=1, oy=-1)

            self._maze_preset_btns[preset["key"]] = (cl, cr, cb, ct)

        # ENTER MAZE button
        play_w = 240;  play_h = 48
        play_x = w // 2 - play_w // 2
        play_y = card_y - play_h - 22
        play_hov = self._is_hovering(play_x, play_x + play_w, play_y, play_y + play_h)
        ep = 0.5 + 0.5 * math.sin(t * 3.5)
        sc = selected_preset["color"]
        e_fill   = (
            int(sc[0] * (0.72 + 0.16 * ep)),
            int(sc[1] * (0.72 + 0.16 * ep)),
            int(sc[2] * (0.72 + 0.16 * ep)),
            248,
        )
        e_border = (*sc, 255 if play_hov else 225)
        if play_hov:
            arcade.draw_lrbt_rectangle_filled(play_x - 2, play_x + play_w + 2,
                                               play_y - 2, play_y + play_h + 2,
                                               (*sc, 34))
        arcade.draw_lrbt_rectangle_filled(play_x, play_x + play_w,
                                           play_y, play_y + play_h, e_fill)
        arcade.draw_lrbt_rectangle_outline(play_x, play_x + play_w,
                                            play_y, play_y + play_h, e_border, 2)
        self._txt_shadow("[ ENTER MAZE ]", w // 2, play_y + play_h // 2,
                         (255, 255, 255, 255), 18, FU,
                         anchor_x="center", anchor_y="center", bold=True, ox=2, oy=-2)
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

        arcade.draw_text("Select a maze plan, then press ENTER MAZE  ·  ESC to go back",
                         w // 2, 16, (70, 130, 95, 140), 9,
                         anchor_x="center", font_name=FN)

    def _start_maze_with_preset(self):
        """Reset all maze run state and start a fresh maze with the chosen preset."""
        self.maze_preset = next(
            (p for p in MAZE_PRESETS if p["key"] == self.selected_maze_preset),
            MAZE_PRESETS[0]
        )
        self.maze_level = 0
        self.maze_run_complete = False
        self.score      = 0
        self.time_alive = 0.0
        self.run_coins  = 0
        self.setup_maze(keep_player=False)
