"""Identification: stable shuffle per seed, use-to-identify, appearances."""

import random

from emberdeep import identify, items
from emberdeep.engine import State


def test_appearance_shuffle_stable_per_seed():
    a = identify.make_appearances(random.Random(9))
    b = identify.make_appearances(random.Random(9))
    c = identify.make_appearances(random.Random(10))
    assert a == b
    assert a != c
    # every potion effect has a look and vice versa
    assert set(a) >= set(items.POTIONS) | set(items.SCROLLS)


def test_unidentified_display_uses_appearance():
    state = State(seed=11)
    potion = items.make_consumable("potion", "heal")
    assert identify.display_name(state, potion) == state.appearances["heal"]
    assert "healing" not in identify.display_name(state, potion)


def test_use_identifies_type_runwide():
    state = State(seed=12)
    potion = items.make_consumable("potion", "heal")
    state.player.inventory.append(potion)
    from emberdeep import actions

    assert "heal" not in state.identified
    actions.equip_or_use(state, potion)
    assert "heal" in state.identified
    assert potion not in state.player.inventory  # consumed
    other = items.make_consumable("potion", "heal")
    assert identify.display_name(state, other) == "potion of healing"


def test_equipment_unknown_until_equipped():
    state = State(seed=13)
    sword = items.Item("weapon", "Ember longsword", ")", (255, 255, 255), slot="weapon",
                       dmg=(4, 7), affixes=[("fiery", 3)], rarity="magic",
                       known=False, base_name="longsword")
    assert identify.display_name(state, sword) == "an unusual longsword"
    state.player.inventory.append(sword)
    from emberdeep import actions

    actions.equip_or_use(state, sword)
    assert sword.known
    assert identify.display_name(state, sword) == "Ember longsword"
