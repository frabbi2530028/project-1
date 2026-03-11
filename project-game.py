import arcade
import random
import math
from PIL import Image

# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------

SCREEN_WIDTH        = 800
SCREEN_HEIGHT       = 600
SCREEN_TITLE        = "Space Shooter"

PLAYER_SPEED        = 5
ENEMY_SPEED         = 2
BOSS_SPEED          = 1

PLAYER_HEALTH       = 100
ENEMY_HEALTH        = 30
BOSS_HEALTH         = 200

BULLET_SPEED        = 10
ENEMY_BULLET_SPEED  = 7

NORMAL_FIRE_RATE    = 0.25
AUTO_FIRE_RATE      = 0.08

POWERUP_DURATION    = 10.0
DROP_CHANCE         = 40


# -------------------------------------------------
# TEXTURE CACHE  — load each image ONCE, reuse forever
# -------------------------------------------------

_texture_cache: dict = {}

def load_texture_clean(path: str, scale: float = 1.0) -> arcade.Texture:
    key = (path, scale)
    if key in _texture_cache:
        return _texture_cache[key]
    img = Image.open(path).convert("RGBA")
    pixels = img.getdata()
    img.putdata([
        (r, g, b, 0) if (r > 200 and g > 200 and b > 200) else (r, g, b, a)
        for r, g, b, a in pixels
    ])
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
# POWERUP
# -------------------------------------------------

POWERUP_TYPES  = ["health", "shield", "autofire", "speed", "triple"]
POWERUP_COLORS = {
    "health":   (0,   255, 80,  220),
    "shield":   (0,   180, 255, 220),
    "autofire": (255, 60,  255, 220),
    "speed":    (255, 220, 0,   220),
    "triple":   (255, 120, 0,   220),
}
POWERUP_LABELS = {
    "health":   "+HP",
    "shield":   "SHIELD",
    "autofire": "AUTO",
    "speed":    "SPEED",
    "triple":   "TRIPLE",
}

class Powerup(arcade.Sprite):
    def __init__(self, x, y, kind: str):
        super().__init__()
        self.texture  = solid_texture(22, POWERUP_COLORS[kind])
        self.center_x = x
        self.center_y = y
        self.kind     = kind
        self.change_y = -1.5

    def update(self, delta_time=0, *args, **kwargs):
        self.center_y += self.change_y


# -------------------------------------------------
# PLAYER
# -------------------------------------------------

