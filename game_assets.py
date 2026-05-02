import arcade
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from game_config import *

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
    # Cockpit glowff
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


def _draw_texture_fitted(texture: arcade.Texture, center_x: float, center_y: float,
                         max_width: float, max_height: float) -> None:
    """Draw a texture scaled to fit inside a bounded box."""
    if texture.width <= 0 or texture.height <= 0:
        return

    scale = min(max_width / texture.width, max_height / texture.height)
    draw_w = max(1, texture.width * scale)
    draw_h = max(1, texture.height * scale)
    try:
        arcade.draw_texture_rect(texture, arcade.XYWH(center_x, center_y, draw_w, draw_h))
    except (AttributeError, TypeError):
        sprite = arcade.Sprite()
        sprite.texture = texture
        sprite.center_x = center_x
        sprite.center_y = center_y
        sprite.scale = scale
        sprite.draw()


# ─────────────────────────────────────────────────────
#  POWERUPS
# ─────────────────────────────────────────────────────

POWERUP_TYPES  = ["health", "shield", "speed", "triple", "beam360", "elec360"]
POWERUP_COLORS = {
    "health":   (0,   255, 90,  220),
    "shield":   (0,   190, 255, 220),
    "speed":    (255, 220, 0,   220),
    "triple":   (255, 130, 0,   220),
    "beam360":  (255, 60,  20,  220),   # fiery orange-red
    "elec360":  (120, 80,  255, 220),   # electric violet
}
POWERUP_LABELS = {
    "health":  "+HP",   "shield":  "SHIELD",
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
