"""The identification minigame.

Potion colors and scroll titles are shuffled per run. Using an item (or a
scroll of identify) reveals its type for the rest of the run. Equipment with
affixes shows as "unusual" / "ornate" until equipped once — Brogue-style,
softened: there are no curses.
"""

from __future__ import annotations

POTION_LOOKS = [
    "a murky crimson potion",
    "a swirling silver potion",
    "an opaque black potion",
    "a fizzy orange potion",
    "a milky white potion",
    "a deep azure potion",
    "a viscous green potion",
]

SCROLL_LOOKS = [
    "a scroll titled 'ZORN'",
    "a scroll inscribed 'GEBETH'",
    "a scroll marked 'VULKAN'",
    "a scroll labeled 'ASHKAR'",
    "a scroll reading 'MIRATH'",
    "a scroll scrawled 'OLUX'",
]


def make_appearances(rng) -> dict:
    from .items import POTIONS, SCROLLS

    looks = POTION_LOOKS[:]
    rng.shuffle(looks)
    table = {effect: looks[i] for i, effect in enumerate(POTIONS)}
    titles = SCROLL_LOOKS[:]
    rng.shuffle(titles)
    table.update({effect: titles[i] for i, effect in enumerate(SCROLLS)})
    return table


def display_name(state, item) -> str:
    """What the player sees in inventory / on the ground."""
    if item.kind == "potion" and item.effect not in state.identified:
        return state.appearances[item.effect]
    if item.kind == "scroll" and item.effect not in state.identified:
        return state.appearances[item.effect]
    if item.kind in ("weapon", "armor", "ring") and not item.known:
        adj = "an ornate" if item.rarity == "legendary" else "an unusual"
        return f"{adj} {item.base_name or item.name}"
    return item.name


def reveal(state, item) -> None:
    """Mark a consumable type as identified run-wide."""
    if item.kind in ("potion", "scroll") and item.effect:
        first = item.effect not in state.identified
        state.identified.add(item.effect)
        if first:
            state.log(f"it was {item.name}!", warn=True)


def unidentified_carried(state) -> list:
    out = []
    for item in state.player.inventory:
        if item.kind in ("potion", "scroll") and item.effect not in state.identified:
            out.append(item)
        elif item.kind in ("weapon", "armor", "ring") and not item.known:
            out.append(item)
    return out
