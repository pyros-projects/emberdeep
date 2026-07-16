"""Player actions. Each perform() returns True if it consumed a turn.

These are thin command objects: __main__ translates keys into actions, the
engine supplies the state. Consumable effects live here too.
"""

from __future__ import annotations

from . import combat, entities, identify, items, terrain
from .terrain import Terrain


# --- movement / stairs ---------------------------------------------------------

def move(state, dx: int, dy: int) -> bool:
    p = state.player
    if p.statuses.get("confusion", 0) > 0:
        dx, dy = state.rng.choice([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1),
                                   (1, -1), (1, 0), (1, 1)])
        state.log("you stumble in confusion!", dim=True)
    nx, ny = p.x + dx, p.y + dy
    m = state.map
    if not m.in_bounds(nx, ny):
        return False
    target = m.actor_at(nx, ny)
    if target is not None and target.faction == "monster":
        combat.attack(state, p, target)
        return True
    if target is not None:  # ally: swap places
        target.x, target.y, p.x, p.y = p.x, p.y, nx, ny
        return True
    if not m.is_walkable(nx, ny):
        return False
    p.x, p.y = nx, ny
    item = m.item_at(nx, ny)
    if item is not None:
        state.log(f"you see {identify.display_name(state, item)} here.", dim=True)
    t = Terrain(int(m.terrain[nx, ny]))
    if t == Terrain.VENT:
        state.log("a vent hisses caustic gas here. fire would be... unwise.", dim=True)
    return True


def wait(state) -> bool:
    return True


def descend(state) -> bool:
    m = state.map
    if Terrain(int(m.terrain[state.player.x, state.player.y])) != Terrain.STAIR_DOWN:
        state.log("there are no stairs down here.", dim=True)
        return False
    state.depth += 1
    state._enter_map(state.depth, arriving_from="below")
    state.log(f"you descend. depth {state.depth}.", warn=True)
    return True


def ascend(state) -> bool:
    m = state.map
    if Terrain(int(m.terrain[state.player.x, state.player.y])) != Terrain.STAIR_UP:
        state.log("there are no stairs up here.", dim=True)
        return False
    if state.depth == 1:
        if state.has_heart:
            state.victory = True
            state.log("you climb into the light, the Emberheart warm against your chest.",
                      warn=True)
            return True
        state.log("you cannot leave without the Emberheart.", warn=True)
        return False
    state.depth -= 1
    state._enter_map(state.depth, arriving_from="above")
    state.log(f"you climb. depth {state.depth}.", warn=True)
    return True


# --- items ------------------------------------------------------------------------

def pickup(state) -> bool:
    m = state.map
    item = m.item_at(state.player.x, state.player.y)
    if item is None:
        state.log("there is nothing here to pick up.", dim=True)
        return False
    if item.kind == "heart":
        m.take_item_at(state.player.x, state.player.y)
        state.has_heart = True
        state.log("you take the EMBERHEART. the mountain itself seems to shudder.", warn=True)
        state.log("now — get out alive.", warn=True)
        for monster in m.monsters:
            monster.target = (state.player.x, state.player.y)  # the deep knows
        return True
    if len(state.player.inventory) >= 26:
        state.log("your pack is full.", dim=True)
        return False
    m.take_item_at(state.player.x, state.player.y)
    state.player.inventory.append(item)
    state.log(f"you pick up {identify.display_name(state, item)}.")
    return True


def drop(state, item) -> bool:
    p = state.player
    if item in (p.equipment or {}).values():
        state.log("unequip it first (select it again in your pack).", dim=True)
        return False
    p.inventory.remove(item)
    m = state.map
    if m.item_at(p.x, p.y) is None:
        m.items.append((p.x, p.y, item))
    else:  # don't stack two items on one cell; scatter to a neighbor
        for nx, ny in terrain.neighbors8(p.x, p.y):
            if m.is_walkable(nx, ny) and m.item_at(nx, ny) is None:
                m.items.append((nx, ny, item))
                break
        else:
            p.inventory.append(item)
            state.log("no room to drop that here.", dim=True)
            return False
    state.log(f"you drop {identify.display_name(state, item)}.")
    return True


