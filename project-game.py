import arcade
import random
import math
from PIL import Image

# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Space Shooter: Neon Drift"

BG_COLOR = (6, 9, 24)

# Speeds are now pixels/second for smooth delta-time movement.
PLAYER_SPEED = 320
ENEMY_SPEED = 125
BOSS_SPEED = 82

PLAYER_HEALTH = 100
ENEMY_HEALTH = 30
BOSS_HEALTH = 220

BULLET_SPEED = 660
ENEMY_BULLET_SPEED = 430
POWERUP_FALL_SPEED = 105

NORMAL_FIRE_RATE = 0.22
AUTO_FIRE_RATE = 0.075

POWERUP_DURATION = 10.0
DROP_CHANCE = 40

STAR_COUNT = 120
MAX_PARTICLES = 700
CONTACT_DAMAGE = 14
CONTACT_DAMAGE_COOLDOWN = 0.35


# -------------------------------------------------
# TEXTURE CACHE
# -------------------------------------------------

_texture_cache: dict = {}


def load_texture_clean(path: str, scale: float = 1.0) -> arcade.Texture:
    key = (path, scale)
    if key in _texture_cache:
        return _texture_cache[key]

    img = Image.open(path).convert("RGBA")
    pixels = img.getdata()
    img.putdata(
        [
            (r, g, b, 0) if (r > 200 and g > 200 and b > 200) else (r, g, b, a)
            for r, g, b, a in pixels
        ]
    )
    if scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

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


# -------------------------------------------------
# POWERUPS
# -------------------------------------------------

POWERUP_TYPES = ["health", "shield", "autofire", "speed", "triple"]
POWERUP_COLORS = {
    "health": (0, 255, 90, 220),
    "shield": (0, 190, 255, 220),
    "autofire": (255, 70, 255, 220),
    "speed": (255, 220, 0, 220),
    "triple": (255, 130, 0, 220),
}
POWERUP_LABELS = {
    "health": "+HP",
    "shield": "SHIELD",
    "autofire": "AUTO",
    "speed": "SPEED",
    "triple": "TRIPLE",
}


class Powerup(arcade.Sprite):
    def __init__(self, x, y, kind: str):
        super().__init__()
        self.texture = solid_texture(22, POWERUP_COLORS[kind])
        self.center_x = x
        self.center_y = y
        self.kind = kind
        self.change_y = -POWERUP_FALL_SPEED
        self.wobble_phase = random.uniform(0.0, math.tau)

    def update(self, delta_time=1 / 60, *args, **kwargs):
        self.center_y += self.change_y * delta_time
        self.wobble_phase += 4.0 * delta_time
        self.center_x += math.sin(self.wobble_phase) * 18.0 * delta_time


# -------------------------------------------------
# PLAYER
# -------------------------------------------------


