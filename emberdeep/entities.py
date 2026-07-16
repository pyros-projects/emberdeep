"""Actors: the player shell, the bestiary, and monster AI.

AI is deliberately simple: monsters see the player within range 8 with line
of sight, remember the last seen position, and otherwise wander. Each monster
type has exactly one trick, Brogue-style.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import tcod

from . import combat
from .terrain import Terrain, flammable, neighbors8, walkable

SIGHT_RANGE = 8


@dataclass
class Actor:
    x: int
    y: int
    ch: str
    color: tuple
    name: str
    hp: int
    max_hp: int
    dmg: tuple
    accuracy: int
    dodge: int
    defense: int
    xp_value: int
    ai: str = "chase"
    faction: str = "monster"          # monster | ally | player
    key: str = ""
    statuses: dict = field(default_factory=dict)
    target: tuple | None = None       # last seen player position
    # behavioral flags
    flee_threshold: float = 0.0
    on_hit: str | None = None         # "poison"
    can_split: bool = False
    fire_immune: bool = False
    teleport_on_hit: bool = False
    slow: bool = False
    fast: bool = False
    aura: bool = False
    # player-only baggage (None for monsters)
    is_player: bool = False
    inventory: list | None = None
    equipment: dict | None = None
    # player progression (ignored by monsters)
    strength: int = 0
    acc_bonus: int = 0
    level: int = 1
    xp: int = 0
    xp_next: int = 18

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def distance_to(self, x: int, y: int) -> float:
        return max(abs(self.x - x), abs(self.y - y))  # Chebyshev


# --- bestiary ----------------------------------------------------------------
# hp, dmg, accuracy, dodge, defense, xp value; weight per depth band.
MONSTERS = {
    "rat":       dict(ch="r", color=(170, 150, 125), name="rat", hp=5, dmg=(1, 3), accuracy=75, dodge=15, defense=0, xp=2, ai="chase"),
    "kobold":    dict(ch="k", color=(205, 130, 90), name="kobold", hp=8, dmg=(2, 4), accuracy=80, dodge=10, defense=0, xp=3, ai="chase"),
    "bat":       dict(ch="b", color=(150, 130, 210), name="bat", hp=4, dmg=(1, 2), accuracy=85, dodge=35, defense=0, xp=2, ai="erratic"),
    "goblin":    dict(ch="g", color=(95, 175, 85), name="goblin", hp=10, dmg=(2, 5), accuracy=80, dodge=12, defense=0, xp=4, ai="chase", flee_threshold=0.3),
    "spider":    dict(ch="s", color=(190, 70, 70), name="cave spider", hp=9, dmg=(1, 4), accuracy=82, dodge=18, defense=0, xp=5, ai="chase", on_hit="poison"),
    "jelly":     dict(ch="j", color=(90, 200, 190), name="ochre jelly", hp=12, dmg=(2, 4), accuracy=75, dodge=5, defense=0, xp=6, ai="chase", can_split=True),
    "imp":       dict(ch="i", color=(235, 120, 60), name="imp", hp=8, dmg=(1, 3), accuracy=80, dodge=20, defense=0, xp=7, ai="ranged"),
    "wraith":    dict(ch="w", color=(180, 190, 220), name="wraith", hp=10, dmg=(2, 6), accuracy=82, dodge=40, defense=0, xp=9, ai="chase", teleport_on_hit=True),
    "ogre":      dict(ch="O", color=(140, 110, 80), name="ogre", hp=22, dmg=(5, 10), accuracy=70, dodge=5, defense=1, xp=12, ai="chase", slow=True),
    "naga":      dict(ch="N", color=(120, 200, 120), name="naga", hp=16, dmg=(3, 7), accuracy=85, dodge=15, defense=1, xp=14, ai="chase", fast=True),
    "elemental": dict(ch="E", color=(250, 150, 40), name="fire elemental", hp=14, dmg=(3, 6), accuracy=82, dodge=10, defense=0, xp=16, ai="chase", aura=True, fire_immune=True),
    "warden":    dict(ch="W", color=(250, 90, 40), name="Ember Warden", hp=42, dmg=(6, 12), accuracy=88, dodge=10, defense=3, xp=40, ai="chase", fire_immune=True),
    "shade":     dict(ch="S", color=(130, 110, 200), name="echoing shade", hp=8, dmg=(2, 5), accuracy=85, dodge=20, defense=0, xp=0, ai="ally", faction="ally"),
}

# (key, weight, min_depth, max_depth)
SPAWN_TABLE = [
    ("rat", 12, 1, 5), ("kobold", 11, 1, 6), ("bat", 9, 1, 6),
    ("goblin", 10, 1, 7), ("spider", 9, 2, 8), ("jelly", 8, 3, 9),
    ("imp", 8, 4, 10), ("wraith", 7, 5, 11), ("ogre", 7, 6, 12),
    ("naga", 6, 7, 13), ("elemental", 6, 8, 15),
]


def spawn(key: str, x: int, y: int) -> Actor:
    d = MONSTERS[key]
    return Actor(
        x=x, y=y, ch=d["ch"], color=d["color"], name=d["name"],
        hp=d["hp"], max_hp=d["hp"], dmg=d["dmg"], accuracy=d["accuracy"],
        dodge=d["dodge"], defense=d["defense"], xp_value=d["xp"], ai=d["ai"],
        faction=d.get("faction", "monster"), key=key,
        flee_threshold=d.get("flee_threshold", 0.0),
        on_hit=d.get("on_hit"), can_split=d.get("can_split", False),
        fire_immune=d.get("fire_immune", False),
        teleport_on_hit=d.get("teleport_on_hit", False),
        slow=d.get("slow", False), fast=d.get("fast", False),
        aura=d.get("aura", False),
    )


def populate(game_map, depth: int, rng) -> None:
    """Place 6-10 depth-appropriate monsters, away from the up-stairs.

    The deep makes its dwellers stronger: spawns scale with depth, so a
    depth-12 kobold is a grizzled veteran of the same breed.
    """
    count = rng.randint(6, 10)
    ux, uy = game_map.up_stairs
    avoid = {
        (ux + dx, uy + dy)
        for dx in range(-5, 6)
        for dy in range(-5, 6)
    }
    options = [row for row in SPAWN_TABLE if row[2] <= depth <= row[3]]
    for _ in range(count):
        total = sum(w for _, w, _, _ in options)
        roll = rng.uniform(0, total)
        key = options[0][0]
        for key, w, _, _ in options:
            roll -= w
            if roll <= 0:
                break
        pos = game_map.random_walkable(rng, avoid=avoid)
        if pos:
            game_map.monsters.append(_scale(spawn(key, *pos), depth))


def _scale(actor: Actor, depth: int) -> Actor:
    bonus_hp = int(actor.hp * 0.10 * (depth - 1))
    actor.hp = actor.max_hp = actor.hp + bonus_hp
    dmg_bonus = (depth - 1) // 3
    actor.dmg = (actor.dmg[0] + dmg_bonus, actor.dmg[1] + dmg_bonus)
    actor.accuracy += depth - 1
    actor.xp_value += (depth - 1) // 4
    return actor


# --- spatial helpers ---------------------------------------------------------

def los(game_map, x0: int, y0: int, x1: int, y1: int) -> bool:
    """Bresenham line of sight over terrain transparency."""
    for x, y in tcod.los.bresenham((x0, y0), (x1, y1)).tolist():
        if not game_map.in_bounds(x, y):
            return False
        if (x, y) != (x0, y0) and (x, y) != (x1, y1):
            from .terrain import transparent

            if not transparent(Terrain(int(game_map.terrain[x, y]))):
                return False
    return True


def _path_cost(state, actor) -> np.ndarray:
    m = state.map
    walk = np.vectorize(lambda v: walkable(Terrain(int(v))))(m.terrain)
    cost = np.where(walk, 1.0, 0.0).astype(np.float32)
    cost[m.terrain == Terrain.WATER] = 2.0
    if not actor.fire_immune:
        cost[(m.fire > 0) | (m.terrain == Terrain.LAVA) | (m.gas > 0)] = 0.0
    # don't path through other actors
    for other in m.monsters:
        if other is not actor and other.is_alive:
            cost[other.x, other.y] = 0.0
    cost[state.player.x, state.player.y] = 1.0  # pathing toward the player is fine
    return cost


def _step_toward(state, actor, tx: int, ty: int) -> None:
    cost = _path_cost(state, actor)
    cost[tx, ty] = max(cost[tx, ty], 1.0)
    path = tcod.path.AStar(cost, diagonal=1.41).get_path(actor.x, actor.y, tx, ty)
    if len(path) > 1:
        _move_or_attack(state, actor, path[1][0] - actor.x, path[1][1] - actor.y)


def _move_or_attack(state, actor, dx: int, dy: int) -> None:
    nx, ny = actor.x + dx, actor.y + dy
    m = state.map
    if not m.in_bounds(nx, ny):
        return
    if nx == state.player.x and ny == state.player.y:
        if actor.faction == "monster":
            combat.attack(state, actor, state.player)
        return
    occupant = m.actor_at(nx, ny)
    if occupant is not None:
        if actor.faction == "ally" and occupant.faction == "monster":
            combat.attack(state, actor, occupant)
        return
    if not m.is_walkable(nx, ny):
        return
    if not actor.fire_immune and (m.fire[nx, ny] > 0 or m.terrain[nx, ny] == Terrain.LAVA):
        return
    actor.x, actor.y = nx, ny


def _wander(state, actor) -> None:
    options = [
        (nx, ny)
        for nx, ny in neighbors8(actor.x, actor.y)
        if state.map.is_walkable(nx, ny) and state.map.actor_at(nx, ny) is None
        and (nx, ny) != (state.player.x, state.player.y)
        and (actor.fire_immune or (state.map.fire[nx, ny] == 0 and state.map.terrain[nx, ny] != Terrain.LAVA))
    ]
    if options and state.rng.random() < 0.6:
        nx, ny = options[state.rng.randrange(len(options))]
        actor.x, actor.y = nx, ny


# --- the AI entry point ------------------------------------------------------

def act(state, actor) -> None:
    rng = state.rng
    player = state.player

    if actor.statuses.get("confusion", 0) > 0:
        _wander(state, actor)
        return
    if actor.slow and rng.random() < 0.5:
        return  # ogres take their time

    if actor.faction == "ally":
        _act_ally(state, actor)
        return

    if actor.ai == "erratic":
        _wander(state, actor)
        return

    dist = actor.distance_to(player.x, player.y)
    sees_player = (
        dist <= SIGHT_RANGE
        and player.is_alive
        and los(state.map, actor.x, actor.y, player.x, player.y)
    )
    if sees_player:
        actor.target = (player.x, player.y)

    fleeing = (
        actor.statuses.get("fear", 0) > 0
        or (actor.flee_threshold and actor.hp < actor.max_hp * actor.flee_threshold)
    )
    if fleeing and sees_player:
        dx = _sign(actor.x - player.x)
        dy = _sign(actor.y - player.y)
        _move_or_attack(state, actor, dx, dy)
        return

    if actor.aura:
        _aura_tick(state, actor)

    if actor.ai == "ranged" and sees_player and 2 <= dist <= 6 and rng.random() < 0.55:
        _hurl_fire(state, actor, player)
        return

    if actor.target is not None:
        if actor.target == (actor.x, actor.y) and not sees_player:
            actor.target = None
        else:
            _step_toward(state, actor, *actor.target)
            if not sees_player and (actor.x, actor.y) == actor.target:
                actor.target = None
    else:
        _wander(state, actor)


def _act_ally(state, actor) -> None:
    prey = [
        m for m in state.map.monsters
        if m.faction == "monster" and m.is_alive and m.distance_to(actor.x, actor.y) <= 8
    ]
    if not prey:
        return
    prey.sort(key=lambda m: m.distance_to(actor.x, actor.y))
    target = prey[0]
    if target.distance_to(actor.x, actor.y) == 1:
        combat.attack(state, actor, target)
    else:
        _step_toward(state, actor, target.x, target.y)


def _aura_tick(state, actor) -> None:
    m = state.map
    for nx, ny in neighbors8(actor.x, actor.y):
        if m.in_bounds(nx, ny) and flammable(Terrain(int(m.terrain[nx, ny]))):
            if state.rng.random() < 0.4:
                m.fire[nx, ny] = max(int(m.fire[nx, ny]), 3)
    if actor.distance_to(state.player.x, state.player.y) == 1:
        combat.add_status(state.player, "burning", 3)
        state.log("the elemental's heat sears you — you are burning!", warn=True)


def _hurl_fire(state, actor, player) -> None:
    state.log(f"the {actor.name} hurls a ball of fire!", warn=True)
    combat.add_status(player, "burning", 2)
    state.damage_actor(player, state.rng.randint(3, 6), source=f"the {actor.name}'s fire")
    from . import terrain

    terrain.ignite(state.map, player.x, player.y, fuel=2)


def _sign(v: int) -> int:
    return (v > 0) - (v < 0)