def equip_or_use(state, item) -> bool:
    """Inventory selection: equip gear, drink/read consumables, zap staves."""
    p = state.player
    eq = p.equipment

    if item.kind in ("weapon", "armor", "ring"):
        if item in eq.values():
            for slot, worn in list(eq.items()):
                if worn is item:
                    eq.pop(slot)
                    state.log(f"you remove {item.name}.")
            return True
        slot = item.slot
        if slot == "ring":
            slot = "ring1" if "ring1" not in eq else ("ring2" if "ring2" not in eq else "ring1")
        if slot in eq:
            state.log(f"you swap {eq[slot].name} for {identify.display_name(state, item)}.")
        eq[slot] = item
        if not item.known:
            item.known = True
            item.name = items._equipment_name(item.base_name, item.affixes, item.enchant)
            state.log(f"it is {item.name}!", warn=True)
            if item.legendary_id:
                state.log(f"{item.name}: {items.LEGENDARIES[item.legendary_id]['blurb']}.",
                          warn=True)
        else:
            state.log(f"you equip {item.name}.")
        return True

    if item.kind == "potion":
        _drink(state, item)
        identify.reveal(state, item)
        p.inventory.remove(item)
        return True

    if item.kind == "scroll":
        if item.effect == "identify":
            candidates = identify.unidentified_carried(state)
            if not candidates:
                state.log("you are carrying nothing that needs identifying.", dim=True)
                return False
            state.pending_identify = item  # ui finishes the job
            return False
        _read_scroll(state, item)
        identify.reveal(state, item)
        p.inventory.remove(item)
        return True

    if item.kind == "staff":
        if item.charges <= 0:
            state.log(f"the {item.name} is spent.", dim=True)
            return False
        state.targeting = {"item": item, "x": p.x, "y": p.y}
        state.log("aim with the movement keys; enter to fire, esc to cancel.", dim=True)
        return False  # turn spent only on a successful zap

    return False


def apply_identify(state, scroll, item) -> None:
    """Scroll-of-identify completion, driven by the inventory UI."""
    if item.kind in ("potion", "scroll"):
        identify.reveal(state, item)
    else:
        item.known = True
        item.name = items._equipment_name(item.base_name, item.affixes, item.enchant)
        state.log(f"it is {item.name}!", warn=True)
    state.player.inventory.remove(scroll)
    state.pending_identify = None
    state.spend_turn()


# --- consumable effects ------------------------------------------------------------

def _drink(state, item) -> None:
    p = state.player
    effect = item.effect
    if effect == "heal":
        healed = min(30, p.max_hp - p.hp)
        p.hp += healed
        state.log(f"warmth floods your limbs. (+{healed} HP)" if healed else
                  "you feel no different.", warn=healed > 0)
    elif effect == "strength":
        p.strength += 1
        state.log("your muscles swell with power. +1 strength.", warn=True)
    elif effect == "life":
        p.max_hp += 5
        p.hp += 5
        state.log("your life force deepens. +5 max HP.", warn=True)
    elif effect == "telepathy":
        combat.add_status(p, "telepathy", 30)
        state.log("minds glimmer around you like candles.", warn=True)
    elif effect == "incineration":
        state.log("fire erupts from within you!", warn=True)
        combat.add_status(p, "burning", 4)
        terrain.ignite(state.map, p.x, p.y, fuel=2)
        state.damage_actor(p, state.rng.randint(4, 8), source="a fiery potion")
    elif effect == "confusion":
        combat.add_status(p, "confusion", 8)
        state.log("the world spins sickeningly.", warn=True)
    elif effect == "blindness":
        combat.add_status(p, "blind", 12)
        state.log("darkness floods your eyes!", warn=True)


