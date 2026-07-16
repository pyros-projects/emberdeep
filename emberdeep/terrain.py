"""Terrain types and the fire/gas/water/lava simulation.

The map stores three parallel int arrays indexed [x, y]:
  terrain — the static Terrain enum value
  fire    — turns of fuel remaining (0 = not burning)
  gas     — gas concentration 0..3 (vents replenish it)

The simulation runs once per player action. Fire spreads to flammable
neighbors, gas drifts and decays, and fire touching gas detonates it in a
2-tile blast — the classic Brogue chain reaction.
"""

from __future__ import annotations

from enum import IntEnum

import numpy as np


class Terrain(IntEnum):
    WALL = 0
    FLOOR = 1
    GRASS = 2      # flammable lichen
    FUNGUS = 3     # flammable glowfungus
    WATER = 4      # extinguishes fire and burning actors
    LAVA = 5       # damages and ignites
    VENT = 6       # emits flammable gas
    STAIR_UP = 7
    STAIR_DOWN = 8


# glyph, color key, walkable, transparent, flammable, display name
PROPS = {
    Terrain.WALL:       ("#", "wall",       False, False, False, "a stone wall"),
    Terrain.FLOOR:      (".", "floor",      True,  True,  False, "stone floor"),
    Terrain.GRASS:      ('"', "grass",      True,  True,  True,  "lichen"),
    Terrain.FUNGUS:     ("%", "fungus",     True,  True,  True,  "glowfungus"),
    Terrain.WATER:      ("~", "water",      True,  True,  False, "water"),
    Terrain.LAVA:       ("=", "lava",       True,  True,  False, "molten lava"),
    Terrain.VENT:       (":", "vent",       True,  True,  False, "a hissing gas vent"),
    Terrain.STAIR_UP:   ("<", "stair_up",   True,  True,  False, "stairs leading up"),
    Terrain.STAIR_DOWN: (">", "stair_down", True,  True,  False, "stairs leading down"),
}

FLAMMABLE = frozenset(t for t, p in PROPS.items() if p[4])


def glyph(t: Terrain) -> str:
    return PROPS[t][0]


def color_key(t: Terrain) -> str:
    return PROPS[t][1]


def walkable(t: Terrain) -> bool:
    return PROPS[t][2]


def transparent(t: Terrain) -> bool:
    return PROPS[t][3]


def flammable(t: Terrain) -> bool:
    return PROPS[t][4]


def name(t: Terrain) -> str:
    return PROPS[t][5]


def neighbors8(x: int, y: int):
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                yield x + dx, y + dy


def ignite(game_map, x: int, y: int, fuel: int = 3) -> bool:
    """Set a cell on fire. Gas cells detonate instead of smouldering."""
    if not game_map.in_bounds(x, y):
        return False
    if game_map.gas[x, y] > 0:
        return False  # caller should explode; handled in tick
    t = game_map.terrain[x, y]
    if walkable(t) and (flammable(t) or fuel <= 2):
        game_map.fire[x, y] = max(int(game_map.fire[x, y]), fuel)
        return True
    return False


def tick(state) -> None:
    """Advance fire and gas by one turn. Damage is applied by the engine."""
    m = state.map
    rng = state.rng
    fire, gas, terr = m.fire, m.gas, m.terrain

    # --- burning cells: spread, detonate gas, burn out ----------------------
    burning = list(zip(*np.nonzero(fire > 0)))
    for x, y in burning:
        if fire[x, y] <= 0:
            continue  # consumed by an explosion earlier this tick
        for nx, ny in neighbors8(x, y):
            if not m.in_bounds(nx, ny):
                continue
            if gas[nx, ny] > 0:
                explode(state, nx, ny)
            elif (
                flammable(terr[nx, ny])
                and fire[nx, ny] == 0
                and rng.random() < 0.30
            ):
                fire[nx, ny] = 3
                if state.visible[nx, ny]:
                    state.log("the flames spread.", dim=True)
        fire[x, y] -= 1
        if fire[x, y] <= 0 and terr[x, y] in FLAMMABLE:
            terr[x, y] = Terrain.FLOOR

    # fire standing in gas goes off immediately
    flash = list(zip(*np.nonzero((fire > 0) & (gas > 0))))
    for x, y in flash:
        explode(state, x, y)

    # --- vents replenish gas -------------------------------------------------
    vent_cells = list(zip(*np.nonzero(terr == Terrain.VENT)))
    for x, y in vent_cells:
        if gas[x, y] < 3 and rng.random() < 0.40:
            gas[x, y] += 1

    # --- gas drift and decay --------------------------------------------------
    gassy = list(zip(*np.nonzero(gas > 0)))
    for x, y in gassy:
        if terr[x, y] == Terrain.VENT:
            continue
        if gas[x, y] >= 1 and rng.random() < 0.35:
            options = [
                (nx, ny)
                for nx, ny in neighbors8(x, y)
                if m.in_bounds(nx, ny)
                and walkable(terr[nx, ny])
                and gas[nx, ny] < gas[x, y]
            ]
            if options:
                nx, ny = options[rng.randrange(len(options))]
                gas[nx, ny] += 1
        if rng.random() < 0.12:
            gas[x, y] -= 1


def explode(state, x: int, y: int) -> None:
    """Detonate the gas at (x, y): 2-tile blast, damage, lingering fire."""
    m = state.map
    if state.visible[x, y]:
        state.log("the pocket of gas erupts in flame!", warn=True)
    radius = 2
    for cx in range(x - radius, x + radius + 1):
        for cy in range(y - radius, y + radius + 1):
            if not m.in_bounds(cx, cy):
                continue
            if max(abs(cx - x), abs(cy - y)) > radius:
                continue
            m.gas[cx, cy] = 0
            t = m.terrain[cx, cy]
            if walkable(t):
                m.fire[cx, cy] = max(int(m.fire[cx, cy]), 3 if flammable(t) else 2)
            victim = m.actor_at(cx, cy)
            if victim is not None:
                state.damage_actor(victim, state.rng.randint(8, 16), source="the explosion")
            if state.player.is_alive and (state.player.x, state.player.y) == (cx, cy):
                state.damage_actor(
                    state.player, state.rng.randint(8, 16), source="the explosion"
                )
