"""Bottom panel, inventory overlay, look/targeting cursors, level-up prompt."""

from __future__ import annotations

from . import terrain as terrain_mod
from .constants import (
    CONSOLE_W,
    GOLD,
    HP_BAD,
    HP_GOOD,
    LOG_FRESH,
    LOG_STALE,
    LOG_LINES,
    MAP_H,
    PANEL_H,
    XP_BAR,
)
from .identify import display_name
from .terrain import Terrain

WARN_COLOR = (240, 150, 60)

# ASCII frame decoration: corners, edges, center (tcod's 9-glyph order)
FRAME = tuple(map(ord, "+-+| |+-+"))


# --- panel ----------------------------------------------------------------------

def draw_panel(console, state) -> None:
    from .items import derived_stats

    p = state.player
    stats = derived_stats(state)
    y0 = MAP_H
    console.print(0, y0, "-" * CONSOLE_W, fg=(60, 55, 52))

    # HP bar
    bar_w = 20
    max_hp = p.max_hp + stats["hp_bonus"]
    ratio = p.hp / max(1, max_hp)
    filled = int(bar_w * ratio)
    bar = "#" * filled + "-" * (bar_w - filled)
    console.print(1, y0 + 1, "HP ", fg=LOG_STALE)
    console.print(4, y0 + 1, bar, fg=HP_GOOD if ratio > 0.35 else HP_BAD)
    console.print(4 + bar_w + 1, y0 + 1, f"{p.hp}/{max_hp}", fg=LOG_FRESH)

    # XP bar
    xp_ratio = p.xp / max(1, p.xp_next)
    xp_filled = int(12 * xp_ratio)
    console.print(30, y0 + 1, "XP ", fg=LOG_STALE)
    console.print(33, y0 + 1, "#" * xp_filled + "-" * (12 - xp_filled), fg=XP_BAR)
    console.print(46, y0 + 1, f"LV {p.level}", fg=LOG_FRESH)

    status_bits = [k for k in ("burning", "poison", "confusion", "blind", "telepathy")
                   if p.statuses.get(k, 0) > 0]
    right = f"STR {stats['strength']}  DEF {stats['defense']}  depth {state.depth}  turn {state.turn}"
    if status_bits:
        right = " ".join(status_bits).upper() + "  |  " + right
    console.print(CONSOLE_W - len(right) - 1, y0 + 1, right, fg=WARN_COLOR if status_bits else LOG_STALE)

    # equipment line
    eq = p.equipment or {}
    w = eq.get("weapon")
    a = eq.get("armor")
    rings = [eq.get("ring1"), eq.get("ring2")]
    gear = f"W: {w.name if w else 'fists'}   A: {a.name if a else '—'}   R: {', '.join(r.name for r in rings if r) or '—'}"
    if state.has_heart:
        gear += "   [EMBERHEART]"
    console.print(1, y0 + 2, gear[: CONSOLE_W - 2], fg=GOLD if state.has_heart else LOG_STALE)

    # message log: newest at the bottom, older lines fading
    recent = state.messages[-LOG_LINES:]
    for i, msg in enumerate(recent):
        age = state.turn - msg["turn"]
        if msg["warn"]:
            color = WARN_COLOR
        elif msg["dim"] or age > 0:
            color = LOG_STALE
        else:
            color = LOG_FRESH
        console.print(1, y0 + 3 + i, msg["text"][: CONSOLE_W - 2], fg=color)


# --- inventory ---------------------------------------------------------------------

def draw_inventory(console, state, purpose: str = "use") -> None:
    inv = state.player.inventory
    width = 56
    height = min(len(inv) + 4, 34)
    x0, y0 = 2, 2
    console.draw_rect(x0, y0, width, height, ord(" "), bg=(18, 16, 14))
    console.draw_frame(x0, y0, width, height, fg=(90, 80, 70), decoration=FRAME)
    title = {"use": "pack — select to use / equip",
             "identify": "identify what?",
             "drop": "drop what?"}[purpose]
    console.print(x0 + 2, y0, f" {title} ", fg=LOG_FRESH)

    eq = state.player.equipment or {}
    for i, item in enumerate(inv[:26]):
        name = display_name(state, item)
        marks = []
        if item in eq.values():
            marks.append("worn")
        if item.kind == "staff":
            marks.append(f"{item.charges} charges")
        if item.kind in ("weapon", "armor") and item.str_req and item.known:
            marks.append(f"req STR {item.str_req}")
        suffix = f"  ({'; '.join(marks)})" if marks else ""
        color = item.color if item.known or item.kind not in ("weapon", "armor", "ring") else (200, 200, 200)
        console.print(x0 + 2, y0 + 2 + i, f"{chr(97 + i)}) {name}{suffix}", fg=color)
    if not inv:
        console.print(x0 + 2, y0 + 2, "(empty)", fg=LOG_STALE)
    console.print(x0 + 2, y0 + height - 1, "esc to close", fg=LOG_STALE)


# --- look mode ---------------------------------------------------------------------

def describe_cell(state, x: int, y: int) -> str:
    m = state.map
    if not m.in_bounds(x, y):
        return ""
    if not m.explored[x, y]:
        return "unexplored darkness."
    parts = [terrain_mod.name(Terrain(int(m.terrain[x, y])))]
    if m.fire[x, y] > 0:
        parts.append("burning!")
    if m.gas[x, y] > 0:
        parts.append("wreathed in gas")
    actor = m.actor_at(x, y)
    if actor is not None and state.visible[x, y]:
        parts.append(f"{actor.name} ({actor.hp}/{actor.max_hp} HP)")
    item = m.item_at(x, y)
    if item is not None:
        parts.append(display_name(state, item))
    if (x, y) == (state.player.x, state.player.y):
        parts.append("you")
    return "; ".join(parts) + "."


def draw_look_bar(console, state, x: int, y: int) -> None:
    text = describe_cell(state, x, y)
    console.print(1, MAP_H - 1, " " * (CONSOLE_W - 2), bg=(25, 22, 18))
    console.print(1, MAP_H - 1, text[: CONSOLE_W - 2], fg=LOG_FRESH, bg=(25, 22, 18))


# --- targeting -----------------------------------------------------------------------

def draw_target_line(console, state, tx: int, ty: int) -> None:
    import tcod

    p = state.player
    line = tcod.los.bresenham((p.x, p.y), (tx, ty)).tolist()
    for x, y in line[1:]:
        if 0 <= x < console.width and 0 <= y < MAP_H:
            console.rgb["bg"][x, y] = (60, 50, 30)
    console.print(1, MAP_H - 1, f"targeting: {describe_cell(state, tx, ty)}"[: CONSOLE_W - 2],
                  fg=WARN_COLOR)


# --- level-up ---------------------------------------------------------------------------

def draw_levelup(console, state) -> None:
    width, height = 44, 9
    x0 = (CONSOLE_W - width) // 2
    y0 = (MAP_H - height) // 2
    console.draw_frame(x0, y0, width, height, fg=(150, 110, 200), bg=(18, 14, 24),
                       decoration=FRAME)
    console.print(x0 + 2, y0 + 1, f"level {state.player.level}! choose a boon:", fg=LOG_FRESH)
    console.print(x0 + 2, y0 + 3, "s) +1 strength   (hits harder)", fg=LOG_FRESH)
    console.print(x0 + 2, y0 + 4, "a) +3 accuracy   (hits more often)", fg=LOG_FRESH)
    console.print(x0 + 2, y0 + 5, "v) +6 max health (and heal 6)", fg=LOG_FRESH)
