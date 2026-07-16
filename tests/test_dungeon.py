"""Dungeon generation invariants: stairs, connectivity, sane density."""

import random

from emberdeep.constants import MAX_DEPTH
from emberdeep.dungeon import connected, generate
from emberdeep.terrain import Terrain, walkable


def test_stairs_present_and_connected_all_depths():
    for depth in range(1, MAX_DEPTH + 1):
        rng = random.Random(1000 + depth)
        m = generate(depth, rng)
        assert m.up_stairs is not None
        assert Terrain(int(m.terrain[m.up_stairs])) == Terrain.STAIR_UP
        if depth < MAX_DEPTH:
            assert m.down_stairs is not None
            assert Terrain(int(m.terrain[m.down_stairs])) == Terrain.STAIR_DOWN
        else:
            assert m.down_stairs is None  # the bottom of the world
        assert connected(m), f"depth {depth} is disconnected"


def test_walkable_density_sane():
    for seed in range(5):
        m = generate(3, random.Random(seed))
        total = m.width * m.height
        open_cells = sum(1 for v in m.terrain.flat if walkable(Terrain(int(v))))
        ratio = open_cells / total
        assert 0.15 < ratio < 0.75, f"seed {seed}: {ratio:.2f} open"


def test_generation_deterministic_per_seed():
    a = generate(5, random.Random(42))
    b = generate(5, random.Random(42))
    assert (a.terrain == b.terrain).all()
    assert a.up_stairs == b.up_stairs


def test_lava_only_deep():
    shallow = generate(2, random.Random(7))
    assert (shallow.terrain == Terrain.LAVA).sum() == 0
    deep_count = sum(
        (generate(10, random.Random(s)).terrain == Terrain.LAVA).sum() for s in range(4)
    )
    assert deep_count > 0  # lava channels exist by depth 10
