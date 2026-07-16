"""Generate docs/banner.png — a stylized slice of the Emberdeep.

The banner renders a real generated dungeon (depth 10, so lava shows up)
with the game's own palette and light falloff, staged with fire, gas,
monsters and loot, then overlays a glowing ember title.

Run: .venv/bin/python scripts/make_banner.py [seed]
"""

import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emberdeep.constants import FIRE_COLOR, GAS_TINT, IVORY, TERRAIN_COLORS
from emberdeep.dungeon import generate
from emberdeep.entities import MONSTERS
from emberdeep.terrain import PROPS, Terrain

CELL = 16                     # pixels per map cell
COLS, ROWS = 76, 22
W, H = COLS * CELL, ROWS * CELL
FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "banner.png")


def find_cells(m, terrain_type, limit=99):
    out = []
    for x in range(m.width):
        for y in range(m.height):
            if m.terrain[x, y] == terrain_type:
                out.append((x, y))
    return out[:limit]


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    rng = random.Random(seed)
    m = generate(10, rng, width=COLS, height=ROWS)

    font = ImageFont.truetype(FONT_PATH, CELL + 2)
    img = Image.new("RGB", (W, H), (8, 7, 9))
    draw = ImageDraw.Draw(img)

    # stage the player left of the title band so the '@' stays visible
    floor_cells = find_cells(m, Terrain.FLOOR)
    px, py = min(floor_cells,
                 key=lambda c: (c[0] - int(COLS * 0.28)) ** 2 + (c[1] - ROWS // 2) ** 2)
    radius = 16.0

    def brightness(x, y):
        dist = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
        return max(0.42, min(1.0, 1.0 - 0.55 * dist / radius))

    # --- terrain with light falloff -----------------------------------------
    for x in range(COLS):
        for y in range(ROWS):
            t = Terrain(int(m.terrain[x, y]))
            glyph, ckey = PROPS[t][0], PROPS[t][1]
            base = TERRAIN_COLORS[ckey]
            b = brightness(x, y)
            if t == Terrain.LAVA:
                b = max(b, 0.85)  # lava lights itself
            jitter = 0.92 + 0.16 * rng.random()
            fg = tuple(int(c * b * jitter) for c in base)
            cx, cy = x * CELL, y * CELL
            if m.gas[x, y] > 0:
                tint = tuple(int(c * (m.gas[x, y] / 3.0) * b) for c in GAS_TINT)
                draw.rectangle([cx, cy, cx + CELL, cy + CELL], fill=tint)
            draw.text((cx + 1, cy - 2), glyph, font=font, fill=fg)

    # --- a lichen fire near the player (the imp clearly started it) -------------
    grass = find_cells(m, Terrain.GRASS)
    grass = [c for c in grass if brightness(*c) > 0.3]
    grass.sort(key=lambda c: (c[0] - px) ** 2 + (c[1] - py) ** 2)
    for x, y in grass[:9]:
        f = 0.7 + 0.5 * rng.random()
        color = tuple(int(c * f) for c in FIRE_COLOR)
        draw.rectangle([x * CELL, y * CELL, (x + 1) * CELL, (y + 1) * CELL],
                       fill=(int(90 * f * brightness(x, y)),
                             int(34 * f * brightness(x, y)), 10))
        draw.text((x * CELL + 1, y * CELL - 2), "*", font=font, fill=color)

    # --- monsters, loot, and the player ---------------------------------------
    floor = find_cells(m, Terrain.FLOOR)
    rng.shuffle(floor)

    def near(dist_range):
        for x, y in floor:
            d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if dist_range[0] <= d <= dist_range[1] and brightness(x, y) > 0.3:
                floor.remove((x, y))
                return x, y
        return None

    for key, dr in (("imp", (2, 4)), ("goblin", (4, 6)), ("ogre", (6, 8)),
                    ("wraith", (5, 9)), ("kobold", (3, 6))):
        pos = near(dr)
        if pos:
            d = MONSTERS[key]
            draw.text((pos[0] * CELL + 1, pos[1] * CELL - 2), d["ch"],
                      font=font, fill=d["color"])
    for glyph, color in (("!", (220, 90, 160)), ("o", (230, 190, 90)),
                         ("?", (215, 200, 160))):
        pos = near((3, 8))
        if pos:
            draw.text((pos[0] * CELL + 1, pos[1] * CELL - 2), glyph,
                      font=font, fill=color)
    # the player, with a faint glow
    glow_at = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow_at).text((px * CELL + 1, py * CELL - 2), "@",
                                 font=font, fill=(255, 240, 200, 255))
    img = Image.alpha_composite(img.convert("RGBA"),
                                glow_at.filter(ImageFilter.GaussianBlur(4)))
    img = Image.alpha_composite(img, glow_at).convert("RGB")
    draw = ImageDraw.Draw(img)

    # --- vignette ---------------------------------------------------------------
    xs, ys = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    vig = np.clip(1.0 - 0.30 * (xs ** 2 + ys ** 2), 0.55, 1.0)
    arr = np.asarray(img, dtype=np.float32) * vig[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # --- glowing ember title ------------------------------------------------------
    title = "EMBERDEEP"
    tag = "take the emberheart. come back alive."
    title_font = ImageFont.truetype(FONT_PATH, 84)
    tag_font = ImageFont.truetype(FONT_PATH, 20)

    def text_size(f, s):
        box = f.getbbox(s)
        return box[2] - box[0], box[3] - box[1]

    tw, th = text_size(title_font, title)
    tx, ty = (W - tw) // 2, H // 2 - th // 2 - 26

    # dark band for readability
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(band)
    bdraw.rectangle([0, ty - 22, W, ty + th + 66], fill=(5, 4, 6, 110))
    img = Image.alpha_composite(img.convert("RGBA"), band)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.text((tx, ty), title, font=title_font, fill=(255, 90, 20, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img, glow)

    sharp = ImageDraw.Draw(img)
    for i, ch in enumerate(title):  # ember gradient across the letters
        t = i / max(1, len(title) - 1)
        color = (255, int(200 - 130 * t), int(60 - 30 * t))
        ch_x = tx + sharp.textlength(title[:i], font=title_font)
        sharp.text((ch_x, ty), ch, font=title_font, fill=color,
                   stroke_width=2, stroke_fill=(60, 20, 8, 255))
    tag_w, _ = text_size(tag_font, tag)
    sharp.text(((W - tag_w) // 2, ty + th + 20), tag, font=tag_font,
               fill=(170, 160, 150, 255))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.convert("RGB").save(OUT, "PNG")
    print(f"wrote {OUT} (seed {seed})")


if __name__ == "__main__":
    main()
