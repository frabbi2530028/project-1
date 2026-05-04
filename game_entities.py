import arcade
import math
import random

from PIL import Image, ImageDraw

from game_config import *
from game_assets import (
    _make_powerup_texture,
    _texture_cache,
    load_texture_clean,
)

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
        self.speed_active    = False;  self.speed_timer    = 0.0
        self.triple_active   = False;  self.triple_timer   = 0.0
        self.beam360_active  = False;  self.beam360_timer  = 0.0
        self.elec360_active  = False;  self.elec360_timer  = 0.0

        self.inventory = {"speed": 0, "shield": 0, "triple": 0,
                          "beam360": 0, "elec360": 0}

    def get_speed(self):
        engine = getattr(self, "_engine_bonus", 1.0)
        return PLAYER_SPEED * engine * (1.65 if self.speed_active else 1.0)

    def update_powerups(self, delta):
        for attr in ("shield", "speed", "triple", "beam360", "elec360"):
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
#  GAME WINDOW
# ═════════════════════════════════════════════════════
