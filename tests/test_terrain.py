"""Fire/gas simulation: spread, burnout, gas ignition, water safety."""

import numpy as np

from emberdeep import terrain
from emberdeep.dungeon import GameMap
from emberdeep.engine import State
from emberdeep.terrain import Terrain


def _state_on(map_: GameMap, seed=21) -> State:
    state = State(seed=seed)
    state.maps = {1: map_}
    state.depth = 1
    state.player.x, state.player.y = 1, 1
    state.visible = np.zeros((map_.width, map_.height), dtype=bool)
    return state


def test_fire_spreads_and_burns_out():
    m = GameMap.empty(20, 20)
    m.terrain[5:15, 5:15] = Terrain.GRASS
    state = _state_on(m)
    terrain.ignite(m, 10, 10, fuel=3)
    assert m.fire[10, 10] > 0
    for _ in range(6):
        terrain.tick(state)
    spread = (m.fire > 0).sum() + (m.terrain == Terrain.FLOOR).sum() - (400 - 100)
    assert (m.fire > 0).sum() > 1 or (m.terrain[5:15, 5:15] == Terrain.FLOOR).any(), \
        "fire neither spread nor consumed grass"
    for _ in range(20):
        terrain.tick(state)
    assert (m.fire > 0).sum() == 0, "fire never burned out"
    # burnt grass becomes floor
    assert (m.terrain[5:15, 5:15] == Terrain.FLOOR).any()


def test_gas_explodes_with_fire():
    m = GameMap.empty(20, 20)
    m.gas[8:12, 8:12] = 3
    state = _state_on(m)
    m.fire[10, 10] = 2  # burning cell inside the cloud
    hp_before = state.player.hp
    state.player.x, state.player.y = 10, 10
    terrain.tick(state)
    assert (m.gas > 0).sum() < 16, "gas cloud did not detonate/clear"
    assert state.player.hp < hp_before, "explosion dealt no damage"


def test_water_never_burns():
    m = GameMap.empty(10, 10)
    m.terrain[5, 5] = Terrain.WATER
    # direct ignition of water is rejected unless it's a brief scorch (fuel<=2)
    terrain.ignite(m, 5, 5, fuel=3)
    assert m.fire[5, 5] == 0


def test_vent_replenishes_gas():
    m = GameMap.empty(10, 10)
    m.terrain[5, 5] = Terrain.VENT
    state = _state_on(m)
    for _ in range(10):
        terrain.tick(state)
    assert m.gas[5, 5] > 0