class Player(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture  = load_texture_clean("image/player.png", 0.15)
        self.center_x = SCREEN_WIDTH  // 2
        self.center_y = SCREEN_HEIGHT // 2
        self.health   = PLAYER_HEALTH

        self.shield_active   = False;  self.shield_timer   = 0.0
        self.autofire_active = False;  self.autofire_timer = 0.0
        self.speed_active    = False;  self.speed_timer    = 0.0
        self.triple_active   = False;  self.triple_timer   = 0.0

    def get_speed(self):
        return PLAYER_SPEED * (1.8 if self.speed_active else 1.0)

    def update_powerups(self, delta):
        for attr in ("shield", "autofire", "speed", "triple"):
            if getattr(self, f"{attr}_active"):
                new_t = getattr(self, f"{attr}_timer") - delta
                if new_t <= 0:
                    setattr(self, f"{attr}_active", False)
                    new_t = 0.0
                setattr(self, f"{attr}_timer", new_t)

    def update(self, delta_time=0, *args, **kwargs):
        self.center_x += self.change_x
        self.center_y += self.change_y
        self.left   = max(self.left,   0)
        self.right  = min(self.right,  SCREEN_WIDTH)
        self.bottom = max(self.bottom, 0)
        self.top    = min(self.top,    SCREEN_HEIGHT)


# -------------------------------------------------
# ENEMIES
# -------------------------------------------------

class Enemy(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture  = load_texture_clean("image/enemy.png", 0.12)
        self.center_x = x;  self.center_y = y
        self.health   = ENEMY_HEALTH

class ShootingEnemy(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture     = load_texture_clean("image/shooting_enemy.png", 0.12)
        self.center_x    = x;  self.center_y = y
        self.health      = ENEMY_HEALTH
        self.shoot_timer = 0

class BossEnemy(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture       = load_texture_clean("image/boss.png", 0.2)
        self.center_x      = x;  self.center_y = y
        self.health        = BOSS_HEALTH
        self.normal_timer  = 0
        self.special_timer = 0


# -------------------------------------------------
# BULLETS  — texture assigned from cache, no disk I/O
# -------------------------------------------------

class Bullet(arcade.Sprite):
    def __init__(self, start_x, start_y, angle_rad, speed=BULLET_SPEED):
        super().__init__()
        self.texture  = load_texture_clean("image/bullet.png", 0.1)
        self.center_x = start_x
        self.center_y = start_y
        self.change_x = math.cos(angle_rad) * speed
        self.change_y = math.sin(angle_rad) * speed
        self.angle    = math.degrees(angle_rad)

class EnemyBullet(arcade.Sprite):
    def __init__(self, start_x, start_y, dest_x, dest_y):
        super().__init__()
        self.texture  = load_texture_clean("image/enemy_bullet.png", 0.1)
        self.center_x = start_x;  self.center_y = start_y
        a = math.atan2(dest_y - start_y, dest_x - start_x)
        self.change_x = math.cos(a) * ENEMY_BULLET_SPEED
        self.change_y = math.sin(a) * ENEMY_BULLET_SPEED
        self.angle    = math.degrees(a)


# -------------------------------------------------
# GAME WINDOW
# -------------------------------------------------

class GameWindow(arcade.Window):

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)

        # Pre-warm texture cache before game starts
        load_texture_clean("image/player.png",       0.15)
        load_texture_clean("image/enemy.png",         0.12)
        load_texture_clean("image/shooting_enemy.png",0.12)
        load_texture_clean("image/boss.png",          0.2)
        load_texture_clean("image/bullet.png",        0.1)
        load_texture_clean("image/enemy_bullet.png",  0.1)
        for k in POWERUP_TYPES:
            solid_texture(22, POWERUP_COLORS[k])

        # Pre-build Text objects (fast GPU text, no per-frame cost)
        self.txt_score   = arcade.Text("Score: 0",    10, 570, arcade.color.WHITE, 18)
        self.txt_health  = arcade.Text("Health: 100", 10, 540, arcade.color.WHITE, 18)
        self.txt_active  = arcade.Text("",            10, 510, arcade.color.YELLOW, 13)
        self.txt_notif   = arcade.Text("", SCREEN_WIDTH//2, SCREEN_HEIGHT//2+80,
                                       (255,255,100,255), 28,
                                       anchor_x="center", bold=True)
        self.txt_hint    = arcade.Text("WASD=Move  Hold Mouse=Auto-aim & Shoot",
                                       10, 10, arcade.color.LIGHT_GRAY, 12)
        self.txt_over    = arcade.Text("GAME OVER", SCREEN_WIDTH//2, SCREEN_HEIGHT//2,
                                       arcade.color.RED, 50, anchor_x="center")
        self.txt_score2  = arcade.Text("Score: 0", SCREEN_WIDTH//2, SCREEN_HEIGHT//2-60,
                                       arcade.color.WHITE, 30, anchor_x="center")
        self.txt_restart = arcade.Text("Press R to Restart",
                                       SCREEN_WIDTH//2, SCREEN_HEIGHT//2-120,
                                       arcade.color.WHITE, 20, anchor_x="center")

        self.player = self.player_list = None
        self.enemies = self.shooting_enemies = self.bosses = None
        self.bullets = self.enemy_bullets = self.powerups = None

        self.score = 0;  self.game_over = False
        self.up = self.down = self.left = self.right = False
        self.enemy_spawn = self.shooting_spawn = self.boss_spawn = 0
        self.mouse_held = False
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2
        self.fire_timer  = 0.0
        self.notif_text  = ""
        self.notif_timer = 0.0

    # -------------------------------------------------

    def setup(self):
        self.player      = Player()
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)

        self.enemies          = arcade.SpriteList()
        self.shooting_enemies = arcade.SpriteList()
        self.bosses           = arcade.SpriteList()
        self.bullets          = arcade.SpriteList()
        self.enemy_bullets    = arcade.SpriteList()
        self.powerups         = arcade.SpriteList()

        self.score = 0;  self.game_over = False
        self.mouse_held = False;  self.fire_timer = 0.0
        self.notif_text = "";     self.notif_timer = 0.0
        self.enemy_spawn = self.shooting_spawn = self.boss_spawn = 0
        self.up = self.down = self.left = self.right = False

    # -------------------------------------------------

    def on_draw(self):
        self.clear()

        if self.game_over:
            self.txt_score2.text = f"Score: {self.score}"
            self.txt_over.draw();  self.txt_score2.draw();  self.txt_restart.draw()
            return

        self.powerups.draw()
        self.player_list.draw()
        self.enemies.draw()
        self.shooting_enemies.draw()
        self.bosses.draw()
        self.bullets.draw()
        self.enemy_bullets.draw()

        # Shield ring
        if self.player.shield_active:
            arcade.draw_circle_outline(
                self.player.center_x, self.player.center_y,
                40, arcade.color.CYAN, 3)

        # Powerup labels on pickups
        for p in self.powerups:
            arcade.draw_text(POWERUP_LABELS[p.kind],
                p.center_x, p.center_y - 8,
                arcade.color.WHITE, 9, anchor_x="center")

        # HUD (Text objects — fast)
        self.txt_score.text  = f"Score: {self.score}"
        self.txt_health.text = f"Health: {self.player.health}"

        active = []
        if self.player.shield_active:   active.append(f"SHIELD {self.player.shield_timer:.0f}s")
        if self.player.autofire_active: active.append(f"AUTO {self.player.autofire_timer:.0f}s")
        if self.player.speed_active:    active.append(f"SPEED {self.player.speed_timer:.0f}s")
        if self.player.triple_active:   active.append(f"TRIPLE {self.player.triple_timer:.0f}s")
        self.txt_active.text = ("Active: " + "  |  ".join(active)) if active else ""

        self.txt_score.draw()
        self.txt_health.draw()
        if active: self.txt_active.draw()

        if self.notif_timer > 0:
            alpha = min(255, int(self.notif_timer * 200))
            self.txt_notif.text  = self.notif_text
            self.txt_notif.color = (255, 255, 100, alpha)
            self.txt_notif.draw()

        self.txt_hint.draw()

    # -------------------------------------------------

    def on_update(self, delta_time):
        if self.game_over:
            return

        p   = self.player
        spd = p.get_speed()
        p.change_x = 0;  p.change_y = 0
        if self.up:    p.change_y =  spd
        if self.down:  p.change_y = -spd
        if self.left:  p.change_x = -spd
        if self.right: p.change_x =  spd
        # Normalize diagonal so speed stays consistent
        if p.change_x != 0 and p.change_y != 0:
            p.change_x *= 0.7071
            p.change_y *= 0.7071

        p.update()
        p.update_powerups(delta_time)

        # Firing — always targets nearest enemy when mouse held or autofire active
        if p.autofire_active or self.mouse_held:
            rate = AUTO_FIRE_RATE if p.autofire_active else NORMAL_FIRE_RATE
            self.fire_timer += delta_time
            if self.fire_timer >= rate:
                target = self._nearest_enemy()
                if target:
                    self._shoot_toward(target.center_x, target.center_y)
                self.fire_timer = 0.0

        self.bullets.update()
        self.enemy_bullets.update()
        self.powerups.update()

        # Cull off-screen objects
        for b in list(self.bullets):
            if b.right < 0 or b.left > SCREEN_WIDTH or b.top < 0 or b.bottom > SCREEN_HEIGHT:
                b.remove_from_sprite_lists()
        for b in list(self.enemy_bullets):
            if b.right < 0 or b.left > SCREEN_WIDTH or b.top < 0 or b.bottom > SCREEN_HEIGHT:
                b.remove_from_sprite_lists()
        for pu in list(self.powerups):
            if pu.top < 0:
                pu.remove_from_sprite_lists()

        # Spawn
        self.enemy_spawn += delta_time
        if self.enemy_spawn > 1:
            self.spawn_enemy();  self.enemy_spawn = 0

        self.shooting_spawn += delta_time
        if self.shooting_spawn > 3:
            self.spawn_shooting_enemy();  self.shooting_spawn = 0

        self.boss_spawn += delta_time
        if self.boss_spawn > 20:
            self.spawn_boss();  self.boss_spawn = 0

        if self.notif_timer > 0:
            self.notif_timer -= delta_time

        self.update_enemies(delta_time)
        self.check_collisions()

    # -------------------------------------------------

    def _nearest_enemy(self):
        all_e = list(self.enemies) + list(self.shooting_enemies) + list(self.bosses)
        if not all_e:
            return None
        px, py = self.player.center_x, self.player.center_y
        return min(all_e, key=lambda e: math.hypot(e.center_x - px, e.center_y - py))

    def _shoot_toward(self, tx, ty):
        px, py     = self.player.center_x, self.player.center_y
        base_angle = math.atan2(ty - py, tx - px)
        offsets    = [-0.18, 0.0, 0.18] if self.player.triple_active else [0.0]
        for off in offsets:
            self.bullets.append(Bullet(px, py, base_angle + off))

    # -------------------------------------------------

    def update_enemies(self, delta):
        for enemy in self.enemies:
            a = math.atan2(self.player.center_y - enemy.center_y,
                           self.player.center_x - enemy.center_x)
            enemy.change_x = math.cos(a) * ENEMY_SPEED
            enemy.change_y = math.sin(a) * ENEMY_SPEED
            enemy.update()

        for enemy in self.shooting_enemies:
            a = math.atan2(self.player.center_y - enemy.center_y,
                           self.player.center_x - enemy.center_x)
            enemy.change_x = math.cos(a) * ENEMY_SPEED
            enemy.change_y = math.sin(a) * ENEMY_SPEED
            enemy.update()
            enemy.shoot_timer += delta
            if enemy.shoot_timer > 1:
                self.enemy_bullets.append(EnemyBullet(
                    enemy.center_x, enemy.center_y,
                    self.player.center_x, self.player.center_y))
                enemy.shoot_timer = 0

        for boss in self.bosses:
            a = math.atan2(self.player.center_y - boss.center_y,
                           self.player.center_x - boss.center_x)
            boss.change_x = math.cos(a) * BOSS_SPEED
            boss.change_y = math.sin(a) * BOSS_SPEED
            boss.update()
            boss.normal_timer += delta
            if boss.normal_timer > 2:
                self.enemy_bullets.append(EnemyBullet(
                    boss.center_x, boss.center_y,
                    self.player.center_x, self.player.center_y))
                boss.normal_timer = 0

    # -------------------------------------------------

    def check_collisions(self):
        p = self.player

        for bullet in list(self.bullets):
            hits = arcade.check_for_collision_with_lists(
                bullet, [self.enemies, self.shooting_enemies, self.bosses])
            for enemy in hits:
                enemy.health -= 20
                bullet.remove_from_sprite_lists()
                if enemy.health <= 0:
                    self.score += 50 if isinstance(enemy, BossEnemy) else 10
                    self._try_drop_powerup(enemy.center_x, enemy.center_y,
                                           isinstance(enemy, BossEnemy))
                    enemy.remove_from_sprite_lists()
                break

        for b in list(self.enemy_bullets):
            if arcade.check_for_collision(b, p):
                b.remove_from_sprite_lists()
                if not p.shield_active:
                    p.health -= 10

        for e in arcade.check_for_collision_with_lists(
                p, [self.enemies, self.shooting_enemies, self.bosses]):
            if not p.shield_active:
                p.health -= 1

        for pu in list(self.powerups):
            if arcade.check_for_collision(pu, p):
                self._apply_powerup(pu.kind)
                pu.remove_from_sprite_lists()

        if p.health <= 0:
            self.game_over = True

    # -------------------------------------------------

    def _try_drop_powerup(self, x, y, boss=False):
        if random.randint(1, 100) <= (100 if boss else DROP_CHANCE):
            self.powerups.append(Powerup(x, y, random.choice(POWERUP_TYPES)))

    def _apply_powerup(self, kind):
        p = self.player
        self.notif_text  = {"health": "+30 HEALTH!", "shield": "SHIELD ON!",
                             "autofire": "AUTO-FIRE!", "speed": "SPEED BOOST!",
                             "triple": "TRIPLE SHOT!"}[kind]
        self.notif_timer = 1.5
        if kind == "health":
            p.health = min(PLAYER_HEALTH, p.health + 30)
        elif kind == "shield":
            p.shield_active = True;   p.shield_timer   = POWERUP_DURATION
        elif kind == "autofire":
            p.autofire_active = True; p.autofire_timer = POWERUP_DURATION
        elif kind == "speed":
            p.speed_active = True;    p.speed_timer    = POWERUP_DURATION
        elif kind == "triple":
            p.triple_active = True;   p.triple_timer   = POWERUP_DURATION

    # -------------------------------------------------

    def spawn_enemy(self):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":      x, y = random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 20
        elif side == "bottom": x, y = random.randint(0, SCREEN_WIDTH), -20
        elif side == "left":   x, y = -20, random.randint(0, SCREEN_HEIGHT)
        else:                  x, y = SCREEN_WIDTH + 20, random.randint(0, SCREEN_HEIGHT)
        self.enemies.append(Enemy(x, y))

    def spawn_shooting_enemy(self):
        self.shooting_enemies.append(
            ShootingEnemy(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 20))

    def spawn_boss(self):
        self.bosses.append(BossEnemy(SCREEN_WIDTH // 2, SCREEN_HEIGHT + 50))

    # -------------------------------------------------

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x;  self.mouse_y = y

    def on_mouse_press(self, x, y, button, modifiers):
        if self.game_over: return
        self.mouse_held = True
        self.mouse_x = x;  self.mouse_y = y
        # Fire immediately at nearest enemy on click
        target = self._nearest_enemy()
        if target:
            self._shoot_toward(target.center_x, target.center_y)
        self.fire_timer = 0.0

    def on_mouse_release(self, x, y, button, modifiers):
        self.mouse_held = False

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W: self.up    = True
        if key == arcade.key.S: self.down  = True
        if key == arcade.key.A: self.left  = True
        if key == arcade.key.D: self.right = True
        if key == arcade.key.R and self.game_over: self.setup()

    def on_key_release(self, key, modifiers):
        if key == arcade.key.W: self.up    = False
        if key == arcade.key.S: self.down  = False
        if key == arcade.key.A: self.left  = False
        if key == arcade.key.D: self.right = False


# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():


    game = GameWindow()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()