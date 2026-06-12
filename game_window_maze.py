from game_support import *

import arcade
import heapq
import itertools
import math
import random


FONT_UI_MENU = ("Avenir Next", "Verdana", "Trebuchet MS", "Arial")
FONT_NUMERIC = ("SF Mono", "Menlo", "Monaco", "Courier New", "monospace")


class MazeModeMixin:

    # ══════════════════════════════════════════════════
    #  MAZE MODE — SETUP
    # ══════════════════════════════════════════════════

    def _maze_display_floor(self) -> int:
        return max(1, min(MAZE_MAX_LEVELS, getattr(self, "maze_level", 0) + 1))

    def _maze_legacy_floor(self) -> int:
        floor_idx = self._maze_display_floor() - 1
        floor_idx = max(0, min(len(MAZE_LEGACY_FLOORS) - 1, floor_idx))
        return MAZE_LEGACY_FLOORS[floor_idx]

    def _maze_legacy_level_index(self) -> int:
        return max(0, self._maze_legacy_floor() - 1)

    def _maze_enemy_cap(self) -> int:
        return min(
            MAZE_ENEMY_MAX_CAP,
            MAZE_ENEMY_BASE_CAP + self._maze_floor_index() * MAZE_ENEMY_CAP_PER_FLOOR,
        )

    def _maze_floor_index(self) -> int:
        return max(0, self._maze_display_floor() - 1)

    def _save_maze_resume_floor(self, level: int | None = None) -> None:
        if level is None:
            level = getattr(self, "maze_level", 0)
        self.maze_saved_level = max(0, min(MAZE_MAX_LEVELS - 1, int(level)))
        if hasattr(self, "_save_progress"):
            self._save_progress()

    def _clear_maze_resume_floor(self) -> None:
        self.maze_saved_level = 0
        if hasattr(self, "_save_progress"):
            self._save_progress()

    def _maze_floor_progress(self) -> float:
        if MAZE_MAX_LEVELS <= 1:
            return 1.0
        return self._maze_floor_index() / (MAZE_MAX_LEVELS - 1)

    def _maze_initial_enemy_target(self) -> int:
        return MAZE_ENEMIES_PER_FLOOR + self._maze_floor_index() * MAZE_ENEMY_COUNT_PER_FLOOR

    def _maze_is_final_floor(self) -> bool:
        return self._maze_display_floor() >= MAZE_MAX_LEVELS

    def _maze_player_speed_multiplier(self) -> float:
        progress = self._maze_floor_progress()
        return (
            MAZE_PLAYER_START_SPEED_MULT
            + (MAZE_PLAYER_FINAL_SPEED_MULT - MAZE_PLAYER_START_SPEED_MULT) * progress
        )

    def _maze_floor_power_scale(self, start: float, final: float) -> float:
        start = max(0.000001, float(start))
        final = max(start, float(final))
        if self._maze_is_final_floor():
            return final
        return start * ((final / start) ** self._maze_floor_progress())

    def _maze_player_damage_multiplier(self) -> float:
        return self._maze_floor_power_scale(
            MAZE_PLAYER_START_DAMAGE_MULT,
            MAZE_PLAYER_FINAL_DAMAGE_MULT,
        )

    def _maze_player_damage(self, amount: float) -> float:
        return amount * self._maze_player_damage_multiplier()

    def _maze_player_base_move_speed(self) -> float:
        player = getattr(self, "player", None)
        engine = getattr(player, "_engine_bonus", 1.0)
        return (
            PLAYER_SPEED
            * engine
            * SHIPS[self.selected_ship]["spd_mult"]
            * self._maze_player_speed_multiplier()
        )

    def _maze_player_move_speed(self) -> float:
        player = getattr(self, "player", None)
        speed = self._maze_player_base_move_speed()
        if getattr(player, "speed_active", False):
            speed *= 1.65
        return speed

    def _apply_maze_player_floor_stats(self, refill: bool = False) -> None:
        player = getattr(self, "player", None)
        if player is None:
            return

        base_health = getattr(self, "maze_player_base_health", None)
        if base_health is None:
            base_health = player.max_health
            self.maze_player_base_health = base_health

        progress = self._maze_floor_progress()
        target_health = int(round(
            self._maze_floor_power_scale(base_health, MAZE_PLAYER_FINAL_HEALTH)
        ))
        target_health = max(1, target_health)
        old_max = max(1, getattr(player, "max_health", target_health))
        player.max_health = target_health
        if refill:
            player.health = target_health
        else:
            gained = max(0, target_health - old_max)
            player.health = min(target_health, max(1, player.health + gained))

        if player.texture is not None:
            boss_texture = load_texture_clean(MAZE_BOSS_TEXTURE, MAZE_BOSS_TEXTURE_SCALE)
            boss_size = max(boss_texture.width, boss_texture.height)
            player_size = max(1, max(player.texture.width, player.texture.height))
            base_scale = max(0.01, getattr(player, "_maze_base_scale", player.scale))
            final_scale = max(base_scale, boss_size / player_size)
            player.scale = base_scale + (final_scale - base_scale) * progress

    def setup_maze(self, keep_player: bool = False):
        """Generate a new maze level.  Call with keep_player=True to retain HP between floors."""
        w, h  = self.width, self.height
        legacy_lvl = self._maze_legacy_level_index()
        cs    = MAZE_CELL_SIZE
        preset = getattr(self, "maze_preset", None) or MAZE_PRESETS[0]

        # Visible floors 1-10 reuse the original 50-floor difficulty curve.
        cols = MAZE_BASE_COLS + preset["cols_bonus"] + legacy_lvl * 3
        rows = MAZE_BASE_ROWS + preset["rows_bonus"] + legacy_lvl * 2
        cols = max(9, cols)
        rows = max(7, rows)
        # Keep odd dimensions (nicer-looking mazes)
        if cols % 2 == 0: cols -= 1
        if rows % 2 == 0: rows -= 1

        # Place maze at world origin — camera scrolls to show the player's area
        ox = 0
        oy = 0

        multiplayer_seed = getattr(self, "multiplayer_maze_seed", None)
        if multiplayer_seed is None:
            maze_seed = random.randint(0, 999999)
        else:
            maze_seed = int(multiplayer_seed) + int(getattr(self, "maze_level", 0)) * 1009
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
        self.maze_progress_current = 0.0
        self._maze_progress_cell = None
        self._maze_enemy_flow_target = None
        self._maze_enemy_flow_next = {}
        self._maze_enemy_flow_timer = 0.0
        self.maze_map_open = False
        self.maze_enemies_created = 0
        self._maze_next_enemy_id = 1
        self._maze_next_powerup_id = 1
        self._maze_next_enemy_bullet_id = 1
        self.multiplayer_opened_walls = set()
        if not keep_player:
            self.maze_powerup_dry_kills = 0
        self.maze_keys_collected = 0
        self.maze_key_relocate_timer = MAZE_KEY_RELOCATE_TIME
        self.maze_corner_wave_timer = MAZE_CORNER_WAVE_INTERVAL
        self.maze_potion_spawn_timer = MAZE_POTION_SPAWN_INTERVAL
        self.maze_exit_lock_notice_timer = 0.0
        self._mp_exit_event_sent_level = None

        # ── Player ──────────────────────────────────
        ship = SHIPS[self.selected_ship]
        if self.player is None or not keep_player:
            self.player = Player()
            armor_tier   = self.upgrades.get("armor", 0)
            base_hp      = int(PLAYER_HEALTH * ship["hp_mult"]) + armor_tier * 25
            self.maze_player_base_health = base_hp
            self.player.max_health = base_hp
            self.player.health     = base_hp
        elif not hasattr(self, "maze_player_base_health"):
            self.maze_player_base_health = self.player.max_health
        engine_tier = self.upgrades.get("engine", 0)
        self.player._engine_bonus = 1.0 + engine_tier * 0.12
        tex = load_texture_clean(ship["texture"])
        self.player.texture  = tex
        self.player._maze_base_scale = ship["tex_scale"]
        self.player.front_angle_offset = ship.get("front_angle_offset", 0.0)
        self._apply_maze_player_floor_stats(refill=not keep_player)
        if getattr(self, "_multiplayer_active", lambda: False)() and keep_player and self.player.health <= 0:
            self.player.health = self.player.max_health
        # Spawn at top-left cell
        player_start_x = ox + 0.5 * cs
        player_start_y = oy + (rows - 0.5) * cs
        if getattr(self, "multiplayer_role", None) in ("host", "client"):
            spawn_offsets = {
                1: (0.0, 0.0),
                2: (cs * 0.18, -cs * 0.10),
                3: (cs * 0.10, -cs * 0.24),
            }
            off_x, off_y = spawn_offsets.get(getattr(self, "multiplayer_player_id", 1), (0.0, 0.0))
            player_start_x += off_x
            player_start_y += off_y
        self.player.center_x = player_start_x
        self.player.center_y = player_start_y
        self.player.change_x = 0.0;  self.player.change_y = 0.0
        self.player.angle    = 90.0 + self.player.front_angle_offset
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
        self.beams              = []                    # Interceptor beams in maze mode
        self.elec_bolts         = arcade.SpriteList()   # Reaper bolts in maze mode
        self.multiplayer_remote_bullets = arcade.SpriteList()
        self.multiplayer_remote_elec_bolts = arcade.SpriteList()
        self.multiplayer_remote_beams = []
        self.maze_boss          = None
        self.maze_bosses        = []
        self.maze_boss_spawned  = False

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
        self.notif_text         = f"MAZE  FLOOR  {self._maze_display_floor()}"
        self.notif_color        = (120, 255, 160)
        self.notif_timer        = 2.0
        self.damage_flash       = 0.0
        self.contact_damage_timer = 0.0
        self.particles          = []
        self.maze_exit_reached  = False
        self.boss_on_screen     = False
        mp_client_world = getattr(self, "_multiplayer_is_client_world", lambda: False)()
        if mp_client_world:
            self.maze_keys = []
        else:
            self._place_maze_keys()
        self._reset_maze_autopilot_for_floor()
        if not mp_client_world:
            self._spawn_maze_key_enemies()
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

    def _maze_ray_open_length(self, ox: float, oy: float, angle: float,
                              max_length: float = BEAM_RANGE) -> float:
        """Distance a beam can travel before it reaches a maze wall."""
        length, _wall_hit, _hit_x, _hit_y = self._maze_ray_wall_contact(
            ox, oy, angle, max_length)
        return length

    def _maze_ray_wall_contact(self, ox: float, oy: float, angle: float,
                               max_length: float = BEAM_RANGE) -> tuple[float, tuple | None, float, float]:
        """Return beam travel length plus the wall it reaches, if any."""
        step = 8.0
        dist = step
        while dist <= max_length:
            x = ox + math.cos(angle) * dist
            y = oy + math.sin(angle) * dist
            wall_hit = self._maze_wall_at_point(x, y, 5)
            if wall_hit is not None or not self._maze_can_move_to(x, y, 5):
                return max(0.0, dist - step), wall_hit, x, y
            dist += step
        return max_length, None, ox + math.cos(angle) * max_length, oy + math.sin(angle) * max_length

    def _clip_new_maze_beams(self, start_index: int) -> None:
        for beam in self.beams[start_index:]:
            length, wall_hit, hit_x, hit_y = self._maze_ray_wall_contact(
                beam.ox, beam.oy, beam.angle_rad, beam.length)
            beam.length = length
            self._damage_maze_wall_with_breach(wall_hit, hit_x, hit_y, (255, 150, 70))

    def _damage_maze_wall_with_breach(self, wall_hit: tuple | None,
                                      hit_x: float, hit_y: float,
                                      color: tuple) -> bool:
        if wall_hit is None or not getattr(self.player, "breach_active", False):
            return False
        col, row, direction = wall_hit
        damaged, broken, hp_left = self.maze_grid.damage_wall(col, row, direction)
        if broken:
            if isinstance(getattr(self, "_maze_autopilot_path_cache", None), dict):
                self._maze_autopilot_path_cache.clear()
            if hasattr(self, "_remember_multiplayer_open_wall"):
                self._remember_multiplayer_open_wall(col, row, direction)
            self._maze_enemy_flow_target = None
            self.notif_text = "BREACH OPENED!"
            self.notif_color = (255, 205, 80)
            self.notif_timer = 0.9
            self._burst(hit_x, hit_y, 26, color, 70, 260, 1.4, 3.4, .12, .32)
        elif damaged:
            self.notif_text = f"WALL CRACKED  {hp_left} HP"
            self.notif_color = (255, 195, 80)
            self.notif_timer = max(self.notif_timer, 0.45)
            self._burst(hit_x, hit_y, 12, color, 55, 180, 0.9, 2.2, .06, .18)
        return damaged

    def _maze_kill_enemy(self, enemy: MazeEnemy, color: tuple = (255, 130, 70)) -> None:
        self.score += 20
        self.notif_text  = "+20  ENEMY DOWN!"
        self.notif_color = (120, 255, 160)
        self.notif_timer = 0.8
        self._burst(enemy.center_x, enemy.center_y, 22,
                    color, 65, 240, 1.5, 3.2, .12, .32)
        self._maybe_drop_maze_powerup(enemy.center_x, enemy.center_y)
        enemy.remove_from_sprite_lists()

    def _maze_powerup_drop_chance(self) -> int:
        lucky_bonus = self.upgrades.get("lucky", 0) * 15
        return min(95, MAZE_POWERUP_DROP_CHANCE + lucky_bonus)

    def _maybe_drop_maze_powerup(self, x: float, y: float) -> bool:
        dry_kills = getattr(self, "maze_powerup_dry_kills", 0)
        guaranteed = dry_kills >= MAZE_POWERUP_PITY_KILLS
        if guaranteed or random.randint(1, 100) <= self._maze_powerup_drop_chance():
            self._drop_maze_powerup(x, y)
            self.maze_powerup_dry_kills = 0
            return True

        self.maze_powerup_dry_kills = dry_kills + 1
        return False

    def _damage_maze_enemy(self, enemy: MazeEnemy, amount: float, color: tuple,
                           max_enemies: int) -> bool:
        if enemy not in self.maze_enemies:
            return False
        if getattr(self, "_multiplayer_is_client_world", lambda: False)():
            enemy_id = getattr(enemy, "net_id", None)
            if enemy_id is not None and hasattr(self, "_queue_multiplayer_event"):
                self._queue_multiplayer_event({
                    "type": "enemy_damage",
                    "enemy_id": int(enemy_id),
                    "amount": float(amount),
                })
            enemy.health -= amount
            if enemy.health <= 0:
                self._burst(enemy.center_x, enemy.center_y, 18,
                            color, 58, 210, 1.1, 2.8, .09, .24)
                enemy.remove_from_sprite_lists()
            return True
        enemy.health -= amount
        if enemy.health <= 0:
            if not self._split_maze_enemy(enemy, max_enemies):
                self._maze_kill_enemy(enemy, color)
        return True

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

    @staticmethod
    def _maze_map_breakable_color(theme_color: tuple, alpha: int = 220) -> tuple:
        rgb = tuple(int(c) for c in theme_color[:3])
        return tuple(min(255, int(c + (255 - c) * 0.32)) for c in rgb) + (alpha,)

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
            pulse = 0.65 + 0.35 * math.sin(self.bg_time * 5.2 + col * 0.7 + row * 0.4)
            theme_rgb = tuple(
                int(c) for c in (glow_color[:3] if len(glow_color) >= 3 else (255, 72, 20))
            )
            glow_strength = 0.92 + 0.36 * pulse + 0.24 * ratio
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
            outer_glow = (*theme_rgb, int(76 + 72 * pulse))
            themed_glow = (*theme_rgb, int(125 + 95 * pulse))
            corner_r = min(thick * 0.28, 18)
            self._draw_round_lrbt(left - 12, right + 12, bottom - 12, top + 12, outer_glow, corner_r + 8)
            self._draw_round_lrbt(left - 6, right + 6, bottom - 6, top + 6, themed_glow, corner_r + 5)
            self._draw_round_lrbt(left, right, bottom, top, basalt, corner_r)

            rim = max(7, int(thick * 0.24))
            vein = max(6, int(thick * 0.15))
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
            self._maze_progress_cell = (pc, pr)
            self.maze_progress_current = 1.0
            return 1.0
        if self._maze_progress_cell == (pc, pr):
            return getattr(self, "maze_progress_current", 0.0)
        remaining = len(self.maze_grid.bfs(pc, pr, self.maze_exit_col, self.maze_exit_row))
        total = max(1, getattr(self, "maze_start_to_exit_steps", 1))
        self._maze_progress_cell = (pc, pr)
        self.maze_progress_current = max(0.0, min(1.0, 1.0 - remaining / total))
        return self.maze_progress_current

    def _rebuild_maze_enemy_flow(self, player_col: int, player_row: int) -> None:
        """Build one shared pathing map all maze enemies can follow toward the player."""
        flow_next = self._maze_enemy_flow_for_target(player_col, player_row)
        self._maze_enemy_flow_target = (player_col, player_row)
        self._maze_enemy_flow_next = flow_next
        self._maze_enemy_flow_timer = 0.0

    def _maze_enemy_flow_for_target(self, player_col: int, player_row: int) -> dict:
        from collections import deque

        maze = self.maze_grid
        flow_next: dict[tuple[int, int], tuple[int, int]] = {}
        seen = {(player_col, player_row)}
        q = deque([(player_col, player_row)])

        while q:
            col, row = q.popleft()
            for direction in (MazeGrid.N, MazeGrid.E, MazeGrid.S, MazeGrid.W):
                if not maze.is_open(col, row, direction):
                    continue
                nc = col + MazeGrid.DX[direction]
                nr = row + MazeGrid.DY[direction]
                if not (0 <= nc < maze.cols and 0 <= nr < maze.rows):
                    continue
                if (nc, nr) in seen:
                    continue
                seen.add((nc, nr))
                flow_next[(nc, nr)] = (col, row)
                q.append((nc, nr))

        return flow_next

    def _maze_key_world(self, col: int, row: int) -> tuple[float, float]:
        cs = self.maze_cell_size
        ox, oy = self.maze_origin
        return ox + (col + 0.5) * cs, oy + (row + 0.5) * cs

    def _maze_autopilot_unlocked(self) -> bool:
        checker = getattr(self, "_classic_campaign_complete", None)
        return bool(checker and checker())

    def _maze_autopilot_available(self) -> bool:
        return bool(
            getattr(self, "maze_autopilot_enabled", False)
            and self._maze_autopilot_unlocked()
        )

    def _maze_autopilot_can_run_now(self) -> bool:
        return bool(
            self.maze_keys_collected < MAZE_KEYS_REQUIRED
            or self._maze_autopilot_collectible_powerups()
        )

    def _toggle_maze_autopilot_from_game(self) -> None:
        if not self._maze_autopilot_unlocked():
            self.notif_text = "CLEAR ALL CLASSIC LEVELS TO UNLOCK AUTO PILOT"
            self.notif_color = (255, 210, 95)
            self.notif_timer = 1.6
            return

        if getattr(self, "maze_autopilot_enabled", False):
            self.maze_autopilot_enabled = False
            if hasattr(self, "_save_progress"):
                self._save_progress()
            self._maze_autopilot_handoff()
            self.notif_text = "AUTO PILOT OFF - MANUAL CONTROL"
            self.notif_color = (150, 205, 255)
            self.notif_timer = 1.3
            return

        self.maze_autopilot_enabled = True
        if hasattr(self, "_save_progress"):
            self._save_progress()
        self._reset_maze_autopilot_for_floor()
        self._maze_autopilot_repath_timer = 0.0
        if self.maze_autopilot_active:
            self.notif_text = "AUTO PILOT ON"
            self.notif_color = (120, 255, 170)
        else:
            self.notif_text = "AUTO PILOT ARMED FOR NEXT FLOOR"
            self.notif_color = (140, 210, 255)
        self.notif_timer = 1.5

    def _reset_maze_autopilot_for_floor(self) -> None:
        self._maze_autopilot_target_kind = None
        self._maze_autopilot_target_id = None
        self._maze_autopilot_path = []
        self._maze_autopilot_repath_timer = 0.0
        self._maze_autopilot_powerup_timer = 0.0
        self._maze_autopilot_aim = None
        self._maze_autopilot_fire_special = False
        self._maze_autopilot_decision_depth = 0
        self._maze_autopilot_path_cache = {}
        self._maze_autopilot_breach_savings_cache = {}
        self._maze_autopilot_threat_cache = {}
        self._maze_autopilot_stuck_timer = 0.0
        self._maze_autopilot_last_pos = None
        self._maze_autopilot_last_drive = (0.0, 0.0)
        self.maze_autopilot_active = (
            self._maze_autopilot_available()
            and self._maze_autopilot_can_run_now()
        )
        if self.maze_autopilot_active:
            self.notif_text = "AUTO KEY PILOT ONLINE"
            self.notif_color = (120, 255, 170)
            self.notif_timer = max(getattr(self, "notif_timer", 0.0), 1.4)

    def _maze_autopilot_handoff(self, text: str | None = None) -> None:
        was_active = bool(getattr(self, "maze_autopilot_active", False))
        self.maze_autopilot_active = False
        self._maze_autopilot_path = []
        self._maze_autopilot_target_kind = None
        self._maze_autopilot_target_id = None
        self._maze_autopilot_aim = None
        self._maze_autopilot_fire_special = False
        self._maze_autopilot_stuck_timer = 0.0
        self._maze_autopilot_last_pos = None
        self._maze_autopilot_last_drive = (0.0, 0.0)
        self.mouse_held = False
        self.fire_timer = 0.0
        if was_active and text:
            self.notif_text = text
            self.notif_color = (120, 255, 170)
            self.notif_timer = max(getattr(self, "notif_timer", 0.0), 1.6)

    def _maze_autopilot_remaining_keys(self) -> list[dict]:
        return [
            key for key in getattr(self, "maze_keys", [])
            if not key.get("collected", False)
        ]

    def _maze_autopilot_push_decision_cache(self) -> None:
        depth = int(getattr(self, "_maze_autopilot_decision_depth", 0))
        if depth <= 0:
            if not isinstance(getattr(self, "_maze_autopilot_path_cache", None), dict):
                self._maze_autopilot_path_cache = {}
            self._maze_autopilot_breach_savings_cache = {}
            self._maze_autopilot_threat_cache = {}
            depth = 0
        self._maze_autopilot_decision_depth = depth + 1

    def _maze_autopilot_pop_decision_cache(self) -> None:
        depth = max(0, int(getattr(self, "_maze_autopilot_decision_depth", 0)) - 1)
        self._maze_autopilot_decision_depth = depth
        if depth == 0:
            self._maze_autopilot_breach_savings_cache = {}
            self._maze_autopilot_threat_cache = {}

    def _maze_autopilot_decision_cache_active(self) -> bool:
        return int(getattr(self, "_maze_autopilot_decision_depth", 0)) > 0

    def _maze_autopilot_has_breach_tool(self) -> bool:
        p = getattr(self, "player", None)
        return bool(
            p is not None
            and (
                getattr(p, "breach_active", False)
                or p.inventory.get("breach", 0) > 0
            )
        )

    def _maze_autopilot_breach_wall_budget(self, bonus_charges: int = 0) -> int:
        p = getattr(self, "player", None)
        if p is None:
            return 0
        charges = max(0, int(p.inventory.get("breach", 0))) + max(0, int(bonus_charges))
        if getattr(p, "breach_active", False):
            charges += 1
        return min(9, charges * 3)

    @staticmethod
    def _maze_autopilot_step_direction(col: int, row: int,
                                       next_col: int, next_row: int) -> int | None:
        for direction in (MazeGrid.N, MazeGrid.E, MazeGrid.S, MazeGrid.W):
            if (
                col + MazeGrid.DX[direction] == next_col
                and row + MazeGrid.DY[direction] == next_row
            ):
                return direction
        return None

    def _maze_autopilot_shortest_path(
        self,
        sc: int,
        sr: int,
        ec: int,
        er: int,
        allow_breakable: bool | None = None,
        bonus_breach_charges: int = 0,
        max_breakable_walls: int | None = None,
    ) -> tuple[list[tuple[int, int]], int, float]:
        maze = getattr(self, "maze_grid", None)
        if maze is None:
            return [], 0, math.inf
        if not (0 <= sc < maze.cols and 0 <= sr < maze.rows):
            return [], 0, math.inf
        if not (0 <= ec < maze.cols and 0 <= er < maze.rows):
            return [], 0, math.inf
        if (sc, sr) == (ec, er):
            return [], 0, 0.0

        breach_budget = self._maze_autopilot_breach_wall_budget(bonus_breach_charges)
        if max_breakable_walls is not None:
            breach_budget = max(0, min(breach_budget, int(max_breakable_walls)))
        if allow_breakable is None:
            allow_breakable = breach_budget > 0
        if not allow_breakable:
            breach_budget = 0

        cache_key = (sc, sr, ec, er, bool(allow_breakable), int(breach_budget))
        cache = getattr(self, "_maze_autopilot_path_cache", None)
        if isinstance(cache, dict) and cache_key in cache:
            cached_path, cached_breaks, cached_cost = cache[cache_key]
            return list(cached_path), cached_breaks, cached_cost

        start = (sc, sr, 0)
        costs = {start: 0.0}
        previous: dict[tuple[int, int, int], tuple[int, int, int] | None] = {start: None}
        heuristic = lambda col, row: abs(col - ec) + abs(row - er)
        heap: list[tuple[float, float, int, int, int, int]] = [
            (float(heuristic(sc, sr)), 0.0, 0, 0, sc, sr)
        ]
        sequence = 0
        best_target: tuple[int, int, int] | None = None

        while heap:
            _priority, cost, breaks_used, _seq, col, row = heapq.heappop(heap)
            state = (col, row, breaks_used)
            if cost > costs.get(state, math.inf) + 0.000001:
                continue
            if (col, row) == (ec, er):
                best_target = state
                break

            for direction in (MazeGrid.N, MazeGrid.E, MazeGrid.S, MazeGrid.W):
                nc = col + MazeGrid.DX[direction]
                nr = row + MazeGrid.DY[direction]
                if not (0 <= nc < maze.cols and 0 <= nr < maze.rows):
                    continue

                extra_breaks = 0
                step_cost = 1.0
                if maze.is_open(col, row, direction):
                    pass
                elif allow_breakable and maze.is_breakable_wall(col, row, direction):
                    extra_breaks = 1
                    if breaks_used + extra_breaks > breach_budget:
                        continue
                    wall_hp = max(1, maze.wall_hp(col, row, direction))
                    step_cost += wall_hp * 0.12 + (breaks_used + extra_breaks) * 0.15
                else:
                    continue

                next_breaks = breaks_used + extra_breaks
                next_state = (nc, nr, next_breaks)
                next_cost = cost + step_cost
                if next_cost + 0.000001 >= costs.get(next_state, math.inf):
                    continue
                costs[next_state] = next_cost
                previous[next_state] = state
                sequence += 1
                heapq.heappush(
                    heap,
                    (next_cost + heuristic(nc, nr), next_cost, next_breaks, sequence, nc, nr),
                )

        if best_target is None:
            if isinstance(cache, dict):
                cache[cache_key] = ((), 0, math.inf)
            return [], 0, math.inf

        path: list[tuple[int, int]] = []
        cur = best_target
        while previous[cur] is not None:
            path.append((cur[0], cur[1]))
            cur = previous[cur]
        path.reverse()
        result = (tuple(path), best_target[2], costs[best_target])
        if isinstance(cache, dict):
            if len(cache) > 1024:
                cache.clear()
            cache[cache_key] = result
        return list(result[0]), result[1], result[2]

    def _maze_autopilot_breach_route_savings(self, bonus_breach_charges: int = 1) -> float:
        pc, pr = self._maze_player_cell()
        cache = (
            getattr(self, "_maze_autopilot_breach_savings_cache", None)
            if self._maze_autopilot_decision_cache_active()
            else None
        )
        keys_signature = tuple(
            (int(key.get("id", idx)), int(key.get("col", 0)), int(key.get("row", 0)))
            for idx, key in enumerate(self._maze_autopilot_remaining_keys())
        )
        cache_key = (pc, pr, int(bonus_breach_charges), keys_signature)
        if isinstance(cache, dict) and cache_key in cache:
            return cache[cache_key]

        best_saving = 0.0
        for _key_id, key_col, key_row in keys_signature:
            open_path, _open_breaks, open_cost = self._maze_autopilot_shortest_path(
                pc, pr, key_col, key_row,
                allow_breakable=False,
            )
            shortcut, breaks_used, shortcut_cost = self._maze_autopilot_shortest_path(
                pc, pr, key_col, key_row,
                allow_breakable=True,
                bonus_breach_charges=bonus_breach_charges,
            )
            if not shortcut or breaks_used <= 0:
                continue
            open_cost = open_cost if open_path else len(shortcut) + 10.0
            best_saving = max(best_saving, open_cost - shortcut_cost)
        best_saving = max(0.0, best_saving)
        if isinstance(cache, dict):
            cache[cache_key] = best_saving
        return best_saving

    def _maze_autopilot_next_breakable_wall(
        self, path: list[tuple[int, int]] | None
    ) -> tuple[int, int, int] | None:
        if not path:
            return None
        pc, pr = self._maze_player_cell()
        target_col, target_row = path[0]
        direction = self._maze_autopilot_step_direction(pc, pr, target_col, target_row)
        if direction is None:
            return None
        if self.maze_grid.is_open(pc, pr, direction):
            return None
        if not self.maze_grid.is_breakable_wall(pc, pr, direction):
            return None
        return pc, pr, direction

    def _maze_autopilot_wall_aim_point(
        self, col: int, row: int, direction: int
    ) -> tuple[float, float]:
        cx, cy = self._maze_key_world(col, row)
        return (
            cx + MazeGrid.DX[direction] * self.maze_cell_size * 0.52,
            cy + MazeGrid.DY[direction] * self.maze_cell_size * 0.52,
        )

    def _maze_autopilot_choose_key_path(self) -> tuple[dict | None, list[tuple[int, int]]]:
        needs_cache_scope = not self._maze_autopilot_decision_cache_active()
        if needs_cache_scope:
            self._maze_autopilot_push_decision_cache()
        try:
            return self._maze_autopilot_choose_key_path_cached()
        finally:
            if needs_cache_scope:
                self._maze_autopilot_pop_decision_cache()

    def _maze_autopilot_choose_key_path_cached(self) -> tuple[dict | None, list[tuple[int, int]]]:
        pc, pr = self._maze_player_cell()
        keys = self._maze_autopilot_remaining_keys()
        if not keys:
            return None, []
        for key in keys:
            if (key["col"], key["row"]) == (pc, pr):
                return key, []

        best_route = None
        breach_budget = self._maze_autopilot_breach_wall_budget()
        # Only three keys are active, so checking every order is cheap and gives
        # the shortest remaining key route instead of a greedy nearest-key route.
        for order in itertools.permutations(keys):
            cur_col, cur_row = pc, pr
            first = order[0]
            first_path: list[tuple[int, int]] = []
            total_cost = 0.0
            total_breaks = 0
            route_ok = True
            for index, next_key in enumerate(order):
                remaining_breaks = breach_budget - total_breaks
                leg, leg_breaks, leg_cost = self._maze_autopilot_shortest_path(
                    cur_col, cur_row,
                    next_key["col"], next_key["row"],
                    max_breakable_walls=remaining_breaks,
                )
                if not leg and (cur_col, cur_row) != (next_key["col"], next_key["row"]):
                    route_ok = False
                    break
                total_breaks += leg_breaks
                total_cost += leg_cost
                if index == 0:
                    first_path = leg
                cur_col, cur_row = next_key["col"], next_key["row"]
            if route_ok and (best_route is None or total_cost < best_route[0]):
                best_route = (total_cost, first, first_path)

        if best_route is None:
            return None, []
        return best_route[1], best_route[2]

    def _maze_autopilot_powerup_cell(self, pu: Powerup) -> tuple[int, int]:
        ox, oy = self.maze_origin
        cs = self.maze_cell_size
        col = max(0, min(self.maze_grid.cols - 1, int((pu.center_x - ox) / cs)))
        row = max(0, min(self.maze_grid.rows - 1, int((pu.center_y - oy) / cs)))
        return col, row

    def _maze_autopilot_collectible_powerups(self) -> list[Powerup]:
        return [
            pu for pu in getattr(self, "powerups", [])
            if getattr(pu, "life", 0.0) > 0.9
        ]

    def _maze_autopilot_current_powerup(self) -> Powerup | None:
        if getattr(self, "_maze_autopilot_target_kind", None) != "powerup":
            return None
        target_id = getattr(self, "_maze_autopilot_target_id", None)
        for pu in self._maze_autopilot_collectible_powerups():
            if id(pu) == target_id:
                return pu
        return None

    def _maze_autopilot_powerup_value(self, pu: Powerup, path_len: int) -> float:
        p = self.player
        kind = getattr(pu, "kind", "")
        speed = max(1.0, self._maze_player_move_speed())
        eta = path_len * self.maze_cell_size / speed
        if getattr(pu, "life", 0.0) < eta + 0.75:
            return 0.0

        if kind == "beam360" and self.selected_ship not in BEAM_SHIP_INDICES:
            return 0.0
        if kind == "elec360" and self.selected_ship not in ELECTRIC_SHIP_INDICES:
            return 0.0

        if kind in ("health", "maze_health"):
            missing_ratio = max(0.0, (p.max_health - p.health) / max(1, p.max_health))
            if missing_ratio <= 0.03:
                return 2.0 if path_len <= 2 else 0.0
            return 7.5 + missing_ratio * 8.0

        if kind == "maze_speed":
            return 3.0 if getattr(p, "speed_active", False) else 5.0

        if kind in POWERUP_TYPES:
            limit = self._powerup_storage_limit(kind)
            stored = p.inventory.get(kind, 0)
            active = getattr(p, f"{kind}_active", False)
            if stored >= limit and kind in ("breach", "elec360"):
                return 0.0
            if stored >= limit and active:
                return 0.0

        close_threats = self._maze_autopilot_nearby_threat_count(self.maze_cell_size * 1.5)
        surrounded = self._maze_autopilot_nearby_threat_count(self.maze_cell_size * 2.4)
        health_ratio = p.health / max(1, p.max_health)

        if kind == "shield":
            return 9.5 if health_ratio <= 0.65 or close_threats >= 2 else 5.0
        if kind == "speed":
            return 2.5 if getattr(p, "speed_active", False) else 4.5
        if kind == "triple":
            return 6.0 if close_threats else 3.8
        if kind == "breach":
            shortcut_savings = self._maze_autopilot_breach_route_savings(
                bonus_breach_charges=1)
            if shortcut_savings >= 1.0:
                return 6.0 + min(8.0, shortcut_savings * 0.9)
            key, key_path = self._maze_autopilot_choose_key_path()
            return 5.2 if key is not None and len(key_path) >= 5 else 4.0
        if kind in ("beam360", "elec360"):
            return 8.5 if surrounded >= 3 else 5.5
        return 2.5

    def _maze_autopilot_choose_powerup_path(
        self, key_path_len: int | None = None
    ) -> tuple[Powerup | None, list[tuple[int, int]]]:
        needs_cache_scope = not self._maze_autopilot_decision_cache_active()
        if needs_cache_scope:
            self._maze_autopilot_push_decision_cache()
        try:
            return self._maze_autopilot_choose_powerup_path_cached(key_path_len)
        finally:
            if needs_cache_scope:
                self._maze_autopilot_pop_decision_cache()

    def _maze_autopilot_choose_powerup_path_cached(
        self, key_path_len: int | None = None
    ) -> tuple[Powerup | None, list[tuple[int, int]]]:
        pc, pr = self._maze_player_cell()
        keys_done = self.maze_keys_collected >= MAZE_KEYS_REQUIRED
        speed = max(1.0, self._maze_player_move_speed())
        health_ratio = self.player.health / max(1, self.player.max_health)
        candidates = []
        for pu in self._maze_autopilot_collectible_powerups():
            col, row = self._maze_autopilot_powerup_cell(pu)
            approx_steps = abs(col - pc) + abs(row - pr)
            eta = approx_steps * self.maze_cell_size / speed
            if getattr(pu, "life", 0.0) < eta * 0.55:
                continue
            kind = getattr(pu, "kind", "")
            pre_value = self._maze_autopilot_powerup_value(pu, max(1, approx_steps))
            if pre_value <= 0.0:
                continue
            if kind in ("health", "maze_health") and health_ratio < 0.45:
                pre_value += 4.0
            approx_score = pre_value - approx_steps * 0.42
            candidates.append((-approx_score, approx_steps, pre_value, pu, col, row))

        candidates.sort(key=lambda item: (item[0], item[1]))
        filtered_candidates = []
        for idx, item in enumerate(candidates):
            _rank, approx_steps, pre_value, pu, _col, _row = item
            kind = getattr(pu, "kind", "")
            near_key_route = (
                key_path_len is not None
                and approx_steps <= key_path_len + 5
                and pre_value >= 7.0
            )
            if idx < 10 or near_key_route or kind == "breach":
                filtered_candidates.append(item)
        if len(filtered_candidates) > 14:
            breach_candidates = [
                item for item in filtered_candidates
                if getattr(item[3], "kind", "") == "breach"
            ]
            other_candidates = [
                item for item in filtered_candidates
                if getattr(item[3], "kind", "") != "breach"
            ]
            filtered_candidates = (
                breach_candidates
                + other_candidates[:max(0, 14 - len(breach_candidates))]
            )[:14]

        best = None
        for _rank, _approx_steps, _pre_value, pu, col, row in filtered_candidates:
            if (col, row) == (pc, pr):
                path = [(col, row)]
                route_cost = 0.0
            else:
                path, _breaks_used, route_cost = self._maze_autopilot_shortest_path(
                    pc, pr, col, row,
                    allow_breakable=self._maze_autopilot_has_breach_tool(),
                )
                if not path:
                    continue
            px, py = self._maze_key_world(col, row)
            local_dist = math.hypot(pu.center_x - px, pu.center_y - py) / max(1, self.maze_cell_size)
            travel_steps = max(len(path), int(math.ceil(route_cost)))
            value = self._maze_autopilot_powerup_value(pu, travel_steps)
            if value <= 0.0:
                continue
            if not keys_done and key_path_len is not None:
                too_far_from_key = travel_steps > key_path_len + 4
                if too_far_from_key and value < 8.0:
                    continue
            travel_cost = route_cost * 0.85 + local_dist * 0.45
            score = value - travel_cost
            min_score = -0.5 if keys_done else 0.7
            if score < min_score:
                continue
            if best is None or score > best[0]:
                best = (score, pu, path)
        if best is None:
            return None, []
        return best[1], best[2]

    def _maze_autopilot_choose_objective(self) -> tuple[str | None, object | None, list[tuple[int, int]]]:
        self._maze_autopilot_push_decision_cache()
        try:
            key, key_path = self._maze_autopilot_choose_key_path_cached()
            key_path_len = len(key_path) if key is not None else None
            pu, pu_path = self._maze_autopilot_choose_powerup_path_cached(key_path_len)
            if pu is not None:
                return "powerup", pu, pu_path
            if key is not None:
                return "key", key, key_path
            return None, None, []
        finally:
            self._maze_autopilot_pop_decision_cache()

    def _maze_autopilot_current_key(self) -> dict | None:
        if getattr(self, "_maze_autopilot_target_kind", None) != "key":
            return None
        target_id = getattr(self, "_maze_autopilot_target_id", None)
        for key in getattr(self, "maze_keys", []):
            if key.get("id") == target_id and not key.get("collected", False):
                return key
        return None

    def _maze_autopilot_trim_current_path(
        self, path: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        if not path:
            return []
        pc, pr = self._maze_player_cell()
        while path and path[0] == (pc, pr):
            path = path[1:]
        return path

    def _maze_autopilot_targets(self) -> list:
        return [
            target for target in (
                list(getattr(self, "maze_enemies", []))
                + list(self._active_maze_bosses())
            )
            if getattr(target, "health", 1) > 0
        ]

    def _maze_autopilot_line_clear(self, tx: float, ty: float, slack: float = 18.0) -> bool:
        p = self.player
        dx = tx - p.center_x
        dy = ty - p.center_y
        dist = math.hypot(dx, dy)
        if dist <= 1.0:
            return True
        angle = math.atan2(dy, dx)
        open_length, _wall_hit, _hit_x, _hit_y = self._maze_ray_wall_contact(
            p.center_x, p.center_y, angle, dist)
        return open_length + slack >= dist

    def _maze_autopilot_front_target(self, forward_x: float,
                                     forward_y: float) -> tuple[float, float] | None:
        p = self.player
        f_len = math.hypot(forward_x, forward_y)
        if f_len <= 0.001:
            return None
        fx = forward_x / f_len
        fy = forward_y / f_len
        max_dist = self.maze_cell_size * 4.5
        cone_dot = math.cos(math.radians(42.0))
        best = None
        for target in self._maze_autopilot_targets():
            dx = target.center_x - self.player.center_x
            dy = target.center_y - self.player.center_y
            dist_sq = dx * dx + dy * dy
            if dist_sq <= 1.0 or dist_sq > max_dist * max_dist:
                continue
            dist = math.sqrt(dist_sq)
            dot = (dx * fx + dy * fy) / dist
            if dot < cone_dot:
                continue
            if not self._maze_autopilot_line_clear(target.center_x, target.center_y):
                continue
            score = dot * 2.0 - dist / max_dist
            if best is None or score > best[0]:
                best = (score, target)
        if best is None:
            return None
        target = best[1]
        return target.center_x, target.center_y

    def _maze_autopilot_visible_threat_target(
        self, radius: float, forward_x: float = 0.0, forward_y: float = 0.0
    ) -> tuple[float, float] | None:
        p = self.player
        radius_sq = radius * radius
        f_len = math.hypot(forward_x, forward_y)
        fx = forward_x / f_len if f_len > 0.001 else 0.0
        fy = forward_y / f_len if f_len > 0.001 else 0.0
        best = None
        for target in self._maze_autopilot_targets():
            dx = target.center_x - p.center_x
            dy = target.center_y - p.center_y
            dist_sq = dx * dx + dy * dy
            if dist_sq <= 1.0 or dist_sq > radius_sq:
                continue
            if not self._maze_autopilot_line_clear(target.center_x, target.center_y, slack=24.0):
                continue
            dist = math.sqrt(dist_sq)
            forward_bonus = 0.0
            if f_len > 0.001:
                forward_bonus = max(0.0, (dx * fx + dy * fy) / dist) * 0.45
            health_ratio = max(0.0, min(1.0, getattr(target, "health", 1.0) / max(1.0, getattr(target, "max_health", 1.0))))
            score = (1.0 - dist / max(1.0, radius)) + forward_bonus + (1.0 - health_ratio) * 0.25
            if best is None or score > best[0]:
                best = (score, target)
        if best is None:
            return None
        target = best[1]
        return target.center_x, target.center_y

    def _maze_autopilot_nearby_threat_count(self, radius: float) -> int:
        cache = (
            getattr(self, "_maze_autopilot_threat_cache", None)
            if self._maze_autopilot_decision_cache_active()
            else None
        )
        cache_key = round(float(radius), 1)
        if isinstance(cache, dict) and cache_key in cache:
            return cache[cache_key]
        p = self.player
        radius_sq = radius * radius
        count = 0
        for target in self._maze_autopilot_targets():
            dx = target.center_x - p.center_x
            dy = target.center_y - p.center_y
            if dx * dx + dy * dy <= radius_sq:
                count += 1
        for bullet in getattr(self, "maze_enemy_bullets", []):
            dx = bullet.center_x - p.center_x
            dy = bullet.center_y - p.center_y
            if dx * dx + dy * dy <= radius_sq:
                count += 1
        if isinstance(cache, dict):
            cache[cache_key] = count
        return count

    def _maze_autopilot_breach_target(
        self,
        key: dict | None,
        path_len: int,
        path: list[tuple[int, int]] | None = None,
    ) -> tuple[float, float] | None:
        p = self.player
        if not self._maze_autopilot_has_breach_tool():
            return None

        next_wall = self._maze_autopilot_next_breakable_wall(path)
        if next_wall is not None:
            return self._maze_autopilot_wall_aim_point(*next_wall)

        if key is None or path_len < 5:
            return None
        tx, ty = self._maze_key_world(key["col"], key["row"])
        dx = tx - p.center_x
        dy = ty - p.center_y
        dist = math.hypot(dx, dy)
        if dist <= self.maze_cell_size * 0.8:
            return None
        angle = math.atan2(dy, dx)
        open_length, wall_hit, hit_x, hit_y = self._maze_ray_wall_contact(
            p.center_x, p.center_y, angle, min(dist, self.maze_cell_size * 3.5))
        if wall_hit is None:
            return None
        col, row, direction = wall_hit
        if not self.maze_grid.is_breakable_wall(col, row, direction):
            return None
        if open_length > self.maze_cell_size * 2.9:
            return None
        return hit_x, hit_y

    def _maze_autopilot_use_powerups(self, delta: float,
                                     front_target: tuple[float, float] | None,
                                     path_len: int,
                                     breach_target: tuple[float, float] | None) -> None:
        p = self.player
        self._maze_autopilot_powerup_timer = max(
            0.0, getattr(self, "_maze_autopilot_powerup_timer", 0.0) - delta)
        if self._maze_autopilot_powerup_timer > 0.0:
            return

        def use(kind: str) -> bool:
            if p.inventory.get(kind, 0) <= 0 or getattr(p, f"{kind}_active", False):
                return False
            self._use_stored_powerup(kind)
            self._maze_autopilot_powerup_timer = 0.45
            return True

        health_ratio = p.health / max(1, p.max_health)
        close_threats = self._maze_autopilot_nearby_threat_count(self.maze_cell_size * 1.35)
        if (health_ratio <= 0.58 or close_threats >= 3) and use("shield"):
            return

        surrounded = self._maze_autopilot_nearby_threat_count(self.maze_cell_size * 2.2)
        if surrounded >= 4:
            if self.selected_ship in BEAM_SHIP_INDICES and use("beam360"):
                return
            if self.selected_ship in ELECTRIC_SHIP_INDICES and use("elec360"):
                return

        if front_target is not None and use("triple"):
            return

        if breach_target is not None:
            if use("breach"):
                return

        if path_len >= 4 and close_threats == 0:
            use("speed")

    def _maze_autopilot_drive(self, delta: float, p: Player, cs: int) -> tuple[float, float] | None:
        if not getattr(self, "maze_autopilot_active", False):
            return None
        if not self._maze_autopilot_available():
            self._maze_autopilot_handoff()
            return None
        if (self.maze_keys_collected >= MAZE_KEYS_REQUIRED
                and not self._maze_autopilot_collectible_powerups()):
            self._maze_autopilot_handoff("AUTO KEY PILOT COMPLETE - MANUAL CONTROL")
            return None

        last_pos = getattr(self, "_maze_autopilot_last_pos", None)
        last_drive = getattr(self, "_maze_autopilot_last_drive", (0.0, 0.0))
        breaching = bool(getattr(p, "breach_active", False) and getattr(self, "_maze_autopilot_aim", None))
        if last_pos is not None and math.hypot(*last_drive) > 0.1 and not breaching:
            moved = math.hypot(p.center_x - last_pos[0], p.center_y - last_pos[1])
            if moved < max(0.8, cs * 0.01):
                self._maze_autopilot_stuck_timer = getattr(
                    self, "_maze_autopilot_stuck_timer", 0.0) + delta
            else:
                self._maze_autopilot_stuck_timer = 0.0
        else:
            self._maze_autopilot_stuck_timer = 0.0
        self._maze_autopilot_last_pos = (p.center_x, p.center_y)
        if getattr(self, "_maze_autopilot_stuck_timer", 0.0) > 0.18:
            self._maze_autopilot_repath_timer = 0.0

        self._maze_autopilot_repath_timer = max(
            0.0, getattr(self, "_maze_autopilot_repath_timer", 0.0) - delta)
        current_target_collected = False
        target_kind = getattr(self, "_maze_autopilot_target_kind", None)
        target_id = getattr(self, "_maze_autopilot_target_id", None)
        if target_kind == "powerup":
            current_target_collected = self._maze_autopilot_current_powerup() is None
        elif target_kind == "key":
            current_target_collected = True
            for key in getattr(self, "maze_keys", []):
                if key.get("id") == target_id:
                    current_target_collected = key.get("collected", False)
                    break
        if (self._maze_autopilot_repath_timer <= 0.0
                or current_target_collected
                or not getattr(self, "_maze_autopilot_path", [])):
            target_kind, target, path = self._maze_autopilot_choose_objective()
            if target is None:
                self._maze_autopilot_handoff("AUTO KEY PILOT COMPLETE - MANUAL CONTROL")
                return None
            self._maze_autopilot_target_kind = target_kind
            if target_kind == "powerup":
                self._maze_autopilot_target_id = id(target)
            else:
                self._maze_autopilot_target_id = target.get("id")
            self._maze_autopilot_path = self._maze_autopilot_trim_current_path(list(path))
            self._maze_autopilot_repath_timer = 0.12

        path = self._maze_autopilot_trim_current_path(getattr(self, "_maze_autopilot_path", []))
        self._maze_autopilot_path = path
        current_powerup = self._maze_autopilot_current_powerup()
        if current_powerup is None and getattr(self, "_maze_autopilot_target_kind", None) == "powerup":
            self._maze_autopilot_repath_timer = 0.0
            self._maze_autopilot_last_drive = (0.0, 0.0)
            return 0.0, 0.0

        if not path:
            if current_powerup is not None:
                tx, ty = current_powerup.center_x, current_powerup.center_y
                dx = tx - p.center_x
                dy = ty - p.center_y
                dist = math.hypot(dx, dy)
                front_target = self._maze_autopilot_front_target(dx, dy)
                if front_target is None and self._maze_autopilot_nearby_threat_count(cs * 1.9) > 0:
                    front_target = self._maze_autopilot_visible_threat_target(cs * 3.0, dx, dy)
                self._maze_autopilot_aim = front_target
                self._maze_autopilot_fire_special = (
                    front_target is None
                    and (p.beam360_active or p.elec360_active)
                    and self._maze_autopilot_nearby_threat_count(cs * 2.2) > 0
                )
                self._maze_autopilot_use_powerups(delta, front_target, 0, None)
                if dist <= 2.0:
                    self._maze_autopilot_last_drive = (0.0, 0.0)
                    return 0.0, 0.0
                move = (dx / dist, dy / dist)
                self._maze_autopilot_last_drive = move
                return move
            key, path = self._maze_autopilot_choose_key_path()
            if key is None:
                self._maze_autopilot_handoff("AUTO KEY PILOT COMPLETE - MANUAL CONTROL")
                return None
            self._maze_autopilot_target_kind = "key"
            self._maze_autopilot_target_id = key.get("id")
            self._maze_autopilot_path = self._maze_autopilot_trim_current_path(list(path))
            self._maze_autopilot_repath_timer = 0.12
            front_target = self._maze_autopilot_front_target(p.change_x, p.change_y)
            if front_target is None and self._maze_autopilot_nearby_threat_count(cs * 1.9) > 0:
                front_target = self._maze_autopilot_visible_threat_target(cs * 3.0, p.change_x, p.change_y)
            self._maze_autopilot_aim = front_target
            self._maze_autopilot_fire_special = (
                front_target is None
                and (p.beam360_active or p.elec360_active)
                and self._maze_autopilot_nearby_threat_count(cs * 2.2) > 0
            )
            self._maze_autopilot_use_powerups(delta, front_target, 0, None)
            self._maze_autopilot_last_drive = (0.0, 0.0)
            return 0.0, 0.0

        target_col, target_row = path[0]
        tx, ty = self._maze_key_world(target_col, target_row)
        pc, pr = self._maze_player_cell()
        if current_powerup is not None and (target_col, target_row) == (pc, pr):
            tx, ty = current_powerup.center_x, current_powerup.center_y
        if (target_col, target_row) != (pc, pr):
            cx, cy = self._maze_key_world(pc, pr)
            if target_col != pc and target_row == pr:
                ty = cy
            elif target_row != pr and target_col == pc:
                tx = cx
        dx = tx - p.center_x
        dy = ty - p.center_y
        dist = math.hypot(dx, dy)
        close_enough = max(12.0, cs * 0.07)
        if dist < close_enough and len(path) > 1:
            self._maze_autopilot_path = path[1:]
            path = self._maze_autopilot_path
            target_col, target_row = self._maze_autopilot_path[0]
            tx, ty = self._maze_key_world(target_col, target_row)
            pc, pr = self._maze_player_cell()
            if current_powerup is not None and (target_col, target_row) == (pc, pr):
                tx, ty = current_powerup.center_x, current_powerup.center_y
            if (target_col, target_row) != (pc, pr):
                cx, cy = self._maze_key_world(pc, pr)
                if target_col != pc and target_row == pr:
                    ty = cy
                elif target_row != pr and target_col == pc:
                    tx = cx
            dx = tx - p.center_x
            dy = ty - p.center_y
            dist = math.hypot(dx, dy)

        if dist > 1.0:
            forward_x, forward_y = dx, dy
        else:
            forward_x, forward_y = p.change_x, p.change_y
        immediate_wall = self._maze_autopilot_next_breakable_wall(path)
        if immediate_wall is not None and not self._maze_autopilot_has_breach_tool():
            self._maze_autopilot_repath_timer = 0.0
            self._maze_autopilot_last_drive = (0.0, 0.0)
            return 0.0, 0.0
        front_target = None if immediate_wall is not None else self._maze_autopilot_front_target(
            forward_x, forward_y)
        if front_target is None and immediate_wall is None and self._maze_autopilot_nearby_threat_count(cs * 1.9) > 0:
            front_target = self._maze_autopilot_visible_threat_target(cs * 3.0, forward_x, forward_y)
        target_key = self._maze_autopilot_current_key()
        breach_target = None if front_target is not None else self._maze_autopilot_breach_target(
            target_key, len(path), path)
        self._maze_autopilot_use_powerups(delta, front_target, len(path), breach_target)
        self._maze_autopilot_aim = front_target or breach_target
        self._maze_autopilot_fire_special = (
            self._maze_autopilot_aim is None
            and (p.beam360_active or p.elec360_active)
            and self._maze_autopilot_nearby_threat_count(cs * 2.2) > 0
        )
        if dist <= 1.0:
            self._maze_autopilot_last_drive = (0.0, 0.0)
            return 0.0, 0.0
        move = (dx / dist, dy / dist)
        self._maze_autopilot_last_drive = move
        return move

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
        player_cell = self._maze_player_cell() if self.player is not None else start
        min_player_dist = max(10, min(24, (maze.cols + maze.rows) // 4))
        min_exit_dist = 6

        for _ in range(900):
            col = random.randint(0, maze.cols - 1)
            row = random.randint(0, maze.rows - 1)
            if (col, row) in reserved:
                continue
            if abs(col - player_cell[0]) + abs(row - player_cell[1]) < min_player_dist:
                continue
            if abs(col - exit_cell[0]) + abs(row - exit_cell[1]) < min_exit_dist:
                continue
            return col, row

        candidates = []
        for row in range(maze.rows):
            for col in range(maze.cols):
                if (col, row) in reserved:
                    continue
                exit_dist = abs(col - exit_cell[0]) + abs(row - exit_cell[1])
                if exit_dist < min_exit_dist:
                    continue
                player_dist = abs(col - player_cell[0]) + abs(row - player_cell[1])
                candidates.append((player_dist, random.random(), col, row))

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][2], candidates[0][3]

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

    def _spawn_maze_key_enemies(self) -> int:
        """Seed each key with a nearby cluster of maze enemies."""
        maze = self.maze_grid
        if maze is None:
            return 0

        max_enemies = self._maze_enemy_cap()
        reserved = {
            (0, maze.rows - 1),
            (self.maze_exit_col, self.maze_exit_row),
            self._maze_player_cell(),
        }
        for key in getattr(self, "maze_keys", []):
            if not key.get("collected", False):
                reserved.add((key["col"], key["row"]))
        for enemy in getattr(self, "maze_enemies", []):
            reserved.add((enemy.maze_col, enemy.maze_row))

        active_keys = [
            key for key in getattr(self, "maze_keys", [])
            if not key.get("collected", False)
        ]
        if not active_keys:
            return 0

        target_total = min(max_enemies, self._maze_initial_enemy_target())
        base_per_key, extra_per_key = divmod(target_total, len(active_keys))

        spawned_total = 0
        for key_index, key in enumerate(active_keys):
            key_col = key["col"]
            key_row = key["row"]
            target_for_key = base_per_key + (1 if key_index < extra_per_key else 0)
            candidates = []
            for row in range(maze.rows):
                for col in range(maze.cols):
                    cell = (col, row)
                    if cell in reserved:
                        continue
                    dist = abs(col - key_col) + abs(row - key_row)
                    if dist == 0:
                        continue
                    candidates.append((dist, random.random(), col, row))

            candidates.sort()
            spawned_for_key = 0
            for _dist, _roll, col, row in candidates:
                if (spawned_for_key >= target_for_key
                        or len(self.maze_enemies) >= max_enemies):
                    break
                cell = (col, row)
                if cell in reserved:
                    continue
                if self._spawn_maze_enemy_at(col, row):
                    reserved.add(cell)
                    spawned_for_key += 1
                    spawned_total += 1

        return spawned_total

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
        self._maze_autopilot_repath_timer = 0.0
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
            self._maze_autopilot_repath_timer = 0.0
            if getattr(self, "_multiplayer_is_client_world", lambda: False)():
                if hasattr(self, "_queue_multiplayer_event"):
                    self._queue_multiplayer_event({
                        "type": "key_collect",
                        "key_id": int(key.get("id", 0)),
                    })
            elif self.maze_keys_collected >= MAZE_KEYS_REQUIRED:
                self._spawn_maze_boss()
                if self._maze_autopilot_collectible_powerups():
                    self._maze_autopilot_repath_timer = 0.0
                else:
                    self._maze_autopilot_handoff("AUTO KEY PILOT COMPLETE - MANUAL CONTROL")
            break

    def _maze_boss_spawn_cell(self) -> tuple[int, int]:
        pc, pr = self._maze_player_cell()
        exit_cell = (self.maze_exit_col, self.maze_exit_row)
        if exit_cell != (pc, pr):
            return exit_cell

        farthest = (0, random.random(), exit_cell[0], exit_cell[1])
        for row in range(self.maze_grid.rows):
            for col in range(self.maze_grid.cols):
                dist = abs(col - pc) + abs(row - pr)
                farthest = max(farthest, (dist, random.random(), col, row))
        return farthest[2], farthest[3]

    def _active_maze_bosses(self) -> list[MazeBoss]:
        bosses = getattr(self, "maze_bosses", None)
        if bosses is None:
            boss = getattr(self, "maze_boss", None)
            bosses = [boss] if boss is not None else []
            self.maze_bosses = bosses
        else:
            bosses[:] = [boss for boss in bosses if boss is not None]

        self.maze_boss = bosses[0] if bosses else None
        return bosses

    def _spawn_maze_boss(self) -> bool:
        if getattr(self, "maze_boss_spawned", False) or self._active_maze_bosses():
            return False

        col, row = self._maze_boss_spawn_cell()
        hp = int(MAZE_BOSS_HEALTH)
        self.maze_boss = MazeBoss(col, row, self.maze_cell_size, *self.maze_origin, health=hp)
        if hasattr(self, "_assign_maze_enemy_id"):
            self._assign_maze_enemy_id(self.maze_boss)
        self.maze_bosses = [self.maze_boss]
        self.maze_boss_spawned = True
        self.boss_on_screen = True
        dx = self.player.center_x - self.maze_boss.center_x
        dy = self.player.center_y - self.maze_boss.center_y
        self.maze_boss.angle = self._maze_player_angle_from_motion(dx, dy)
        self._burst(self.maze_boss.center_x, self.maze_boss.center_y, 48,
                    (255, 210, 90), 90, 320, 2.0, 4.6, .12, .34)
        self.notif_text = (
            "FINAL MISSION: DEFEAT THE BOSS!"
            if self._maze_is_final_floor()
            else "MAZE BOSS ARRIVED!  DEFEAT IT TO FINISH!"
        )
        self.notif_color = (255, 210, 90)
        self.notif_timer = 2.0
        return True

    def _maze_boss_split_cells(self, boss: MazeBoss) -> list[tuple[int, int]]:
        maze = self.maze_grid
        cells = []
        for direction in (MazeGrid.N, MazeGrid.E, MazeGrid.S, MazeGrid.W):
            if not maze.is_open(boss.maze_col, boss.maze_row, direction):
                continue
            col = boss.maze_col + MazeGrid.DX[direction]
            row = boss.maze_row + MazeGrid.DY[direction]
            if 0 <= col < maze.cols and 0 <= row < maze.rows:
                cells.append((col, row))
        random.shuffle(cells)
        cells.insert(0, (boss.maze_col, boss.maze_row))
        while len(cells) < 2:
            cells.append((boss.maze_col, boss.maze_row))
        return cells[:2]

    def _maze_boss_next_step(self, boss: MazeBoss, pc: int, pr: int) -> tuple[int, int, int] | None:
        start = (boss.maze_col, boss.maze_row)
        target = (pc, pr)
        if start == target:
            return None

        from collections import deque
        maze = self.maze_grid
        prev = {start: None}
        q = deque([start])
        while q:
            col, row = q.popleft()
            if (col, row) == target:
                break
            for direction in (MazeGrid.N, MazeGrid.E, MazeGrid.S, MazeGrid.W):
                nc = col + MazeGrid.DX[direction]
                nr = row + MazeGrid.DY[direction]
                if not (0 <= nc < maze.cols and 0 <= nr < maze.rows):
                    continue
                if not (maze.is_open(col, row, direction)
                        or maze.is_breakable_wall(col, row, direction)):
                    continue
                if (nc, nr) in prev:
                    continue
                prev[(nc, nr)] = ((col, row), direction)
                q.append((nc, nr))

        if target not in prev:
            return None

        cur = target
        while prev[cur] is not None and prev[cur][0] != start:
            cur = prev[cur][0]
        if prev[cur] is None:
            return None
        return cur[0], cur[1], prev[cur][1]

    def _break_wall_for_maze_boss(self, boss: MazeBoss, direction: int) -> bool:
        maze = self.maze_grid
        if maze.is_open(boss.maze_col, boss.maze_row, direction):
            return True
        if not maze.is_breakable_wall(boss.maze_col, boss.maze_row, direction):
            return False

        damaged, broken, _hp_left = maze.damage_wall(
            boss.maze_col, boss.maze_row, direction, MAZE_BREAKABLE_WALL_HP)
        if damaged:
            if broken and isinstance(getattr(self, "_maze_autopilot_path_cache", None), dict):
                self._maze_autopilot_path_cache.clear()
            if broken and hasattr(self, "_remember_multiplayer_open_wall"):
                self._remember_multiplayer_open_wall(boss.maze_col, boss.maze_row, direction)
            self._maze_enemy_flow_target = None
            hx = boss.center_x + MazeGrid.DX[direction] * self.maze_cell_size * 0.48
            hy = boss.center_y + MazeGrid.DY[direction] * self.maze_cell_size * 0.48
            self._burst(hx, hy, 28, (255, 190, 80), 80, 260, 1.4, 3.0, .10, .24)
        return broken

    def _update_maze_boss(self, delta: float, p: Player, cs: int, ox: float, oy: float) -> None:
        bosses = self._active_maze_bosses()
        if not bosses:
            self.boss_on_screen = False
            return

        boss_speed = self._maze_player_base_move_speed()
        for boss in list(bosses):
            target_x, target_y = p.center_x, p.center_y
            pc, pr = self._maze_player_cell()
            if getattr(self, "_multiplayer_active", lambda: False)() and hasattr(self, "_closest_multiplayer_hero"):
                target = self._closest_multiplayer_hero(boss.center_x, boss.center_y)
                if target is not None:
                    target_x, target_y = target["x"], target["y"]
                    pc, pr = target["col"], target["row"]
            boss.speed = boss_speed
            step = self._maze_boss_next_step(boss, pc, pr)
            if step is not None:
                nc, nr, direction = step
                if self._break_wall_for_maze_boss(boss, direction):
                    tx = ox + (nc + 0.5) * cs
                    ty = oy + (nr + 0.5) * cs
                    dx = tx - boss.center_x
                    dy = ty - boss.center_y
                    dist = math.hypot(dx, dy)
                    if dist <= max(4.0, boss.speed * delta):
                        boss.center_x = tx
                        boss.center_y = ty
                        boss.maze_col = nc
                        boss.maze_row = nr
                    elif dist > 0:
                        boss.center_x += (dx / dist) * boss.speed * delta
                        boss.center_y += (dy / dist) * boss.speed * delta
                    boss.angle = self._maze_player_angle_from_motion(dx, dy)

            boss.shoot_timer -= delta
            while boss.shoot_timer <= 0:
                boss.shoot_timer += NORMAL_FIRE_RATE
                ang = math.atan2(target_y - boss.center_y, target_x - boss.center_x)
                bullet = Bullet(boss.center_x, boss.center_y, ang)
                bullet.scale = 1.0
                bullet.damage = MAZE_BOSS_SHOT_DAMAGE
                if hasattr(self, "_assign_maze_enemy_bullet_id"):
                    self._assign_maze_enemy_bullet_id(bullet)
                self.maze_enemy_bullets.append(bullet)

        self.boss_on_screen = True

    def _damage_maze_boss(self, boss: MazeBoss, amount: float, color: tuple) -> bool:
        if boss not in self._active_maze_bosses():
            return False
        if getattr(self, "_multiplayer_is_client_world", lambda: False)():
            boss_id = getattr(boss, "net_id", None)
            if boss_id is not None and hasattr(self, "_queue_multiplayer_event"):
                self._queue_multiplayer_event({
                    "type": "enemy_damage",
                    "enemy_id": int(boss_id),
                    "amount": float(amount),
                })
            boss.health -= amount
            self._burst(boss.center_x, boss.center_y, 8, color, 45, 150, 0.9, 2.0, .04, .12)
            if boss.health <= 0:
                bosses = self._active_maze_bosses()
                if boss in bosses:
                    bosses.remove(boss)
                self.maze_boss = bosses[0] if bosses else None
                self.boss_on_screen = bool(bosses)
            return True
        boss.health -= amount
        self._burst(boss.center_x, boss.center_y, 10, color, 55, 190, 1.2, 2.8, .06, .18)
        if boss.health <= 0:
            self._kill_maze_boss(boss)
        return True

    def _kill_maze_boss(self, boss: MazeBoss) -> None:
        bosses = self._active_maze_bosses()
        if boss not in bosses:
            return
        self.score += 450 + self._maze_legacy_level_index() * 30
        self._burst(boss.center_x, boss.center_y, 110,
                    (255, 120, 70), 90, 380, 2.4, 5.0, .18, .55)
        bosses.remove(boss)

        if boss.split_depth < MAZE_BOSS_MAX_SPLITS:
            child_hp = max(1, int(boss.max_health * 0.5))
            child_depth = boss.split_depth + 1
            split_cells = self._maze_boss_split_cells(boss)
            offsets = (-0.18, 0.18)
            for i, (col, row) in enumerate(split_cells):
                child = MazeBoss(
                    col, row, self.maze_cell_size, *self.maze_origin,
                    health=child_hp, split_depth=child_depth,
                )
                child.center_x += offsets[i] * self.maze_cell_size
                child.center_y += offsets[1 - i] * self.maze_cell_size
                child.shoot_timer = random.uniform(0.08, NORMAL_FIRE_RATE)
                if hasattr(self, "_assign_maze_enemy_id"):
                    self._assign_maze_enemy_id(child)
                dx = self.player.center_x - child.center_x
                dy = self.player.center_y - child.center_y
                child.angle = self._maze_player_angle_from_motion(dx, dy)
                bosses.append(child)
            self._burst(boss.center_x, boss.center_y, 64,
                        (255, 210, 90), 120, 430, 2.0, 4.6, .12, .34)
            self.notif_text = f"MAZE BOSS SPLIT!  {len(bosses)} BODIES"
            self.notif_color = (255, 210, 90)
            self.notif_timer = 1.5
        elif not bosses:
            self.maze_run_complete = True
            self.score += 5000
            self._clear_maze_resume_floor()
            self.notif_text = (
                "FINAL BOSS DEFEATED!"
                if self._maze_is_final_floor()
                else "MAZE BOSS DEFEATED!"
            )
            self.notif_color = (120, 255, 160)
            self.notif_timer = 2.0
            self.game_state = STATE_MAZE_OVER
            self.set_mouse_visible(True)

        self.maze_boss = bosses[0] if bosses else None
        self.boss_on_screen = bool(bosses)

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
        pu = Powerup(x, y, kind, maze_style=True)
        pu.change_y = 0
        pu.life = 60.0
        pu.scale = 1.35
        if hasattr(self, "_assign_maze_powerup_id"):
            self._assign_maze_powerup_id(pu)
        self.powerups.append(pu)
        if getattr(self, "maze_autopilot_active", False):
            self._maze_autopilot_repath_timer = 0.0
        glow = POWERUP_COLORS.get(kind, (255, 255, 255))[:3]
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

    def _maze_local_map_bounds(self, cols_visible: int, rows_visible: int) -> tuple[int, int, int, int]:
        """Return a player-centered map window as col_min, col_max, row_min, row_max."""
        maze = self.maze_grid
        pc, pr = self._maze_player_cell()
        view_cols = min(maze.cols, cols_visible)
        view_rows = min(maze.rows, rows_visible)

        col_min = pc - view_cols // 2
        row_min = pr - view_rows // 2
        col_min = max(0, min(maze.cols - view_cols, col_min))
        row_min = max(0, min(maze.rows - view_rows, row_min))
        return col_min, col_min + view_cols, row_min, row_min + view_rows

    def _maze_minimap_layout(self) -> tuple[int, int, int, int, int, int]:
        maze = self.maze_grid
        col_min, col_max, row_min, row_max = self._maze_local_map_bounds(11, 9)
        view_cols = col_max - col_min
        view_rows = row_max - row_min
        mm_cs = max(5, min(9, 90 // max(view_cols, view_rows)))
        mx = 16
        my = self.height - 185 - view_rows * mm_cs
        mw = view_cols * mm_cs
        mh = view_rows * mm_cs
        return mx, my, mw, mh, mm_cs, 8

    def _maze_minimap_hit(self, x: float, y: float) -> bool:
        mx, my, mw, mh, _mm_cs, pad = self._maze_minimap_layout()
        return mx - pad <= x <= mx + mw + pad and my - pad <= y <= my + mh + pad

    def _maze_team_map_markers(self) -> list[dict]:
        if self.player is None or self.maze_grid is None:
            return []

        def safe_float(value, fallback: float) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return fallback

        def safe_int(value, fallback: int = 0) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return fallback

        markers = []
        local_id = safe_int(getattr(self, "multiplayer_player_id", 0), 0) or 1
        players = getattr(self, "multiplayer_players", {})
        active_mp = getattr(self, "_multiplayer_active", lambda: False)()
        rows = players.items() if active_mp else [(local_id, {})]
        seen_ids = set()

        for player_id, data in sorted(rows, key=lambda item: safe_int(item[0])):
            player_id = safe_int(player_id, local_id)
            if not isinstance(data, dict):
                data = {}
            if player_id in seen_ids:
                continue
            seen_ids.add(player_id)
            is_local = player_id == local_id
            fallback_ship = getattr(self, "selected_ship", 0)
            ship_idx = safe_int(data.get("ship", fallback_ship), fallback_ship) if isinstance(data, dict) else fallback_ship
            ship_idx = max(0, min(len(SHIPS) - 1, ship_idx))
            x = self.player.center_x if is_local else safe_float(data.get("x"), self.player.center_x)
            y = self.player.center_y if is_local else safe_float(data.get("y"), self.player.center_y)
            health = self.player.health if is_local else safe_float(data.get("health", 100.0), 100.0)
            markers.append({
                "id": player_id,
                "name": "YOU" if is_local else str(data.get("name", f"P{player_id}"))[:6],
                "x": x,
                "y": y,
                "color": tuple(SHIPS[ship_idx]["color"][:3]),
                "is_local": is_local,
                "alive": health > 0,
            })

        if local_id not in seen_ids:
            ship_idx = max(0, min(len(SHIPS) - 1, getattr(self, "selected_ship", 0)))
            markers.append({
                "id": local_id,
                "name": "YOU",
                "x": self.player.center_x,
                "y": self.player.center_y,
                "color": tuple(SHIPS[ship_idx]["color"][:3]),
                "is_local": True,
                "alive": self.player.health > 0,
            })
        return markers

    def _draw_maze_map_player_marker(
            self, x: float, y: float, radius: float, marker: dict,
            label: bool = False) -> None:
        color = marker["color"]
        alpha = 245 if marker.get("alive", True) else 120
        pulse = 0.5 + 0.5 * math.sin(self.bg_time * 5.4 + int(marker.get("id", 0)))
        ring_c = (235, 250, 255, 215) if marker.get("is_local") else (*color, 190)
        arcade.draw_circle_filled(x, y, radius * (1.55 + 0.18 * pulse), (*color, int(34 + 32 * pulse)))
        arcade.draw_circle_filled(x, y, radius, (*color, alpha))
        arcade.draw_circle_outline(x, y, radius * 1.55, ring_c, 2)
        if label:
            text = "YOU" if marker.get("is_local") else f"P{int(marker.get('id', 0))}"
            arcade.draw_text(text, x, y,
                             (8, 10, 22, 245), max(7, min(10, int(radius * 1.55))),
                             anchor_x="center", anchor_y="center", bold=True,
                             font_name=FONT_NUMERIC)

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
        final_mission = (
            self._maze_is_final_floor()
            and exit_unlocked
            and (self.maze_boss_spawned or self._active_maze_bosses())
        )
        exit_c = (255, 210, 90) if final_mission else (EXIT_C if exit_unlocked else (255, 165, 60))
        exit_label = "BOSS" if final_mission else ("EXIT" if exit_unlocked else "LOCK")
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

        for boss in self._active_maze_bosses():
            pulse = 0.5 + 0.5 * math.sin(t * 4.0)
            boss_r = max(boss.width, boss.height) * (0.46 + 0.08 * pulse)
            arcade.draw_circle_filled(
                boss.center_x, boss.center_y, boss_r, (255, 190, 80, 48))
            arcade.draw_circle_outline(
                boss.center_x, boss.center_y, boss_r + 9, (255, 210, 105, 145), 3)
            arcade.draw_sprite(boss)
            bar_w = max(cs * 0.9, boss.width * 0.95)
            bx_ = boss.center_x - bar_w / 2
            by_ = boss.center_y + boss.height * 0.54 + 12
            ratio_ = max(0.0, boss.health / boss.max_health)
            arcade.draw_lrbt_rectangle_filled(
                bx_, bx_ + bar_w, by_, by_ + 8, (65, 26, 8, 225))
            arcade.draw_lrbt_rectangle_filled(
                bx_, bx_ + bar_w * ratio_, by_, by_ + 8, (255, 176, 55, 240))
            boss_name = "MAZE BOSS" if boss.split_depth == 0 else f"SPLIT {boss.split_depth}"
            self._txt_shadow(boss_name, boss.center_x, by_ + 12,
                             (255, 220, 125, 230), 10, FONT_UI_MENU,
                             anchor_x="center", bold=True)
            self._txt_shadow(f"{max(0, int(boss.health)):,} HP", boss.center_x, by_ - 10,
                             (255, 228, 160, 220), 8, FONT_NUMERIC,
                             anchor_x="center", bold=True)

        # ── Maze powerup glows ───────────────────────
        for pu in self.powerups:
            color = POWERUP_COLORS.get(pu.kind, (255, 255, 255))[:3]
            pulse = 0.5 + 0.5 * math.sin(t * 5.5 + pu.wobble_phase)
            arcade.draw_circle_filled(
                pu.center_x, pu.center_y,
                30 + 9 * pulse,
                (*color, int(46 + 58 * pulse)),
            )
            arcade.draw_circle_outline(
                pu.center_x, pu.center_y,
                36 + 6 * pulse,
                (*color, int(135 + 70 * pulse)),
                2,
            )
        self.powerups.draw()

        # ── Bullets ──────────────────────────────────
        self.maze_bullets.draw()
        self.maze_enemy_bullets.draw()
        for beam in self.beams:
            beam.draw()
        for bolt in self.elec_bolts:
            bolt.draw_bolt()
        if hasattr(self, "_draw_multiplayer_remote_fire_visuals"):
            self._draw_multiplayer_remote_fire_visuals()

        if hasattr(self, "_draw_multiplayer_remote_players"):
            self._draw_multiplayer_remote_players(t)

        # ── Player ──────────────────────────────────
        if self.player:
            p  = self.player
            glow_r = max(24, min(54, max(p.width, p.height) * 0.30))
            pg = (95, 200, 255, 36)
            arcade.draw_circle_filled(p.center_x, p.center_y, glow_r, pg)
            if p.shield_active:
                rr = glow_r + 2.5 * math.sin(t * 9)
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

        if not self.show_hud:
            self._maze_autopilot_btn = None
            self._txt_shadow("[H] show HUD", 14, h - 18,
                             (110, 135, 185, 110), 9, FU)
            return

        def compact_hp(value: float) -> str:
            value = max(0, int(value))
            units = ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K"))
            for divisor, suffix in units:
                if value >= divisor:
                    scaled = value / divisor
                    decimals = 2 if scaled < 10 else 1 if scaled < 100 else 0
                    text = f"{scaled:.{decimals}f}".rstrip("0").rstrip(".")
                    return f"{text}{suffix}"
            return str(value)

        # ── Health readout: classic stacked number + segmented bar ──
        hp_ratio = max(0.0, min(1.0, p.health / max(1, p.max_health)))
        hp_c = (70, 225, 105) if hp_ratio > 0.35 else (255, 70, 80)
        low_flash = hp_ratio <= 0.25 and math.sin(t * 11.0) > 0
        if low_flash:
            hp_c = (255, 235, 120)

        hx = 24
        hy = h - 14
        hp_pair = f"{compact_hp(p.health)} / {compact_hp(p.max_health)}"
        health_label_y = hy
        self._txt_shadow("HEALTH", hx + 2, health_label_y,
                         (120, 255, 160, 190), 11, FU, anchor_y="top", bold=True)

        hp_text_y = health_label_y - 22
        self._txt_shadow(hp_pair, hx, hp_text_y,
                         (*hp_c[:3], 235), 12, FN, anchor_y="top", bold=True)

        segs = 22
        gap = 3
        seg_w = 9
        seg_h = 10
        bar_x = hx
        bar_y = hp_text_y - 38
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
        lbl = f"FLOOR  {self._maze_display_floor()}/{MAZE_MAX_LEVELS}"
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
        enemy_cap = self._maze_enemy_cap()
        self._txt_shadow(f"ENEMIES  {len(self.maze_enemies)}/{enemy_cap}",
                         w - 16, h - 72, (255, 145, 120, 190),
                         10, FN, anchor_x="right", bold=True)
        keys_left = max(0, MAZE_KEYS_REQUIRED - self.maze_keys_collected)
        key_time = max(0, int(math.ceil(getattr(self, "maze_key_relocate_timer", 0.0))))
        self._txt_shadow(f"KEYS  {self.maze_keys_collected}/{MAZE_KEYS_REQUIRED}   SHIFT {key_time:03d}s",
                         w - 16, h - 90, (255, 220, 95, 215 if keys_left else 170),
                         10, FN, anchor_x="right", bold=True)

        self._draw_powerup_panel(p, t, FU, FN)

        # ── In-game auto pilot toggle ───────────────────
        auto_unlocked = self._maze_autopilot_unlocked()
        auto_enabled = auto_unlocked and bool(getattr(self, "maze_autopilot_enabled", False))
        auto_active = auto_enabled and bool(getattr(self, "maze_autopilot_active", False))
        btn_w = min(250, max(204, int(w * 0.15)))
        btn_h = 28
        btn_x = w // 2 - btn_w // 2
        btn_y = 30
        self._maze_autopilot_btn = (btn_x, btn_x + btn_w, btn_y, btn_y + btn_h)
        auto_hover = auto_unlocked and self._is_hovering(btn_x, btn_x + btn_w, btn_y, btn_y + btn_h)
        if auto_active:
            auto_fill = (12, 94, 62, 220)
            auto_border = (110, 255, 175, 240)
            auto_text = (150, 255, 195, 255)
            auto_label = "[TAB] AUTO PILOT ON"
        elif auto_enabled:
            auto_fill = (18, 55, 95, 210)
            auto_border = (120, 205, 255, 220)
            auto_text = (170, 225, 255, 245)
            auto_label = "[TAB] AUTO ARMED"
        elif auto_unlocked:
            auto_fill = (12, 28, 58, 190)
            auto_border = (88, 165, 235, 200)
            auto_text = (170, 215, 255, 235)
            auto_label = "[TAB] AUTO PILOT OFF"
        else:
            auto_fill = (18, 22, 38, 145)
            auto_border = (88, 105, 145, 145)
            auto_text = (130, 145, 178, 175)
            auto_label = "[TAB] AUTO LOCKED"
        if auto_hover:
            auto_fill = (*auto_fill[:3], min(255, auto_fill[3] + 35))
            auto_border = (*auto_border[:3], 255)
        arcade.draw_lrbt_rectangle_filled(btn_x + 4, btn_x + btn_w + 4,
                                          btn_y - 4, btn_y + btn_h - 4,
                                          (0, 0, 0, 70))
        arcade.draw_lrbt_rectangle_filled(btn_x, btn_x + btn_w, btn_y, btn_y + btn_h, auto_fill)
        arcade.draw_lrbt_rectangle_filled(btn_x + 2, btn_x + btn_w - 2,
                                          btn_y + btn_h - 5, btn_y + btn_h - 2,
                                          (255, 255, 255, 34 if auto_unlocked else 18))
        arcade.draw_lrbt_rectangle_outline(btn_x, btn_x + btn_w, btn_y, btn_y + btn_h,
                                           auto_border, 2)
        self._txt_shadow(auto_label, btn_x + btn_w // 2, btn_y + btn_h // 2 - 1,
                         auto_text, 10, FU, anchor_x="center", anchor_y="center", bold=True)

        # ── Hint ────────────────────────────────────
        arcade.draw_text("WASD Move · Hold LMB Fire · TAB Auto · M Map · 1-3 Power-ups · 5 Special · B Breach · ESC Pause · H HUD",
                         w // 2, 12, (70, 100, 155, 130), 8,
                         anchor_x="center", font_name=FN)

        # ── Notification ────────────────────────────
        if self.notif_timer > 0:
            a = min(255, int(self.notif_timer * 300))
            self._txt_shadow(self.notif_text, w // 2, h // 2 + 90,
                             (*self.notif_color[:3], a), 26, FU,
                             anchor_x="center", bold=True)

        self._draw_maze_minimap()
        if getattr(self, "maze_map_open", False):
            self._draw_maze_map_overlay()

    def _draw_maze_minimap(self):
        maze   = self.maze_grid
        mode_c = tuple((getattr(self, "maze_preset", None) or MAZE_PRESETS[0])["color"][:3])
        cs = self.maze_cell_size
        ox, oy = self.maze_origin
        mx, my, mw, mh, mm_cs, pad = self._maze_minimap_layout()
        col_min, col_max, row_min, row_max = self._maze_local_map_bounds(11, 9)
        view_cols = col_max - col_min
        view_rows = row_max - row_min
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
        break_c = self._maze_map_breakable_color(mode_c, 220)

        detailed_minimap = view_cols * view_rows <= 1600
        if detailed_minimap:
            # Floors
            for row in range(row_min, row_max):
                for col in range(col_min, col_max):
                    fx = mx + (col - col_min) * mm_cs;  fy = my + (row - row_min) * mm_cs
                    arcade.draw_lrbt_rectangle_filled(fx, fx + mm_cs, fy, fy + mm_cs, (*mini_bg, 80))

            # Walls
            for row in range(row_min, row_max):
                for col in range(col_min, col_max):
                    fx = mx + (col - col_min) * mm_cs;  fy = my + (row - row_min) * mm_cs
                    if row < row_max - 1 and not maze.is_open(col, row, MazeGrid.N):
                        wall_c = break_c if maze.is_breakable_wall(col, row, MazeGrid.N) else wc2
                        arcade.draw_lrbt_rectangle_filled(
                            fx, fx + mm_cs,
                            fy + mm_cs - MWTT, fy + mm_cs + MWTT, wall_c)
                    if col < col_max - 1 and not maze.is_open(col, row, MazeGrid.E):
                        wall_c = break_c if maze.is_breakable_wall(col, row, MazeGrid.E) else wc2
                        arcade.draw_lrbt_rectangle_filled(
                            fx + mm_cs - MWTT, fx + mm_cs + MWTT,
                            fy, fy + mm_cs, wall_c)
        else:
            arcade.draw_lrbt_rectangle_filled(mx, mx + mw, my, my + mh, (*mini_bg, 82))
            step = max(3, max(view_cols, view_rows) // 5)
            grid_c = (*mode_c, 38)
            for row in range(0, view_rows + 1, step):
                yy = my + row * mm_cs
                arcade.draw_line(mx, yy, mx + mw, yy, grid_c, 1)
            for col in range(0, view_cols + 1, step):
                xx = mx + col * mm_cs
                arcade.draw_line(xx, my, xx, my + mh, grid_c, 1)

        # Border
        arcade.draw_lrbt_rectangle_outline(mx, mx + mw, my, my + mh, wc2, MWTT)

        # Exit marker
        if col_min <= self.maze_exit_col < col_max and row_min <= self.maze_exit_row < row_max:
            ex2 = mx + (self.maze_exit_col - col_min + 0.5) * mm_cs
            ey2 = my + (self.maze_exit_row - row_min + 0.5) * mm_cs
            exit_mini_c = (0, 255, 155, 210) if self.maze_keys_collected >= MAZE_KEYS_REQUIRED else (255, 165, 60, 210)
            arcade.draw_circle_filled(ex2, ey2, mm_cs * 0.45, exit_mini_c)

        # Key markers
        for key in getattr(self, "maze_keys", []):
            if key.get("collected", False):
                continue
            if not (col_min <= key["col"] < col_max and row_min <= key["row"] < row_max):
                continue
            kx = mx + (key["col"] - col_min + 0.5) * mm_cs
            ky = my + (key["row"] - row_min + 0.5) * mm_cs
            arcade.draw_circle_filled(kx, ky, max(2, mm_cs * 0.36), (255, 220, 70, 235))
            arcade.draw_circle_outline(kx, ky, max(3, mm_cs * 0.55), (255, 245, 160, 160), 1)

        enemy_count = len(self.maze_enemies)
        for enemy in self.maze_enemies:
            e_col = (enemy.center_x - ox) / cs
            e_row = (enemy.center_y - oy) / cs
            if not (col_min <= e_col < col_max and row_min <= e_row < row_max):
                continue
            ex3 = mx + (e_col - col_min) * mm_cs
            ey3 = my + (e_row - row_min) * mm_cs
            dot_r = max(1.5, mm_cs * 0.26)
            arcade.draw_circle_filled(ex3, ey3, dot_r, (255, 70, 70, 235))
            arcade.draw_circle_outline(ex3, ey3, max(2.5, dot_r * 1.55), (255, 150, 120, 135), 1)

        for boss in self._active_maze_bosses():
            b_col = (boss.center_x - ox) / cs
            b_row = (boss.center_y - oy) / cs
            if col_min <= b_col < col_max and row_min <= b_row < row_max:
                bx = mx + (b_col - col_min) * mm_cs
                by = my + (b_row - row_min) * mm_cs
                arcade.draw_circle_filled(bx, by, max(3, mm_cs * 0.42), (255, 190, 70, 245))
                arcade.draw_circle_outline(bx, by, max(5, mm_cs * 0.72), (255, 235, 130, 180), 2)

        for marker in self._maze_team_map_markers():
            p_col = (marker["x"] - ox) / cs
            p_row = (marker["y"] - oy) / cs
            if not (col_min <= p_col < col_max and row_min <= p_row < row_max):
                continue
            px3 = mx + (p_col - col_min) * mm_cs
            py3 = my + (p_row - row_min) * mm_cs
            self._draw_maze_map_player_marker(px3, py3, max(2.5, mm_cs * 0.42), marker)

        self._txt_shadow(f"ENEMY {enemy_count}", mx + mw + pad, my - 14,
                         (255, 135, 115, 210), 8, FONT_NUMERIC,
                         anchor_x="right", anchor_y="top", bold=True)

    def _draw_maze_map_overlay(self):
        maze = self.maze_grid
        mode_c = tuple((getattr(self, "maze_preset", None) or MAZE_PRESETS[0])["color"][:3])
        cs = self.maze_cell_size
        ox, oy = self.maze_origin
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
        break_c = self._maze_map_breakable_color(mode_c, 218)

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

        enemy_count = len(self.maze_enemies)
        for enemy in self.maze_enemies:
            ex3 = mx + ((enemy.center_x - ox) / cs) * mm_cs
            ey3 = my + ((enemy.center_y - oy) / cs) * mm_cs
            dot_r = max(3, mm_cs * 0.22)
            arcade.draw_circle_filled(ex3, ey3, dot_r, (255, 72, 72, 235))
            arcade.draw_circle_outline(ex3, ey3, max(5, dot_r * 1.65), (255, 145, 115, 145), 1)

        for boss in self._active_maze_bosses():
            bx = mx + ((boss.center_x - ox) / cs) * mm_cs
            by = my + ((boss.center_y - oy) / cs) * mm_cs
            arcade.draw_circle_filled(bx, by, max(5, mm_cs * 0.42), (255, 190, 70, 245))
            arcade.draw_circle_outline(bx, by, max(8, mm_cs * 0.75), (255, 235, 130, 180), 2)

        for marker in self._maze_team_map_markers():
            px = mx + ((marker["x"] - ox) / cs) * mm_cs
            py = my + ((marker["y"] - oy) / cs) * mm_cs
            if not (mx <= px <= mx + mw and my <= py <= my + mh):
                continue
            self._draw_maze_map_player_marker(px, py, max(5, mm_cs * 0.36), marker, label=True)

        progress = int(max(getattr(self, "maze_progress_best", 0.0), self._maze_completion_ratio()) * 100)
        self._txt_shadow("MAZE MAP", w // 2, my + mh + 52, (190, 255, 220, 245),
                         22, FU, anchor_x="center", bold=True)
        self._txt_shadow(f"FLOOR {self._maze_display_floor()}   {progress:02d}% COMPLETE   ENEMIES {enemy_count}",
                         w // 2, my + mh + 28, (150, 210, 230, 220),
                         11, FN, anchor_x="center", bold=True)
        self._txt_shadow("PRESS M OR ESC TO CLOSE",
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
        self._txt_shadow(f"FLOOR  {self._maze_display_floor()}/{MAZE_MAX_LEVELS}",
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

        mp_client_world = getattr(self, "_multiplayer_is_client_world", lambda: False)()
        self.time_alive += delta
        self.maze_exit_lock_notice_timer = max(
            0.0, getattr(self, "maze_exit_lock_notice_timer", 0.0) - delta)
        if not mp_client_world:
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
        player_dead = getattr(self, "_multiplayer_active", lambda: False)() and p.health <= 0

        # ── Player movement ──────────────────────────
        if player_dead:
            ix = iy = 0.0
        else:
            ix = float(self.right_key) - float(self.left_key)
            iy = float(self.up) - float(self.down)
            if ix and iy:
                ix *= 0.70710678;  iy *= 0.70710678
            auto_vec = self._maze_autopilot_drive(delta, p, cs)
            if auto_vec is not None:
                ix, iy = auto_vec
        ship_spd = self._maze_player_move_speed()
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
            target_angle = (
                self._maze_player_angle_from_motion(p.change_x, p.change_y)
                + getattr(p, "front_angle_offset", 0.0)
            )
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
        if not player_dead:
            self._collect_maze_key_at_player()

        # ── Exit check ───────────────────────────────
        pc2, pr2 = self._maze_player_cell()
        self.maze_progress_best = max(
            getattr(self, "maze_progress_best", 0.0),
            self._maze_completion_ratio(),
        )
        if (not player_dead
                and pc2 == self.maze_exit_col and pr2 == self.maze_exit_row
                and not self.maze_exit_reached):
            if self.maze_keys_collected < MAZE_KEYS_REQUIRED:
                if self.maze_exit_lock_notice_timer <= 0:
                    needed = MAZE_KEYS_REQUIRED - self.maze_keys_collected
                    self.notif_text = f"EXIT LOCKED!  {needed} KEY{'S' if needed != 1 else ''} NEEDED"
                    self.notif_color = (255, 190, 70)
                    self.notif_timer = 1.1
                    self.maze_exit_lock_notice_timer = 1.25
            else:
                if mp_client_world:
                    if getattr(self, "_mp_exit_event_sent_level", None) != self.maze_level:
                        if hasattr(self, "_queue_multiplayer_event"):
                            self._queue_multiplayer_event({
                                "type": "exit_reached",
                                "level": int(self.maze_level),
                            })
                        self._mp_exit_event_sent_level = self.maze_level
                    if self.maze_exit_lock_notice_timer <= 0:
                        self.notif_text = "WAITING FOR HOST TO ADVANCE THE FLOOR"
                        self.notif_color = (120, 220, 255)
                        self.notif_timer = 1.0
                        self.maze_exit_lock_notice_timer = 1.25
                elif self._maze_is_final_floor():
                    if not self.maze_boss_spawned:
                        self._spawn_maze_boss()
                    if self.maze_exit_lock_notice_timer <= 0:
                        self.notif_text = "FINAL MISSION: DEFEAT THE BOSS!"
                        self.notif_color = (255, 210, 90)
                        self.notif_timer = 1.2
                        self.maze_exit_lock_notice_timer = 1.25
                else:
                    if getattr(self, "_multiplayer_active", lambda: False)() and hasattr(self, "_advance_multiplayer_maze_floor"):
                        self._advance_multiplayer_maze_floor()
                    else:
                        self.maze_exit_reached = True
                        bonus = max(0, 2000 - int(self.time_alive * 5))
                        self.score += bonus
                        self.maze_level = min(MAZE_MAX_LEVELS - 1, self.maze_level + 1)
                        self._save_maze_resume_floor()
                        self.setup_maze(keep_player=True)
                        self.notif_text  = (
                            f"FLOOR {self._maze_display_floor()} SPEED + DAMAGE + STORAGE UP!  "
                            f"+{bonus} TIME BONUS"
                        )
                        self.notif_color = (120, 255, 160)
                        self.notif_timer = 1.8

        self._update_particles(delta)

        # ── Maze powerups ───────────────────────────────────────────
        self.powerups.update(delta)
        for pu in list(self.powerups):
            if pu.life <= 0:
                if not getattr(self, "_multiplayer_is_client_world", lambda: False)():
                    pu.remove_from_sprite_lists()
                continue
            if not player_dead and arcade.check_for_collision(pu, p):
                collected = False
                if pu.kind in ("maze_health", "maze_speed"):
                    collected = self._collect_maze_potion(pu)
                elif getattr(self, "_powerup_allowed_for_ship", lambda kind: True)(pu.kind):
                    collected = self._collect_powerup(pu.kind)
                else:
                    self._collect_powerup(pu.kind)
                if collected:
                    self._burst(pu.center_x, pu.center_y, 12,
                                (255, 195, 65), 45, 150, 0.9, 2.1, .06, .18)
                    if getattr(self, "_multiplayer_is_client_world", lambda: False)():
                        powerup_id = getattr(pu, "net_id", None)
                        if powerup_id is not None and hasattr(self, "_queue_multiplayer_event"):
                            self._queue_multiplayer_event({
                                "type": "powerup_collect",
                                "powerup_id": int(powerup_id),
                            })
                    pu.remove_from_sprite_lists()
                    if getattr(self, "maze_autopilot_active", False):
                        self._maze_autopilot_repath_timer = 0.0

        # ── Player shooting (hold left-mouse, or auto-pilot while it collects keys) ──
        auto_aim = getattr(self, "_maze_autopilot_aim", None)
        auto_special_fire = bool(
            getattr(self, "maze_autopilot_active", False)
            and getattr(self, "_maze_autopilot_fire_special", False)
        )
        auto_fire = bool(
            getattr(self, "maze_autopilot_active", False)
            and (auto_aim is not None or auto_special_fire)
        )
        if not player_dead and (self.mouse_held or auto_fire):
            is_beam_ship = (self.selected_ship in BEAM_SHIP_INDICES)
            is_electric_ship = (self.selected_ship in ELECTRIC_SHIP_INDICES)
            if p.elec360_active:
                fire_rate = ELECTRIC_360_FIRE_RATE
            else:
                fire_rate = ELECTRIC_FIRE_RATE if is_electric_ship else NORMAL_FIRE_RATE
            self.fire_timer += delta
            while self.fire_timer >= fire_rate:
                self.fire_timer -= fire_rate
                # Convert screen-space mouse → world coords
                if auto_fire:
                    if auto_aim is not None:
                        mx_w, my_w = auto_aim
                    else:
                        mx_w, my_w = p.center_x + 1.0, p.center_y
                else:
                    mx_w = self.maze_cam_x + self.mouse_x
                    my_w = self.maze_cam_y + self.mouse_y
                base_angle = math.atan2(my_w - p.center_y, mx_w - p.center_x)
                shot_angles = (
                    [base_angle - 0.18, base_angle, base_angle + 0.18]
                    if p.triple_active else [base_angle]
                )
                if is_beam_ship or p.beam360_active:
                    first_new = len(self.beams)
                    if hasattr(self, "_queue_multiplayer_fire_event"):
                        self._queue_multiplayer_fire_event(
                            "beam", p.center_x, p.center_y,
                            shot_angles, full_360=p.beam360_active)
                    self._fire_beam(p.beam360_active, aim_x=mx_w, aim_y=my_w)
                    self._clip_new_maze_beams(first_new)
                elif is_electric_ship or p.elec360_active:
                    if hasattr(self, "_queue_multiplayer_fire_event"):
                        self._queue_multiplayer_fire_event(
                            "electric", p.center_x, p.center_y,
                            shot_angles, full_360=p.elec360_active)
                    self._fire_electric(full_360=p.elec360_active, aim_x=mx_w, aim_y=my_w)
                else:
                    if hasattr(self, "_queue_multiplayer_fire_event"):
                        self._queue_multiplayer_fire_event(
                            "bullet", p.center_x, p.center_y, shot_angles)
                    for ang in shot_angles:
                        b = Bullet(p.center_x, p.center_y, ang)
                        self.maze_bullets.append(b)
                        self._spawn_muzzle(p.center_x, p.center_y, ang)
        else:
            self.fire_timer = 0.0

        # ── Update beam/electric weapons in maze space ───────────────
        self.beams = [beam for beam in self.beams if beam.life > 0]
        for beam in self.beams:
            beam.update(delta)

        self.elec_bolts.update(delta)
        for bolt in list(self.elec_bolts):
            wall_hit = self._maze_wall_at_point(bolt.center_x, bolt.center_y, 5)
            blocked = not self._maze_can_move_to(bolt.center_x, bolt.center_y, 5)
            if bolt.life <= 0 or wall_hit is not None or blocked:
                if wall_hit is not None:
                    self._damage_maze_wall_with_breach(
                        wall_hit, bolt.center_x, bolt.center_y, (150, 110, 255))
                if bolt.life > 0:
                    self._burst(bolt.center_x, bolt.center_y, 6,
                                (150, 110, 255), 42, 135, 0.8, 1.8, .04, .12)
                bolt.remove_from_sprite_lists()

        if hasattr(self, "_update_multiplayer_remote_fire_visuals"):
            self._update_multiplayer_remote_fire_visuals(delta)

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
                if getattr(p, "breach_active", False):
                    damaged = self._damage_maze_wall_with_breach(
                        wall_hit, b.center_x, b.center_y, (255, 190, 65))
                    if not damaged:
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

        max_enemies = self._maze_enemy_cap()

        # ── Enemy AI (move + shoot) ───────────────────────────────────
        if mp_client_world and hasattr(self, "_smooth_multiplayer_authoritative_sprites"):
            self._smooth_multiplayer_authoritative_sprites(delta)
        if not mp_client_world:
            pc, pr = self._maze_player_cell()
            shared_targets = (
                getattr(self, "_multiplayer_active", lambda: False)()
                and hasattr(self, "_closest_multiplayer_hero")
            )
            flow_maps = {}
            if not shared_targets:
                if (getattr(self, "_maze_enemy_flow_target", None) != (pc, pr)
                        or not getattr(self, "_maze_enemy_flow_next", None)):
                    self._rebuild_maze_enemy_flow(pc, pr)
                flow_maps[(pc, pr)] = self._maze_enemy_flow_next
            for enemy in list(self.maze_enemies):
                target_x, target_y = p.center_x, p.center_y
                target_cell = (pc, pr)
                if shared_targets:
                    target = self._closest_multiplayer_hero(enemy.center_x, enemy.center_y)
                    if target is not None:
                        target_x, target_y = target["x"], target["y"]
                        target_cell = (target["col"], target["row"])
                    if target_cell not in flow_maps:
                        flow_maps[target_cell] = self._maze_enemy_flow_for_target(*target_cell)
                flow_next = flow_maps[target_cell]
                enemy.maze_update_flow(delta, flow_next, cs, ox, oy)

                enemy.shoot_timer -= delta
                if enemy.shoot_timer <= 0:
                    enemy.shoot_timer = (MAZE_ENEMY_FIRE_RATE
                                         + random.uniform(-0.6, 0.6))
                    dx_to_player = target_x - enemy.center_x
                    dy_to_player = target_y - enemy.center_y
                    if dx_to_player * dx_to_player + dy_to_player * dy_to_player > (cs * 5.5) ** 2:
                        continue
                    ang = math.atan2(dy_to_player, dx_to_player)
                    eb = EnemyBullet(enemy.center_x, enemy.center_y,
                                     angle_rad=ang,
                                     speed=MAZE_ENEMY_BULLET_SPEED)
                    eb.life = MAZE_ENEMY_BULLET_LIFE
                    if hasattr(self, "_assign_maze_enemy_bullet_id"):
                        self._assign_maze_enemy_bullet_id(eb)
                    self.maze_enemy_bullets.append(eb)

            self._update_maze_boss(delta, p, cs, ox, oy)

        # ── Beam/electric → enemy collision ──────────────────────────
        for beam in list(self.beams):
            for enemy in list(self.maze_enemies):
                hit_r = max(enemy.width, enemy.height) * 0.45
                if beam.intersects_circle(enemy.center_x, enemy.center_y, hit_r):
                    self._damage_maze_enemy(enemy, enemy.health, (255, 130, 70), max_enemies)
            for boss in list(self._active_maze_bosses()):
                hit_r = max(boss.width, boss.height) * 0.45
                if beam.intersects_circle(boss.center_x, boss.center_y, hit_r):
                    self._damage_maze_boss(
                        boss,
                        self._maze_player_damage(BEAM_DAMAGE_PER_SEC * delta),
                        (255, 130, 70),
                    )

        for bolt in list(self.elec_bolts):
            hits = arcade.check_for_collision_with_list(bolt, self.maze_enemies)
            if hits:
                enemy = hits[0]
                self._burst(bolt.center_x, bolt.center_y, 10,
                            (140, 100, 255), 55, 200, 1.2, 2.6, .06, .18)
                self._burst(bolt.center_x, bolt.center_y, 4,
                            (220, 200, 255), 80, 260, 0.8, 1.8, .04, .10)
                bolt.remove_from_sprite_lists()
                self._damage_maze_enemy(
                    enemy,
                    self._maze_player_damage(bolt.damage),
                    (130, 90, 255),
                    max_enemies,
                )
                continue
            for boss in list(self._active_maze_bosses()):
                if arcade.check_for_collision(bolt, boss):
                    self._damage_maze_boss(
                        boss,
                        self._maze_player_damage(bolt.boss_damage),
                        (150, 110, 255),
                    )
                    bolt.remove_from_sprite_lists()
                    break

        # ── Bullet → enemy collision ─────────────────────────────────
        for b in list(self.maze_bullets):
            hits = arcade.check_for_collision_with_list(b, self.maze_enemies)
            if hits:
                b.remove_from_sprite_lists()
                enemy = hits[0]
                self._burst(b.center_x, b.center_y, 8,
                            (255, 220, 100), 55, 180, 1.0, 2.2, .07, .18)
                self._damage_maze_enemy(
                    enemy,
                    self._maze_player_damage(20),
                    (255, 130, 70),
                    max_enemies,
                )
                continue
            for boss in list(self._active_maze_bosses()):
                if arcade.check_for_collision(b, boss):
                    b.remove_from_sprite_lists()
                    self._damage_maze_boss(
                        boss,
                        self._maze_player_damage(20),
                        (255, 220, 100),
                    )
                    break

        # ── Enemy bullet → player collision ─────────────────────────
        for b in list(self.maze_enemy_bullets):
            if not player_dead and arcade.check_for_collision(b, p):
                b.remove_from_sprite_lists()
                if mp_client_world:
                    bullet_id = getattr(b, "net_id", None)
                    if bullet_id is not None and hasattr(self, "_queue_multiplayer_event"):
                        self._queue_multiplayer_event({
                            "type": "enemy_bullet_hit",
                            "bullet_id": int(bullet_id),
                        })
                if p.shield_active:
                    self._burst(b.center_x, b.center_y, 7,
                                (90, 220, 255), 50, 160, 0.9, 2.0, .06, .14)
                else:
                    p.health -= getattr(b, "damage", MAZE_ENEMY_BULLET_DAMAGE)
                    self.damage_flash = max(self.damage_flash, 0.75)
                    self._burst(b.center_x, b.center_y, 12,
                                (255, 75, 75), 60, 200, 1.0, 2.2, .08, .20)
                    if p.health <= 0:
                        self._maze_gameover()
                        return

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
        if hasattr(self, "_assign_maze_enemy_id"):
            self._assign_maze_enemy_id(enemy)
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

    def _maze_powerup_drop_pool(self) -> list[str]:
        """Maze drops plus only the selected ship's compatible special."""
        ship_idx = getattr(self, "_maze_drop_ship_override", None)
        if ship_idx is None:
            ship_idx = self.selected_ship
        pool = [
            kind for kind in MAZE_POWERUP_TYPES
            if kind not in BEAM_ONLY_POWERUPS
            and kind not in ELECTRIC_ONLY_POWERUPS
        ]
        if ship_idx in BEAM_SHIP_INDICES:
            pool += ["beam360"] * 2
        if ship_idx in ELECTRIC_SHIP_INDICES:
            pool += ["elec360"] * 2
        return pool

    def _drop_maze_powerup(self, x: float, y: float, kind: str | None = None) -> None:
        """Drop a stationary maze-styled powerup from a defeated enemy."""
        if kind is None:
            kind = random.choice(self._maze_powerup_drop_pool())
        pu = Powerup(x, y, kind, maze_style=True)
        pu.change_y = 0
        pu.life = 18.0
        pu.scale = 1.35
        if hasattr(self, "_assign_maze_powerup_id"):
            self._assign_maze_powerup_id(pu)
        self.powerups.append(pu)
        if getattr(self, "maze_autopilot_active", False):
            self._maze_autopilot_repath_timer = 0.0
        glow = POWERUP_COLORS.get(kind, (255, 255, 255))[:3]
        self._burst(x, y, 14, glow, 40, 150, 0.8, 2.0, .05, .16)

    def _split_maze_enemy(self, enemy: MazeEnemy, max_enemies: int) -> bool:
        """Replace a defeated normal enemy with its next split form."""
        split_depth = getattr(enemy, "split_depth", 0)
        if split_depth >= MAZE_ENEMY_MAX_SPLITS:
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

        col, row = random.choice(options) if options else (enemy.maze_col, enemy.maze_row)
        child_depth = split_depth + 1
        child_health = max(1, int(enemy.max_health * MAZE_ENEMY_SPLIT_HEALTH_MULT))
        child = MazeEnemy(
            col, row, cs, ox, oy,
            health=child_health,
            split_depth=child_depth,
        )
        if hasattr(self, "_assign_maze_enemy_id"):
            self._assign_maze_enemy_id(child)
        child.shoot_timer = random.uniform(0.8, 2.4)
        self._maybe_drop_maze_powerup(enemy.center_x, enemy.center_y)
        enemy.remove_from_sprite_lists()
        self.maze_enemies.append(child)
        self.maze_enemies_created += 1
        self.notif_text = f"ENEMY SPLIT {child_depth}/{MAZE_ENEMY_MAX_SPLITS}!"
        self.notif_color = (255, 170, 110)
        self.notif_timer = max(self.notif_timer, 0.45)
        self._burst(enemy.center_x, enemy.center_y, 10,
                    (255, 120, 90), 45, 140, 0.8, 1.8, .05, .14)
        return True

    def _maze_gameover(self):
        self.maze_run_complete = False
        self.player.health = 0
        if getattr(self, "_multiplayer_active", lambda: False)():
            self._clear_movement_input()
            self.mouse_held = False
            self.notif_text = "SHIP DOWN - RESPAWN NEXT FLOOR"
            self.notif_color = (255, 120, 120)
            self.notif_timer = 2.0
            return
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
        self._draw_space_theme_background(dim_alpha=54)

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

        # ── Mode cards ──────────────────────────────────────────────────
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
                "icon":    "crossed_swords",
                "desc":    "Battle with others",
                "detail":  "Co-op & PvP online",
                "color":   (176, 116, 255),
                "available": True,
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
        self._draw_space_theme_selector(22, 22, min(282, max(230, w * 0.30)), 32, FU, FN)

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
                if mode["key"] == "multiplayer":
                    fill = (7, 13, 37, 232)
                    border = (45, 64, 126, 185)
                else:
                    fill = (12, 16, 40, 210)
                    border = (38, 46, 80, 130)
            elif hov:
                fill = (42, 20, 88, 230) if mode["key"] == "multiplayer" else (14, 32, 80, 220)
                border = (*mc, 255)
            elif sel:
                fill = (30, 14, 72, 236) if mode["key"] == "multiplayer" else (11, 22, 58, 228)
                border = (*mc[:3], 210 if mode["key"] == "multiplayer" else 180)
            else:
                fill = (14, 10, 50, 226) if mode["key"] == "multiplayer" else (9, 18, 50, 220)
                border = (*mc[:3], 135 if mode["key"] == "multiplayer" else 110)

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
            icon_c = mc if avail else (55, 65, 100, 150)
            icon_a = int(200 + 55 * math.sin(t * 3.0 + i)) if avail else 105
            if mode["icon"] == "crossed_swords":
                ix = cx_
                iy = ct - 62
                sword_c = (*icon_c[:3], icon_a)
                shadow_c = (0, 0, 0, 70)
                for dx, dy, color in [(2, -2, shadow_c), (0, 0, sword_c)]:
                    arcade.draw_line(ix - 18 + dx, iy + 18 + dy,
                                     ix + 18 + dx, iy - 18 + dy, color, 3)
                    arcade.draw_line(ix + 18 + dx, iy + 18 + dy,
                                     ix - 18 + dx, iy - 18 + dy, color, 3)
                    arcade.draw_line(ix - 20 + dx, iy - 18 + dy,
                                     ix - 10 + dx, iy - 8 + dy, color, 3)
                    arcade.draw_line(ix + 20 + dx, iy - 18 + dy,
                                     ix + 10 + dx, iy - 8 + dy, color, 3)
            else:
                arcade.draw_text(mode["icon"], cx_, ct - 62,
                                 (*icon_c[:3], icon_a), 34,
                                 anchor_x="center", anchor_y="center", font_name=FU)

            # Divider
            div_c = (*mc[:3], 80) if avail else (38, 46, 80, 60)
            arcade.draw_line(cl + 18, ct - 90, cr - 18, ct - 90, div_c, 1)

            # Mode label
            lbl_c = (*mc, 255) if avail else (78, 98, 160, 210)
            label_size = 18 if mode["key"] == "multiplayer" else 15
            arcade.draw_text(mode["label"], cx_ + 1, ct - 118,
                             (0, 0, 0, 80), label_size, anchor_x="center", bold=True, font_name=FU)
            arcade.draw_text(mode["label"], cx_, ct - 116,
                             lbl_c, label_size, anchor_x="center", bold=True, font_name=FU)

            # Short description
            desc_c = (180, 205, 245, 210) if avail else (82, 104, 166, 185)
            arcade.draw_text(mode["desc"], cx_, ct - 148,
                             desc_c, 11, anchor_x="center", font_name=FU)

            # Detail line
            det_c = (165, 195, 245, 220) if avail else (44, 58, 100, 145)
            self._txt_shadow(mode["detail"], cx_, ct - 168,
                             det_c, 10 if card_w >= 190 else 9, FU,
                             anchor_x="center", ox=1, oy=-1)

            # COMING SOON badge
            if not avail:
                bw2 = card_w - 28;  bh2 = 34
                bx2 = cl + 14;      by2 = cb + 30
                arcade.draw_lrbt_rectangle_filled(bx2, bx2 + bw2, by2, by2 + bh2,
                                                   (22, 28, 62, 220))
                arcade.draw_lrbt_rectangle_outline(bx2, bx2 + bw2, by2, by2 + bh2,
                                                    (76, 96, 166, 205), 2)
                arcade.draw_text("COMING SOON", bx2 + bw2 // 2, by2 + bh2 // 2,
                                 (116, 142, 218, 220), 11, anchor_x="center",
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

        # ── Footer hint ─────────────────────────────────────────────────
        arcade.draw_text("Double-click a mode card to enter  ·  F11 Fullscreen",
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

        arcade.draw_text("Double-click a maze plan to enter  ·  ESC to go back",
                         w // 2, 16, (70, 130, 95, 140), 9,
                         anchor_x="center", font_name=FN)

    def _start_maze_with_preset(self):
        """Reset maze run state and start from the saved floor checkpoint."""
        self.maze_preset = next(
            (p for p in MAZE_PRESETS if p["key"] == self.selected_maze_preset),
            MAZE_PRESETS[0]
        )
        self.maze_level = max(
            0,
            min(MAZE_MAX_LEVELS - 1, int(getattr(self, "maze_saved_level", 0))),
        )
        self._save_maze_resume_floor(self.maze_level)
        self.maze_run_complete = False
        self.score      = 0
        self.time_alive = 0.0
        self.run_coins  = 0
        self.setup_maze(keep_player=False)
