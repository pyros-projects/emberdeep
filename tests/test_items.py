"""Item rolls: rarity, affixes, legendary uniqueness, derived stats."""

import random

from emberdeep import items
from emberdeep.engine import State


def test_loot_rolls_are_valid_items():
    rng = random.Random(1)
    spawned = set()
    for _ in range(300):
        item = items.make_loot(10, rng, spawned)
        assert item.kind in ("weapon", "armor", "ring", "potion", "scroll", "staff")
        if item.kind in ("weapon", "armor", "ring"):
            assert item.rarity in ("normal", "magic", "rare", "legendary")
            assert len(item.affixes) <= 4


def test_rarity_improves_with_depth():
    rng = random.Random(2)

    def rare_rate(depth):
        spawned = set()
        count = 0
        n = 400
        for _ in range(n):
            item = items.make_loot(depth, rng, spawned)
            if item.kind in ("weapon", "armor", "ring") and item.rarity in ("rare", "legendary"):
                count += 1
        return count / n

    assert rare_rate(12) > rare_rate(1)


def test_legendaries_never_repeat():
    rng = random.Random(3)
    spawned = set()
    seen = []
    for _ in range(3000):
        item = items.make_loot(15, rng, spawned)
        if item.legendary_id:
            seen.append(item.legendary_id)
    assert len(seen) == len(set(seen)), "a legendary spawned twice"
    assert len(seen) <= len(items.LEGENDARIES)


def test_affixes_change_derived_stats():
    state = State(seed=5)
    base = items.derived_stats(state)
    sword = items.Item("weapon", "Ember longsword of the Fox", ")", (255, 255, 255),
                       slot="weapon", dmg=(4, 7), str_req=0,
                       affixes=[("fiery", 3), ("fox", 5)], rarity="rare", base_name="longsword")
    state.player.equipment["weapon"] = sword
    boosted = items.derived_stats(state)
    assert boosted["dmg_max"] == 7
    assert boosted["fire_damage"] == 3
    assert boosted["dodge"] == base["dodge"] + 5


def test_str_req_penalty():
    state = State(seed=6)
    hammer = items.Item("weapon", "warhammer", ")", (255, 255, 255), slot="weapon",
                        dmg=(6, 10), str_req=99, base_name="warhammer")
    state.player.equipment["weapon"] = hammer
    stats = items.derived_stats(state)
    assert stats["accuracy"] < 80  # unwieldy


def test_legendary_effects_in_stats():
    state = State(seed=7)
    ring = items._legendary("salamander_ring")
    state.player.equipment["ring1"] = ring
    stats = items.derived_stats(state)
    assert stats["lava_walk"] and stats["fire_heals"] and stats["fire_immune"]
