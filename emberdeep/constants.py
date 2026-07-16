"""Tuning constants and the color palette for Emberdeep.

Art direction: Brogue's dark, jewel-toned look. Near-black background, muted
stone, saturated accents for anything interactive. All glyphs are pure ASCII
so the tileset can be rendered from any system TrueType font.
"""

# --- console / map geometry -------------------------------------------------
CONSOLE_W = 90
CONSOLE_H = 55
MAP_W = 80
MAP_H = 45
PANEL_H = CONSOLE_H - MAP_H  # 10 rows of UI below the map
LOG_LINES = 6

# --- game structure ---------------------------------------------------------
MAX_DEPTH = 15
BASE_LIGHT_RADIUS = 9
HEART_LIGHT_BONUS = 2

# --- player base stats ------------------------------------------------------
PLAYER_HP = 30
PLAYER_STR = 5
PLAYER_ACCURACY = 80
PLAYER_DODGE = 10
PLAYER_FIST_DMG = (1, 3)

# --- combat -----------------------------------------------------------------
BASE_HIT_CHANCE = 80          # percent, adjusted by accuracy vs dodge
MIN_HIT_CHANCE = 15
MAX_HIT_CHANCE = 97
STR_DAMAGE_REFERENCE = 5      # damage bonus = max(0, str - this)

# --- palette (RGB) ----------------------------------------------------------
IVORY = (238, 226, 200)       # player
BLACK = (0, 0, 0)
LOG_FRESH = (220, 214, 200)
LOG_STALE = (110, 104, 96)
HP_GOOD = (90, 190, 90)
HP_BAD = (200, 60, 50)
XP_BAR = (150, 110, 200)
PANEL_LINE = (70, 64, 60)
GOLD = (230, 190, 90)

# rarity colors (Diablo-flavored)
RARITY_COLORS = {
    "normal": (200, 200, 200),
    "magic": (100, 140, 240),
    "rare": (240, 220, 90),
    "legendary": (240, 140, 40),
}

# terrain base colors (lit at full light; render.py applies falloff)
TERRAIN_COLORS = {
    "wall": (96, 90, 108),
    "floor": (128, 118, 108),
    "grass": (64, 148, 58),
    "fungus": (160, 92, 176),
    "water": (52, 96, 190),
    "lava": (232, 96, 30),
    "vent": (112, 168, 92),
    "stair_up": (235, 225, 185),
    "stair_down": (235, 225, 185),
}

FIRE_COLOR = (250, 170, 40)
GAS_TINT = (46, 92, 44)
TELEPATHY_COLOR = (230, 80, 200)
