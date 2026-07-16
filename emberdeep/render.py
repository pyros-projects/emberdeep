"""Map rendering: the Brogue look.

Visible cells are lit with distance falloff from the player's light radius;
remembered cells sit desaturated at ~30%; the unexplored is pure black. Fire
flickers per frame, gas tints the background, water and lava shimmer.
"""

from __future__ import annotations

import numpy as np

from .constants import (
    FIRE_COLOR,
    GAS_TINT,
    IVORY,
    MAP_H,
    MAP_W,
    TELEPATHY_COLOR,
    TERRAIN_COLORS,
)
from .identify import display_name  # noqa: F401  (re-exported for ui)
from .terrain import PROPS, Terrain

# per-terrain glyph/color lookup tables indexed by Terrain value
_N = max(t.value for t in Terrain) + 1
_GLYPH = np.zeros(_N, dtype=np.int32)
_BASE = np.zeros((_N, 3), dtype=np.float32)
for _t, _p in PROPS.items():
    _GLYPH[_t.value] = ord(_p[0])
    _BASE[_t.value] = TERRAIN_COLORS[_p[1]]

_flicker_rng = np.random.default_rng()


def render_map(state, console) -> None:
    m = state.map
    from .items import derived_stats

    stats = derived_stats(state)
    W, H = m.width, m.height
    visible = state.visible
    explored = m.explored

    terr = m.terrain.astype(np.intp)
    ch = _GLYPH[terr]
    base = _BASE[terr]  # (W, H, 3)

    # light falloff from the player
    xs, ys = np.meshgrid(np.arange(W), np.arange(H), indexing="ij")
    dist = np.sqrt((xs - state.player.x) ** 2 + (ys - state.player.y) ** 2)
    radius = max(1.0, float(stats["light_radius"]))
    factor = np.clip(1.0 - 0.72 * dist / radius, 0.28, 1.0)

    lit = base * factor[..., None]
    remembered = base * 0.28
    # desaturate memory slightly toward its own luminance (cheap and moody)
    lum = remembered.mean(axis=2, keepdims=True)
    remembered = remembered * 0.6 + lum * 0.4

    fg = np.where(visible[..., None], lit, np.where(explored[..., None], remembered, 0.0))

    # water shimmer / lava glow on visible cells
    water = (terr == Terrain.WATER) & visible
    if water.any():
        fg[water, 2] = np.clip(fg[water, 2] + _flicker_rng.integers(0, 25, int(water.sum())), 0, 255)
    lava = (terr == Terrain.LAVA) & visible
    if lava.any():
        fg[lava] *= (0.85 + 0.3 * _flicker_rng.random((int(lava.sum()), 1)))

    # background: black, tinted by gas and fire glow
    bg = np.zeros((W, H, 3), dtype=np.float32)
    gas = m.gas
    gassy = (gas > 0) & visible
    if gassy.any():
        tint = np.array(GAS_TINT, dtype=np.float32) * (gas[gassy, None] / 3.0)
        bg[gassy] = tint * 0.9
    burning = (m.fire > 0) & visible
    if burning.any():
        jitter = 0.7 + 0.5 * _flicker_rng.random((int(burning.sum()), 1))
        fg[burning] = np.array(FIRE_COLOR, dtype=np.float32) * jitter
        ch[burning] = ord("*")
        bg[burning] = (np.array((90, 34, 10), dtype=np.float32) * jitter)

    console.rgb["ch"][:W, :H] = ch
    console.rgb["fg"][:W, :H] = np.clip(fg, 0, 255).astype(np.uint8)
    console.rgb["bg"][:W, :H] = np.clip(bg, 0, 255).astype(np.uint8)

    _draw_items(state, console, factor)
    _draw_actors(state, console, stats)


def _draw_items(state, console, factor) -> None:
    for x, y, item in state.map.items:
        if not state.map.explored[x, y]:
            continue
        vis = state.visible[x, y]
        scale = factor[x, y] if vis else 0.45
        color = tuple(int(c * scale) for c in item.color)
        console.print(x, y, item.ch, fg=color)


def _draw_actors(state, console, stats) -> None:
    telepathy = state.player.statuses.get("telepathy", 0) > 0
    for actor in state.map.monsters:
        if not actor.is_alive:
            continue
        vis = state.visible[actor.x, actor.y]
        if vis:
            console.print(actor.x, actor.y, actor.ch, fg=actor.color)
        elif telepathy:
            console.print(actor.x, actor.y, actor.ch, fg=TELEPATHY_COLOR)
    p = state.player
    console.print(p.x, p.y, "@", fg=IVORY)


def highlight_cell(console, x: int, y: int, color=(90, 80, 60)) -> None:
    """Cursor backdrop for look / targeting modes."""
    console.rgb["bg"][x, y] = color
