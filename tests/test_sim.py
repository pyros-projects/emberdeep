"""Headless integration: random-walk the engine, descend, use items, win path."""

import random

from emberdeep import actions
from emberdeep.engine import State


def test_random_playthrough_no_crash():
    for seed in (101, 202):
        state = State(seed=seed)
        rng = random.Random(seed)
        for _ in range(400):
            if state.game_over:
                break
            roll = rng.random()
            if roll < 0.7:
                spent = actions.move(state, *rng.choice(
                    [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1)]))
            elif roll < 0.8:
                spent = actions.pickup(state)
            elif roll < 0.85:
                spent = actions.descend(state)
            elif roll < 0.9 and state.player.inventory:
                spent = actions.equip_or_use(state, state.player.inventory[0])
                state.pending_identify = None  # UI-free: abandon the targeting/ID flow
                state.targeting = None
            else:
                spent = actions.wait(state)
            if spent:
                state.spend_turn()
        assert state.depth >= 1
        assert state.turn > 0


def test_descend_reaches_depth_3():
    state = State(seed=303)
    for _ in range(2):
        state.player.x, state.player.y = state.map.down_stairs
        assert actions.descend(state)
        state.spend_turn()
    assert state.depth == 3
    assert set(state.maps) == {1, 2, 3}


def test_heart_and_victory_flow():
    state = State(seed=404)
    state._enter_map(15, arriving_from="below")
    heart = [(x, y) for x, y, it in state.map.items if it.kind == "heart"]
    assert heart, "no Emberheart on depth 15"
    state.player.x, state.player.y = heart[0]
    assert actions.pickup(state)
    assert state.has_heart
    state.spend_turn()

    state._enter_map(1, arriving_from="below")
    state.player.x, state.player.y = state.map.up_stairs
    assert actions.ascend(state)
    assert state.victory


def test_cannot_leave_without_heart():
    state = State(seed=505)
    state.player.x, state.player.y = state.map.up_stairs
    assert not actions.ascend(state)
    assert not state.victory


def test_death_sets_game_over():
    state = State(seed=606)
    state.damage_actor(state.player, 999, source="a test harness")
    assert state.game_over
    assert "test harness" in state.death_cause
