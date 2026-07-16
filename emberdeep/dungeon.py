"""Procedural dungeon generation: rooms, corridors, cave patches, terrain.

Layout: random rooms joined by L-corridors, plus cellular-automata cave
patches for Brogue's organic feel. Rooms get themes (lichen grove, flooded
chamber, gas pocket); lava channels appear from depth 8. Every level is
BFS-verified fully connected, regenerated otherwise.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from .constants import MAP_H, MAP_W
from .terrain import Terrain, walkable


class GameMap:
    """A single dungeon level: terrain, fire/gas state, and inhabitants."""

    def __init__(self, width: int, height: int, depth: int):
        self.width = width
        self.height = height
        self.depth = depth
        self.terrain = np.full((width, height), Terrain.WALL, dtype=np.int8)
        self.fire = np.zeros((width, height), dtype=np.int8)
        self.gas = np.zeros((width, height), dtype=np.int8)
        self.explored = np.zeros((width, height), dtype=bool)
        self.monsters: list = []          # Actor, faction "monster"
        self.items: list = []             # (x, y, Item)
        self.rooms: list = []             # _Room list, set by generate()
        self.up_stairs: tuple[int, int] | None = None
        self.down_stairs: tuple[int, int] | None = None

    @classmethod
    def empty(cls, width: int, height: int, depth: int = 1) -> "GameMap":
        """All-floor map, used by tests."""
        m = cls(width, height, depth)
        m.terrain[:] = Terrain.FLOOR
        return m

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and walkable(Terrain(self.terrain[x, y]))

    def actor_at(self, x: int, y: int):
        for a in self.monsters:
            if a.is_alive and a.x == x and a.y == y:
                return a
        return None

    def item_at(self, x: int, y: int):
        for ix, iy, item in self.items:
            if ix == x and iy == y:
                return item
        return None

    def take_item_at(self, x: int, y: int):
        for entry in self.items:
            if entry[0] == x and entry[1] == y:
                self.items.remove(entry)
                return entry[2]
        return None

    def random_walkable(self, rng, avoid=None):
        avoid = avoid or set()
        for _ in range(200):
            x = rng.randrange(1, self.width - 1)
            y = rng.randrange(1, self.height - 1)
            if (
                self.is_walkable(x, y)
                and (x, y) not in avoid
                and self.actor_at(x, y) is None
                and self.item_at(x, y) is None
                and self.terrain[x, y] != Terrain.LAVA
            ):
                return x, y
        return None


class _Room:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2

    def cells(self):
        for cx in range(self.x, self.x + self.w):
            for cy in range(self.y, self.y + self.h):
                yield cx, cy


def _carve_room(terrain, room: _Room, t: Terrain = Terrain.FLOOR) -> None:
    for cx, cy in room.cells():
        terrain[cx, cy] = t


def _carve_corridor(terrain, x0, y0, x1, y1, rng) -> None:
    """L-shaped tunnel; horizontal/vertical order chosen at random."""
    legs = (
        [(x, y0) for x in _between(x0, x1)] + [(x1, y) for y in _between(y0, y1)]
        if rng.random() < 0.5
        else [(x0, y) for y in _between(y0, y1)] + [(x, y1) for x in _between(x0, x1)]
    )
    for x, y in legs:
        if 0 < x < terrain.shape[0] - 1 and 0 < y < terrain.shape[1] - 1:
            terrain[x, y] = Terrain.FLOOR


def _between(a: int, b: int):
    step = 1 if b >= a else -1
    return range(a, b + step, step)


def _carve_cave(terrain, rng, size: int = 14) -> None:
    """Carve one cellular-automata cave blob somewhere into the wall mass."""
    w, h = terrain.shape
    ox = rng.randrange(1, max(2, w - size - 1))
    oy = rng.randrange(1, max(2, h - size - 1))
    cave = np.random.default_rng(rng.randrange(2**32)).random((size, size)) < 0.45
    for _ in range(4):
        cave = _automata_step(cave)
    for cx in range(size):
        for cy in range(size):
            if cave[cx, cy]:
                terrain[ox + cx, oy + cy] = Terrain.FLOOR


def _automata_step(cave: np.ndarray) -> np.ndarray:
    padded = np.pad(cave, 1, constant_values=False)
    count = sum(
        padded[1 + dx : 1 + dx + cave.shape[0], 1 + dy : 1 + dy + cave.shape[1]]
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
    )
    return count >= 5


def _apply_themes(game_map: GameMap, rooms: list[_Room], rng) -> None:
    depth = game_map.depth
    t = game_map.terrain
    themes = ["grove", "flooded", "gas"]
    rng.shuffle(themes)
    for room, theme in zip(rooms[1:], themes):
        if theme == "grove":
            for cx, cy in room.cells():
                if t[cx, cy] == Terrain.FLOOR and rng.random() < 0.6:
                    t[cx, cy] = Terrain.GRASS if rng.random() < 0.8 else Terrain.FUNGUS
        elif theme == "flooded":
            cx0, cy0 = room.center
            for cx in range(cx0 - 2, cx0 + 3):
                for cy in range(cy0 - 2, cy0 + 3):
                    if t[cx, cy] == Terrain.FLOOR and abs(cx - cx0) + abs(cy - cy0) <= 3:
                        t[cx, cy] = Terrain.WATER
        elif theme == "gas":
            cx0, cy0 = room.center
            if t[cx0, cy0] == Terrain.FLOOR:
                t[cx0, cy0] = Terrain.VENT
                game_map.gas[cx0, cy0] = 3
    if depth >= 8:
        _carve_lava_channel(game_map, rng)


def _carve_lava_channel(game_map: GameMap, rng) -> None:
    """A drunken river of lava across the level. Lava is walkable (painfully),
    so it cannot disconnect the map."""
    t = game_map.terrain
    x = rng.randrange(2, game_map.width - 2)
    y = rng.randrange(2, game_map.height - 2)
    for _ in range(rng.randint(25, 45)):
        if t[x, y] in (Terrain.FLOOR, Terrain.GRASS):
            t[x, y] = Terrain.LAVA
        dx, dy = [(1, 0), (-1, 0), (0, 1), (0, -1)][rng.randrange(4)]
        x = min(max(x + dx, 1), game_map.width - 2)
        y = min(max(y + dy, 1), game_map.height - 2)


def connected(game_map: GameMap) -> bool:
    """BFS from up-stairs: every walkable cell must be reachable."""
    start = game_map.up_stairs or game_map.down_stairs
    if start is None:
        start = next(
            (
                (x, y)
                for x in range(game_map.width)
                for y in range(game_map.height)
                if game_map.is_walkable(x, y)
            ),
            None,
        )
    if start is None:
        return False
    seen = {start}
    queue = deque([start])
    total_walkable = int(sum(1 for v in game_map.terrain.flat if walkable(Terrain(int(v)))))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) not in seen and game_map.is_walkable(nx, ny):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return len(seen) == total_walkable


def generate(depth: int, rng, width: int = MAP_W, height: int = MAP_H) -> GameMap:
    """Generate a fully connected level for the given depth."""
    for _attempt in range(60):
        m = GameMap(width, height, depth)
        t = m.terrain

        rooms: list[_Room] = []
        for _ in range(rng.randint(10, 15)):
            w, h = rng.randint(4, 10), rng.randint(3, 8)
            x = rng.randrange(1, width - w - 1)
            y = rng.randrange(1, height - h - 1)
            room = _Room(x, y, w, h)
            _carve_room(t, room)
            rooms.append(room)

        for a, b in zip(rooms, rooms[1:]):
            _carve_corridor(t, *a.center, *b.center, rng)
        for _ in range(2):  # loops
            a, b = rng.choice(rooms), rng.choice(rooms)
            _carve_corridor(t, *a.center, *b.center, rng)

        for _ in range(rng.randint(1, 2)):
            _carve_cave(t, rng)

        _apply_themes(m, rooms, rng)

        ux, uy = rooms[0].center
        dx, dy = rooms[-1].center
        t[ux, uy] = Terrain.STAIR_UP
        if depth < _max_depth():
            t[dx, dy] = Terrain.STAIR_DOWN
            m.down_stairs = (dx, dy)
        m.up_stairs = (ux, uy)

        if connected(m):
            m.rooms = rooms
            return m
    raise RuntimeError(f"could not generate a connected level for depth {depth}")


def _max_depth() -> int:
    from .constants import MAX_DEPTH

    return MAX_DEPTH
