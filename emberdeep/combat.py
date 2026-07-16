"""Attack resolution, status effects, and XP.

Damage flows through ``state.damage_actor`` (engine.py) so that death, XP
awards, jelly splits, wraith teleports, and legendary on-kill hooks all live
in one place.
"""

from __future__ import annotations

from .constants import (
    BASE_HIT_CHANCE,
    MAX_HIT_CHANCE,
    MIN_HIT_CHANCE,
    STR_DAMAGE_REFERENCE,
)


def add_status(actor, key: str, turns: int) -> None:
    actor.statuses[key] = max(actor.statuses.get(key, 0), turns)


def attacker_stats(state, actor) -> dict:
    """Unified view of an attacker's numbers (player stats derive from gear)."""
    if actor.is_player:
        from .items import derived_stats

        return derived_stats(state)
    return {
        "dmg_min": actor.dmg[0],
        "dmg_max": actor.dmg[1],
        "strength": 0,
        "accuracy": actor.accuracy,
        "fire_damage": 0,
        "life_on_hit": 0,
        "weapon": None,
    }


def hit_chance(state, att, dfn) -> int:
    astats = attacker_stats(state, att)
    dodge = dfn.dodge
    if dfn.is_player:
        from .items import derived_stats

        dodge = derived_stats(state)["dodge"]
    chance = BASE_HIT_CHANCE + (astats["accuracy"] - dodge)
    return max(MIN_HIT_CHANCE, min(MAX_HIT_CHANCE, chance))


def attack(state, att, dfn) -> None:
    rng = state.rng
    astats = attacker_stats(state, att)
    you = "you" if att.is_player else f"the {att.name}"
    whom = "you" if dfn.is_player else f"the {dfn.name}"

    if rng.randint(1, 100) > hit_chance(state, att, dfn):
        state.log(f"{you} {('miss' if att.is_player else 'misses')} {whom}.", dim=True)
        return

    dmg = rng.randint(astats["dmg_min"], astats["dmg_max"])
    dmg += max(0, astats["strength"] - STR_DAMAGE_REFERENCE)

    weapon = astats.get("weapon")
    if weapon is not None and weapon.legendary_id == "grudgekeeper":
        dmg += weapon.stacks
    if (
        weapon is not None
        and weapon.legendary_id == "whisperfang"
        and not dfn.is_player
        and dfn.target is None
    ):
        dmg *= 3
        state.log("you strike from the shadows!", warn=True)

    defense = dfn.defense
    if dfn.is_player:
        from .items import derived_stats

        defense = derived_stats(state)["defense"]
    dmg = max(1, dmg - defense)

    verb = "hit" if att.is_player else "hits"
    state.log(f"{you} {verb} {whom} for {dmg}." if att.is_player else f"{you} {verb} {whom} for {dmg}.",
              warn=dfn.is_player)

    if astats["fire_damage"] and not dfn.is_player:
        add_status(dfn, "burning", 3)
        state.log(f"the {dfn.name} bursts into flame!", warn=True)
    if (
        weapon is not None
        and weapon.legendary_id == "emberbrand"
        and not dfn.is_player
    ):
        from . import terrain as _terrain

        ignited = False
        for nx, ny in _terrain.neighbors8(dfn.x, dfn.y):
            ignited |= _terrain.ignite(state.map, nx, ny, fuel=3)
        if ignited:
            state.log("Emberbrand sets the ground ablaze!", warn=True)
    if astats["life_on_hit"] and att.is_player:
        healed = min(astats["life_on_hit"], att.max_hp - att.hp)
        if healed > 0:
            att.hp += healed
    if att.on_hit == "poison" and dfn.is_player:
        from .items import derived_stats

        if derived_stats(state)["poison_resist"]:
            state.log("you shrug off the venom.", dim=True)
        else:
            add_status(dfn, "poison", 8)
            state.log("you are poisoned!", warn=True)

    state.damage_actor(dfn, dmg, source=att.name if not att.is_player else "you")

    # thorns: defender's armor bites back
    if dfn.is_player and att.is_alive and not att.is_player:
        from .items import derived_stats

        thorns = derived_stats(state)["thorns"]
        if thorns:
            state.damage_actor(att, thorns, source="your thorns")

    # Stormcall: chain lightning to the two nearest other monsters
    if (
        weapon is not None
        and weapon.legendary_id == "stormcall"
        and not dfn.is_player
    ):
        others = [
            m for m in state.map.monsters
            if m.is_alive and m is not dfn and m.faction == "monster"
            and m.distance_to(dfn.x, dfn.y) <= 4
        ]
        others.sort(key=lambda m: m.distance_to(dfn.x, dfn.y))
        for m in others[:2]:
            state.log(f"lightning arcs to the {m.name}!", warn=True)
            state.damage_actor(m, 6, source="Stormcall")


def xp_to_next(level: int) -> int:
    return int(12 * (level ** 1.35)) + 6


def award_xp(state, amount: int) -> None:
    if amount <= 0:
        return
    from .items import derived_stats

    amount = int(amount * derived_stats(state)["xp_mult"])
    p = state.player
    p.xp += amount
    while p.xp >= p.xp_next:
        p.xp -= p.xp_next
        p.level += 1
        p.xp_next = xp_to_next(p.level)
        state.pending_levels += 1
        state.log(f"you feel stronger — welcome to level {p.level}!", warn=True)