def _read_scroll(state, item) -> None:
    p = state.player
    effect = item.effect
    if effect == "enchant_weapon":
        weapon = (p.equipment or {}).get("weapon")
        if weapon is None:
            state.log("the magic fizzles — you have no weapon equipped.", dim=True)
            p.inventory.append(item)  # refund: nothing to enchant
            return
        weapon.enchant += 1  # derived_stats adds enchant to damage
        state.log(f"your {weapon.base_name} glows with new sharpness. (+{weapon.enchant})",
                  warn=True)
    elif effect == "enchant_armor":
        armor = (p.equipment or {}).get("armor")
        if armor is None:
            state.log("the magic fizzles — you have no armor equipped.", dim=True)
            p.inventory.append(item)
            return
        armor.enchant += 1
        state.log(f"your {armor.base_name} thickens with protective runes. (+{armor.enchant})",
                  warn=True)
    elif effect == "teleport":
        pos = state.map.random_walkable(state.rng)
        if pos:
            p.x, p.y = pos
            state.log("the world folds around you!", warn=True)
    elif effect == "magic_mapping":
        import numpy as np

        walk = np.vectorize(lambda v: terrain.walkable(Terrain(int(v))))(state.map.terrain)
        state.map.explored |= walk | (state.map.terrain == Terrain.WALL)
        state.log("the layout of this level etches itself into your mind.", warn=True)
    elif effect == "fear":
        count = 0
        for monster in state.map.monsters:
            if monster.distance_to(p.x, p.y) <= 6 and monster.faction == "monster":
                combat.add_status(monster, "fear", 6)
                count += 1
        state.log(f"a wave of terror washes outward. ({count} foes flee)" if count
                  else "the magic finds no minds to seize.", warn=count > 0)


# --- staves -------------------------------------------------------------------------

def fire_staff(state, item, tx: int, ty: int) -> bool:
    """Resolve a staff zap at the target cell. Returns True if a turn was spent."""
    p = state.player
    if not state.visible[tx, ty]:
        state.log("you cannot see that spot.", dim=True)
        return False
    if max(abs(tx - p.x), abs(ty - p.y)) > 8:
        state.log("out of range.", dim=True)
        return False

    item.charges -= 1
    m = state.map
    if item.effect == "firebolt":
        state.log("a bolt of fire streaks across the room!", warn=True)
        victim = m.actor_at(tx, ty)
        if (tx, ty) == (p.x, p.y):
            victim = p
        if victim is not None:
            state.damage_actor(victim, state.rng.randint(10, 14), source="a firebolt")
            combat.add_status(victim, "burning", 2)
        if m.gas[tx, ty] > 0:
            terrain.explode(state, tx, ty)
        else:
            terrain.ignite(m, tx, ty, fuel=3)
    elif item.effect == "blink":
        if m.is_walkable(tx, ty) and m.actor_at(tx, ty) is None:
            p.x, p.y = tx, ty
            state.log("you flicker through space.", warn=True)
        else:
            state.log("the magic finds no purchase there.", dim=True)
            item.charges += 1  # refund
            return False
    elif item.effect == "lightning":
        state.log("lightning crackles from the staff!", warn=True)
        victim = m.actor_at(tx, ty)
        if victim is not None:
            state.damage_actor(victim, state.rng.randint(8, 12), source="lightning")
            others = [
                o for o in m.monsters
                if o.is_alive and o is not victim and o.distance_to(victim.x, victim.y) <= 3
            ]
            others.sort(key=lambda o: o.distance_to(victim.x, victim.y))
            for o in others[:1]:
                state.log(f"the bolt arcs to the {o.name}!", warn=True)
                state.damage_actor(o, 6, source="lightning")
        else:
            state.log("the bolt scorches the stone.", dim=True)
    if item.charges <= 0:
        state.log(f"the {item.name} crumbles to dust.", dim=True)
        if item in p.inventory:
            p.inventory.remove(item)
    return True