class Player(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture = load_texture_clean("image/player.png", 0.15)
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT // 2
        self.health = PLAYER_HEALTH
        self.max_health = PLAYER_HEALTH

        self.change_x = 0.0
        self.change_y = 0.0

        self.shield_active = False
        self.shield_timer = 0.0
        self.autofire_active = False
        self.autofire_timer = 0.0
        self.speed_active = False
        self.speed_timer = 0.0
        self.triple_active = False
        self.triple_timer = 0.0

    def get_speed(self):
        return PLAYER_SPEED * (1.65 if self.speed_active else 1.0)

    def update_powerups(self, delta):
        for attr in ("shield", "autofire", "speed", "triple"):
            if getattr(self, f"{attr}_active"):
                new_t = getattr(self, f"{attr}_timer") - delta
                if new_t <= 0:
                    setattr(self, f"{attr}_active", False)
                    new_t = 0.0
                setattr(self, f"{attr}_timer", new_t)

    def update(self, delta_time=1 / 60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.left = max(self.left, 0)
        self.right = min(self.right, SCREEN_WIDTH)
        self.bottom = max(self.bottom, 0)
        self.top = min(self.top, SCREEN_HEIGHT)

        # Slight banking gives motion feel.
        self.angle = max(-20, min(20, -self.change_x * 0.06))


# -------------------------------------------------
# ENEMIES
# -------------------------------------------------


class Enemy(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture = load_texture_clean("image/enemy.png", 0.12)
        self.center_x = x
        self.center_y = y
        self.health = ENEMY_HEALTH
        self.max_health = ENEMY_HEALTH


class ShootingEnemy(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture = load_texture_clean("image/shooting_enemy.png", 0.12)
        self.center_x = x
        self.center_y = y
        self.health = ENEMY_HEALTH
        self.max_health = ENEMY_HEALTH
        self.shoot_timer = 0.0


class BossEnemy(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture = load_texture_clean("image/boss.png", 0.2)
        self.center_x = x
        self.center_y = y
        self.health = BOSS_HEALTH
        self.max_health = BOSS_HEALTH
        self.normal_timer = 0.0
        self.special_timer = 0.0


# -------------------------------------------------
# BULLETS
# -------------------------------------------------


class Bullet(arcade.Sprite):
    def __init__(self, start_x, start_y, angle_rad, speed=BULLET_SPEED):
        super().__init__()
        self.texture = load_texture_clean("image/bullet.png", 0.1)
        self.center_x = start_x
        self.center_y = start_y
        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle = math.degrees(angle_rad)
        self.life = 2.5

    def update(self, delta_time=1 / 60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life -= delta_time


class EnemyBullet(arcade.Sprite):
    def __init__(self, start_x, start_y, dest_x=None, dest_y=None, angle_rad=None, speed=ENEMY_BULLET_SPEED):
        super().__init__()
        self.texture = load_texture_clean("image/enemy_bullet.png", 0.1)
        self.center_x = start_x
        self.center_y = start_y

        if angle_rad is None:
            angle_rad = math.atan2(dest_y - start_y, dest_x - start_x)

        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle = math.degrees(angle_rad)
        self.life = 3.4

    def update(self, delta_time=1 / 60, *args, **kwargs):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.life -= delta_time


# -------------------------------------------------
# GAME WINDOW
# -------------------------------------------------


class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(BG_COLOR)
        self.set_mouse_visible(False)

        # Pre-warm texture cache before game starts.
        load_texture_clean("image/player.png", 0.15)
        load_texture_clean("image/enemy.png", 0.12)
        load_texture_clean("image/shooting_enemy.png", 0.12)
        load_texture_clean("image/boss.png", 0.2)
        load_texture_clean("image/bullet.png", 0.1)
        load_texture_clean("image/enemy_bullet.png", 0.1)
        for k in POWERUP_TYPES:
            solid_texture(22, POWERUP_COLORS[k])

        # HUD text objects.
        self.txt_score = arcade.Text("SCORE 0", 24, 562, arcade.color.WHITE, 18, bold=True)
        self.txt_health = arcade.Text("HP 100", 24, 536, arcade.color.WHITE, 15)
        self.txt_active = arcade.Text("", 24, 512, arcade.color.YELLOW, 12)
        self.txt_notif = arcade.Text(
            "",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT // 2 + 78,
            (255, 255, 110, 255),
            28,
            anchor_x="center",
            bold=True,
        )
        self.txt_hint = arcade.Text("WASD Move   Hold Mouse Shoot   R Restart", 18, 12, (170, 188, 225), 11)
        self.txt_over = arcade.Text("GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10, (255, 90, 90), 52, anchor_x="center")
        self.txt_score2 = arcade.Text("SCORE 0", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 48, arcade.color.WHITE, 28, anchor_x="center")
        self.txt_restart = arcade.Text("Press R to Restart", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 102, arcade.color.WHITE, 19, anchor_x="center")
        self.txt_combo = arcade.Text("", SCREEN_WIDTH - 18, SCREEN_HEIGHT - 28, (255, 220, 95), 18, anchor_x="right", bold=True)
        self.txt_timer = arcade.Text("", SCREEN_WIDTH - 18, SCREEN_HEIGHT - 52, (180, 210, 255), 14, anchor_x="right")

        self.player = self.player_list = None
        self.enemies = self.shooting_enemies = self.bosses = None
        self.bullets = self.enemy_bullets = self.powerups = None

        self.score = 0
        self.game_over = False
        self.up = self.down = self.left = self.right = False
        self.enemy_spawn = self.shooting_spawn = self.boss_spawn = 0.0
        self.mouse_held = False
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2
        self.fire_timer = 0.0
        self.notif_text = ""
        self.notif_timer = 0.0
        self.notif_color = (255, 255, 110)

        self.bg_time = 0.0
        self.stars = []
        self.particles = []
        self.damage_flash = 0.0
        self.contact_damage_timer = 0.0
        self.time_alive = 0.0
        self.combo = 0
        self.combo_timer = 0.0

    # -------------------------------------------------

    def setup(self):
        self.player = Player()
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)

        self.enemies = arcade.SpriteList()
        self.shooting_enemies = arcade.SpriteList()
        self.bosses = arcade.SpriteList()
        self.bullets = arcade.SpriteList()
        self.enemy_bullets = arcade.SpriteList()
        self.powerups = arcade.SpriteList()

        self.score = 0
        self.game_over = False
        self.enemy_spawn = self.shooting_spawn = self.boss_spawn = 0.0
        self.mouse_held = False
        self.fire_timer = 0.0
        self.notif_text = ""
        self.notif_timer = 0.0
        self.notif_color = (255, 255, 110)
        self.up = self.down = self.left = self.right = False
        self.damage_flash = 0.0
        self.contact_damage_timer = 0.0
        self.time_alive = 0.0
        self.combo = 0
        self.combo_timer = 0.0

        self._build_starfield()
        self.particles = []

    # -------------------------------------------------

    def _build_starfield(self):
        self.stars = []
        for _ in range(STAR_COUNT):
            layer = random.randint(1, 3)
            self.stars.append(
                {
                    "x": random.uniform(0, SCREEN_WIDTH),
                    "y": random.uniform(0, SCREEN_HEIGHT),
                    "size": random.uniform(0.8, 2.3) * (0.85 + layer * 0.2),
                    "speed": random.uniform(18, 52) * layer,
                    "alpha": random.randint(80, 220),
                    "phase": random.uniform(0.0, math.tau),
                    "twinkle": random.uniform(1.2, 3.4),
                }
            )

    def _add_particle(self, x, y, vx, vy, size, life, color, drag):
        if len(self.particles) >= MAX_PARTICLES:
            return
        self.particles.append(
            {
                "x": x,
                "y": y,
                "vx": vx,
                "vy": vy,
                "size": size,
                "life": life,
                "max_life": life,
                "color": color,
                "drag": drag,
            }
        )

    def _burst(self, x, y, count, color, speed_min, speed_max, size_min=1.5, size_max=3.6, life_min=0.2, life_max=0.5, drag=0.93):
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(speed_min, speed_max)
            self._add_particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                size=random.uniform(size_min, size_max),
                life=random.uniform(life_min, life_max),
                color=color,
                drag=drag,
            )

    def _spawn_muzzle(self, x, y, angle_rad):
        for _ in range(4):
            offset = random.uniform(-0.25, 0.25)
            spd = random.uniform(120, 280)
            self._add_particle(
                x=x + math.cos(angle_rad) * random.uniform(6, 14),
                y=y + math.sin(angle_rad) * random.uniform(6, 14),
                vx=math.cos(angle_rad + offset) * spd,
                vy=math.sin(angle_rad + offset) * spd,
                size=random.uniform(1.4, 2.4),
                life=random.uniform(0.08, 0.18),
                color=(255, 220, 120),
                drag=0.88,
            )

    # -------------------------------------------------

    def _draw_background(self):
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, BG_COLOR)

        pulse = (math.sin(self.bg_time * 0.7) + 1.0) * 0.5
        arcade.draw_circle_filled(150, 500, 250 + 20 * pulse, (40, 85, 190, 42))
        arcade.draw_circle_filled(670, 170, 280 + 30 * (1.0 - pulse), (150, 45, 170, 34))
        arcade.draw_circle_filled(420, 640, 280, (30, 160, 200, 18))

        # Subtle moving scan lines.
        offset = (self.bg_time * 14.0) % 28.0
        for y in range(-30, SCREEN_HEIGHT + 30, 28):
            yy = y + offset
            arcade.draw_line(0, yy, SCREEN_WIDTH, yy - 18, (30, 46, 78, 26), 1)

        for star in self.stars:
            twinkle = 0.55 + 0.45 * math.sin(self.bg_time * star["twinkle"] + star["phase"])
            alpha = max(20, min(255, int(star["alpha"] * twinkle)))
            arcade.draw_circle_filled(star["x"], star["y"], star["size"], (205, 228, 255, alpha))

    def _draw_entity_glows(self):
        p = self.player
        base_color = (95, 200, 255, 68)
        if p.speed_active:
            base_color = (255, 230, 90, 82)
        arcade.draw_circle_filled(p.center_x, p.center_y, 34, base_color)

        for e in self.enemies:
            arcade.draw_circle_filled(e.center_x, e.center_y, 24, (255, 92, 92, 45))
        for e in self.shooting_enemies:
            arcade.draw_circle_filled(e.center_x, e.center_y, 26, (255, 130, 90, 55))
        for b in self.bosses:
            radius = 54 + 8 * math.sin(self.bg_time * 2.5)
            arcade.draw_circle_filled(b.center_x, b.center_y, radius, (255, 70, 70, 55))

    def _draw_particles(self):
        for particle in self.particles:
            life_ratio = particle["life"] / particle["max_life"]
            alpha = int(255 * life_ratio)
            radius = max(0.5, particle["size"] * (0.45 + 0.55 * life_ratio))
            c = particle["color"]
            arcade.draw_circle_filled(
                particle["x"],
                particle["y"],
                radius,
                (c[0], c[1], c[2], alpha),
            )

    def _draw_enemy_health_bars(self):
        all_lists = [self.enemies, self.shooting_enemies, self.bosses]
        for sprite_list in all_lists:
            for enemy in sprite_list:
                if enemy.health >= enemy.max_health:
                    continue
                ratio = max(0.0, enemy.health / enemy.max_health)
                left = enemy.center_x - enemy.width * 0.45
                right = enemy.center_x + enemy.width * 0.45
                top = enemy.top + 8
                bottom = top - 5
                arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (35, 25, 25, 220))
                arcade.draw_lrbt_rectangle_filled(
                    left,
                    left + (right - left) * ratio,
                    bottom,
                    top,
                    (255, 100, 90, 235),
                )

    def _draw_hud(self):
        p = self.player

        arcade.draw_lrbt_rectangle_filled(12, 340, 500, 590, (9, 18, 42, 176))
        arcade.draw_lrbt_rectangle_outline(12, 340, 500, 590, (95, 125, 185, 180), 2)

        health_ratio = max(0.0, p.health / p.max_health)
        hp_color = (95, 230, 120) if health_ratio > 0.45 else (255, 180, 80) if health_ratio > 0.2 else (255, 90, 90)
        arcade.draw_lrbt_rectangle_filled(24, 250, 528, 548, (28, 35, 55, 220))
        arcade.draw_lrbt_rectangle_filled(24, 24 + 226 * health_ratio, 528, 548, hp_color)

        self.txt_score.text = f"SCORE {self.score}"
        self.txt_health.text = f"HP {int(max(0, p.health))}"
        self.txt_timer.text = f"TIME {self.time_alive:05.1f}s"

        active = []
        if p.shield_active:
            active.append(f"SHIELD {p.shield_timer:.0f}s")
        if p.autofire_active:
            active.append(f"AUTO {p.autofire_timer:.0f}s")
        if p.speed_active:
            active.append(f"SPEED {p.speed_timer:.0f}s")
        if p.triple_active:
            active.append(f"TRIPLE {p.triple_timer:.0f}s")
        self.txt_active.text = ("ACTIVE: " + "   ".join(active)) if active else ""

        self.txt_score.draw()
        self.txt_health.draw()
        self.txt_timer.draw()
        if active:
            self.txt_active.draw()

        if self.combo > 1 and self.combo_timer > 0:
            self.txt_combo.text = f"x{self.combo} COMBO"
            self.txt_combo.draw()

        if self.notif_timer > 0:
            alpha = min(255, int(self.notif_timer * 280))
            self.txt_notif.text = self.notif_text
            c = self.notif_color
            self.txt_notif.color = (c[0], c[1], c[2], alpha)
            self.txt_notif.draw()

        self.txt_hint.draw()

    def _draw_crosshair(self):
        x = self.mouse_x
        y = self.mouse_y
        arcade.draw_circle_outline(x, y, 13, (130, 220, 255, 185), 2)
        arcade.draw_line(x - 20, y, x - 8, y, (130, 220, 255, 185), 2)
        arcade.draw_line(x + 8, y, x + 20, y, (130, 220, 255, 185), 2)
        arcade.draw_line(x, y - 20, x, y - 8, (130, 220, 255, 185), 2)
        arcade.draw_line(x, y + 8, x, y + 20, (130, 220, 255, 185), 2)

    # -------------------------------------------------

    def on_draw(self):
        self.clear()
        self._draw_background()

        if not self.game_over:
            self._draw_entity_glows()

        self.powerups.draw()
        self.player_list.draw()
        self.enemies.draw()
        self.shooting_enemies.draw()
        self.bosses.draw()
        self.bullets.draw()
        self.enemy_bullets.draw()

        # Bullet glow trails.
        for b in self.bullets:
            arcade.draw_circle_filled(b.center_x, b.center_y, 6, (255, 200, 110, 55))
        for b in self.enemy_bullets:
            arcade.draw_circle_filled(b.center_x, b.center_y, 7, (255, 85, 85, 55))

        # Shield ring.
        if self.player.shield_active:
            ring_r = 38 + 2.5 * math.sin(self.bg_time * 9.0)
            arcade.draw_circle_outline(self.player.center_x, self.player.center_y, ring_r, (90, 235, 255, 230), 3)

        # Powerup labels.
        for powerup in self.powerups:
            arcade.draw_text(
                POWERUP_LABELS[powerup.kind],
                powerup.center_x,
                powerup.center_y - 8,
                arcade.color.WHITE,
                9,
                anchor_x="center",
            )

        self._draw_enemy_health_bars()
        self._draw_particles()
        self._draw_hud()

        if self.damage_flash > 0:
            alpha = int(170 * self.damage_flash)
            arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (255, 65, 65, alpha))

        self._draw_crosshair()

        if self.game_over:
            arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (3, 6, 18, 165))
            self.txt_score2.text = f"SCORE {self.score}"
            self.txt_over.draw()
            self.txt_score2.draw()
            self.txt_restart.draw()

    # -------------------------------------------------

    def _update_starfield(self, delta):
        flow_boost = 1.0 + min(0.9, self.time_alive / 80.0)
        for star in self.stars:
            star["y"] -= star["speed"] * flow_boost * delta
            if star["y"] < -6:
                star["y"] = SCREEN_HEIGHT + random.uniform(4, 60)
                star["x"] = random.uniform(0, SCREEN_WIDTH)

    def _update_particles(self, delta):
        alive = []
        for particle in self.particles:
            particle["life"] -= delta
            if particle["life"] <= 0:
                continue
            particle["x"] += particle["vx"] * delta
            particle["y"] += particle["vy"] * delta
            particle["vx"] *= particle["drag"]
            particle["vy"] *= particle["drag"]
            alive.append(particle)
        self.particles = alive

    # -------------------------------------------------

    def on_update(self, delta_time):
        delta = min(0.05, delta_time)
        self.bg_time += delta

        self._update_starfield(delta)
        self._update_particles(delta)

        if self.notif_timer > 0:
            self.notif_timer -= delta
        if self.damage_flash > 0:
            self.damage_flash = max(0.0, self.damage_flash - 2.6 * delta)
        if self.contact_damage_timer > 0:
            self.contact_damage_timer -= delta
        if self.combo_timer > 0:
            self.combo_timer -= delta
        elif self.combo > 0:
            self.combo = 0

        if self.game_over:
            return

        self.time_alive += delta
        p = self.player

        input_x = float(self.right) - float(self.left)
        input_y = float(self.up) - float(self.down)
        if input_x != 0 and input_y != 0:
            inv_len = 0.70710678
            input_x *= inv_len
            input_y *= inv_len

        target_x = input_x * p.get_speed()
        target_y = input_y * p.get_speed()
        smooth = min(1.0, 14.0 * delta)
        p.change_x += (target_x - p.change_x) * smooth
        p.change_y += (target_y - p.change_y) * smooth

        p.update(delta)
        p.update_powerups(delta)

        # Engine particles.
        moving = abs(p.change_x) + abs(p.change_y)
        if moving > 130 and random.random() < 0.55:
            angle = math.atan2(-p.change_y, -p.change_x) + random.uniform(-0.5, 0.5)
            speed = random.uniform(80, 160)
            self._add_particle(
                x=p.center_x + random.uniform(-4, 4),
                y=p.center_y - 8 + random.uniform(-3, 3),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                size=random.uniform(1.4, 2.8),
                life=random.uniform(0.12, 0.24),
                color=(120, 205, 255),
                drag=0.9,
            )

        # Firing.
        firing = self.mouse_held or p.autofire_active
        if firing:
            rate = AUTO_FIRE_RATE if p.autofire_active else NORMAL_FIRE_RATE
            self.fire_timer += delta
            while self.fire_timer >= rate:
                if p.autofire_active:
                    target = self._nearest_enemy()
                    if target:
                        self._shoot_toward(target.center_x, target.center_y)
                    else:
                        self._shoot_toward(self.mouse_x, self.mouse_y)
                else:
                    self._shoot_toward(self.mouse_x, self.mouse_y)
                self.fire_timer -= rate

        self.bullets.update(delta)
        self.enemy_bullets.update(delta)
        self.powerups.update(delta)

        # Cull off-screen / expired.
        for b in list(self.bullets):
            if (
                b.life <= 0
                or b.right < -30
                or b.left > SCREEN_WIDTH + 30
                or b.top < -30
                or b.bottom > SCREEN_HEIGHT + 30
            ):
                b.remove_from_sprite_lists()
        for b in list(self.enemy_bullets):
            if (
                b.life <= 0
                or b.right < -30
                or b.left > SCREEN_WIDTH + 30
                or b.top < -30
                or b.bottom > SCREEN_HEIGHT + 30
            ):
                b.remove_from_sprite_lists()
        for powerup in list(self.powerups):
            if powerup.top < -10:
                powerup.remove_from_sprite_lists()

        # Dynamic spawn cadence.
        difficulty = min(1.6, self.time_alive / 90.0)
        enemy_interval = max(0.42, 1.0 - 0.45 * difficulty)
        shooting_interval = max(1.2, 3.0 - 1.35 * difficulty)
        boss_interval = max(10.5, 20.0 - 6.0 * difficulty)

        self.enemy_spawn += delta
        if self.enemy_spawn >= enemy_interval:
            self.spawn_enemy()
            self.enemy_spawn = 0.0

        self.shooting_spawn += delta
        if self.shooting_spawn >= shooting_interval:
            self.spawn_shooting_enemy()
            self.shooting_spawn = 0.0

        self.boss_spawn += delta
        if self.boss_spawn >= boss_interval:
            self.spawn_boss()
            self.boss_spawn = 0.0

        self.update_enemies(delta, difficulty)
        self.check_collisions()

    # -------------------------------------------------

    def _nearest_enemy(self):
        all_e = list(self.enemies) + list(self.shooting_enemies) + list(self.bosses)
        if not all_e:
            return None
        px, py = self.player.center_x, self.player.center_y
        return min(all_e, key=lambda e: math.hypot(e.center_x - px, e.center_y - py))

    def _shoot_toward(self, tx, ty):
        px, py = self.player.center_x, self.player.center_y
        base_angle = math.atan2(ty - py, tx - px)
        offsets = [-0.18, 0.0, 0.18] if self.player.triple_active else [0.0]
        for offset in offsets:
            ang = base_angle + offset
            self.bullets.append(Bullet(px, py, ang))
            self._spawn_muzzle(px, py, ang)

    # -------------------------------------------------

    def update_enemies(self, delta, difficulty):
        p = self.player

        for enemy in self.enemies:
            a = math.atan2(p.center_y - enemy.center_y, p.center_x - enemy.center_x)
            speed = ENEMY_SPEED * (1.0 + 0.16 * difficulty)
            enemy.center_x += math.cos(a) * speed * delta
            enemy.center_y += math.sin(a) * speed * delta
            enemy.angle = math.degrees(a) - 90

        for enemy in self.shooting_enemies:
            a = math.atan2(p.center_y - enemy.center_y, p.center_x - enemy.center_x)
            speed = ENEMY_SPEED * (0.9 + 0.16 * difficulty)
            enemy.center_x += math.cos(a) * speed * delta
            enemy.center_y += math.sin(a) * speed * delta
            enemy.angle = math.degrees(a) - 90

            enemy.shoot_timer += delta
            shoot_rate = max(0.6, 1.1 - 0.25 * difficulty)
            if enemy.shoot_timer >= shoot_rate:
                self.enemy_bullets.append(
                    EnemyBullet(enemy.center_x, enemy.center_y, p.center_x, p.center_y)
                )
                enemy.shoot_timer = 0.0

        for boss in self.bosses:
            a = math.atan2(p.center_y - boss.center_y, p.center_x - boss.center_x)
            speed = BOSS_SPEED * (0.95 + 0.12 * difficulty)
            boss.center_x += math.cos(a) * speed * delta
            boss.center_y += math.sin(a) * speed * delta
            boss.angle = math.degrees(a) - 90

            boss.normal_timer += delta
            boss.special_timer += delta

            if boss.normal_timer >= 1.45:
                self.enemy_bullets.append(EnemyBullet(boss.center_x, boss.center_y, p.center_x, p.center_y))
                boss.normal_timer = 0.0

            if boss.special_timer >= 4.8:
                base = math.atan2(p.center_y - boss.center_y, p.center_x - boss.center_x)
                for spread in (-0.52, -0.26, 0.0, 0.26, 0.52):
                    self.enemy_bullets.append(
                        EnemyBullet(
                            boss.center_x,
                            boss.center_y,
                            angle_rad=base + spread,
                            speed=ENEMY_BULLET_SPEED * 1.05,
                        )
                    )
                self._burst(boss.center_x, boss.center_y, 16, (255, 100, 100), 60, 170, 2.0, 3.8, 0.15, 0.35)
                boss.special_timer = 0.0

    # -------------------------------------------------

    def check_collisions(self):
        p = self.player

        for bullet in list(self.bullets):
            hits = arcade.check_for_collision_with_lists(bullet, [self.enemies, self.shooting_enemies, self.bosses])
            if not hits:
                continue

            enemy = hits[0]
            enemy.health -= 20
            self._burst(bullet.center_x, bullet.center_y, 6, (255, 220, 140), 70, 190, 1.2, 2.2, 0.08, 0.2)
            bullet.remove_from_sprite_lists()

            if enemy.health <= 0:
                is_boss = isinstance(enemy, BossEnemy)
                base_points = 70 if is_boss else 12
                combo_bonus = min(24, self.combo * 2)
                self.score += base_points + combo_bonus
                self.combo += 1
                self.combo_timer = 2.0

                self._try_drop_powerup(enemy.center_x, enemy.center_y, is_boss)
                if is_boss:
                    self._burst(enemy.center_x, enemy.center_y, 64, (255, 100, 80), 70, 320, 2.3, 4.8, 0.25, 0.65)
                else:
                    self._burst(enemy.center_x, enemy.center_y, 24, (255, 145, 90), 55, 240, 1.7, 3.5, 0.2, 0.45)
                enemy.remove_from_sprite_lists()

        for b in list(self.enemy_bullets):
            if not arcade.check_for_collision(b, p):
                continue

            hit_x, hit_y = b.center_x, b.center_y
            b.remove_from_sprite_lists()
            if p.shield_active:
                self._burst(hit_x, hit_y, 10, (110, 230, 255), 80, 220, 1.2, 2.8, 0.1, 0.24)
            else:
                p.health -= 10
                self.combo = 0
                self.damage_flash = max(self.damage_flash, 0.95)
                self._burst(hit_x, hit_y, 18, (255, 95, 95), 90, 260, 1.6, 3.4, 0.15, 0.32)

        touching = arcade.check_for_collision_with_lists(p, [self.enemies, self.shooting_enemies, self.bosses])
        if touching and self.contact_damage_timer <= 0:
            self.contact_damage_timer = CONTACT_DAMAGE_COOLDOWN
            if p.shield_active:
                self._burst(p.center_x, p.center_y, 14, (100, 230, 255), 70, 180, 1.6, 3.2, 0.1, 0.24)
            else:
                p.health -= CONTACT_DAMAGE
                self.combo = 0
                self.damage_flash = max(self.damage_flash, 1.0)
                self._burst(p.center_x, p.center_y, 24, (255, 80, 80), 90, 260, 1.8, 4.0, 0.16, 0.36)

        for pu in list(self.powerups):
            if arcade.check_for_collision(pu, p):
                self._apply_powerup(pu.kind)
                c = POWERUP_COLORS[pu.kind]
                self._burst(pu.center_x, pu.center_y, 20, (c[0], c[1], c[2]), 70, 240, 1.4, 3.0, 0.12, 0.32)
                pu.remove_from_sprite_lists()

        if p.health <= 0 and not self.game_over:
            self.game_over = True
            self.mouse_held = False
            self._burst(p.center_x, p.center_y, 85, (255, 75, 75), 80, 360, 2.0, 5.0, 0.25, 0.75)

    # -------------------------------------------------

    def _try_drop_powerup(self, x, y, boss=False):
        if random.randint(1, 100) <= (100 if boss else DROP_CHANCE):
            self.powerups.append(Powerup(x, y, random.choice(POWERUP_TYPES)))

    def _apply_powerup(self, kind):
        p = self.player

        notif = {
            "health": ("+30 HEALTH!", (130, 255, 130)),
            "shield": ("SHIELD ONLINE!", (110, 230, 255)),
            "autofire": ("AUTO-FIRE!", (255, 130, 255)),
            "speed": ("SPEED BOOST!", (255, 220, 120)),
            "triple": ("TRIPLE SHOT!", (255, 180, 120)),
        }
        self.notif_text, self.notif_color = notif[kind]
        self.notif_timer = 1.4

        if kind == "health":
            p.health = min(PLAYER_HEALTH, p.health + 30)
        elif kind == "shield":
            p.shield_active = True
            p.shield_timer = POWERUP_DURATION
        elif kind == "autofire":
            p.autofire_active = True
            p.autofire_timer = POWERUP_DURATION
        elif kind == "speed":
            p.speed_active = True
            p.speed_timer = POWERUP_DURATION
        elif kind == "triple":
            p.triple_active = True
            p.triple_timer = POWERUP_DURATION

    # -------------------------------------------------

    def spawn_enemy(self):
        x = random.randint(40, SCREEN_WIDTH - 40)
        y = SCREEN_HEIGHT + 20
        self.enemies.append(Enemy(x, y))

    def spawn_shooting_enemy(self):
        x = random.randint(50, SCREEN_WIDTH - 50)
        y = SCREEN_HEIGHT + 30
        self.shooting_enemies.append(ShootingEnemy(x, y))

    def spawn_boss(self):
        x = random.randint(140, SCREEN_WIDTH - 140)
        self.bosses.append(BossEnemy(x, SCREEN_HEIGHT + 55))
        self.notif_text = "BOSS INCOMING!"
        self.notif_color = (255, 120, 120)
        self.notif_timer = 1.6

    # -------------------------------------------------

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x
        self.mouse_y = y

    def on_mouse_press(self, x, y, button, modifiers):
        if self.game_over:
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.mouse_held = True
        self.mouse_x = x
        self.mouse_y = y
        self._shoot_toward(x, y)
        self.fire_timer = 0.0

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.mouse_held = False

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W:
            self.up = True
        if key == arcade.key.S:
            self.down = True
        if key == arcade.key.A:
            self.left = True
        if key == arcade.key.D:
            self.right = True
        if key == arcade.key.R and self.game_over:
            self.setup()
        if key == arcade.key.ESCAPE:
            self.close()

    def on_key_release(self, key, modifiers):
        if key == arcade.key.W:
            self.up = False
        if key == arcade.key.S:
            self.down = False
        if key == arcade.key.A:
            self.left = False
        if key == arcade.key.D:
            self.right = False


# -------------------------------------------------
# MAIN
# -------------------------------------------------


def main():
    game = GameWindow()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()