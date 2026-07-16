"""Items: equipment, Diablo-style affixes/rarity, legendaries, consumables.

Equipment is weapon / armor / two ring slots. Magic and rare items roll
affixes from a shared pool; legendaries are fixed uniques with their own
effect hooks, which combat.py and engine.py check by ``legendary_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import BASE_LIGHT_RADIUS, HEART_LIGHT_BONUS, PLAYER_ACCURACY, PLAYER_DODGE, PLAYER_FIST_DMG, RARITY_COLORS


@dataclass
class Item:
    kind: str                      # weapon|armor|ring|potion|scroll|staff|heart
    name: str
    ch: str
    color: tuple
    slot: str | None = None        # weapon|armor|ring
    dmg: tuple = (0, 0)
    defense: int = 0
    str_req: int = 0
    affixes: list = field(default_factory=list)   # (affix_key, value)
    rarity: str = "normal"
    legendary_id: str | None = None
    effect: str | None = None      # consumable effect key
    charges: int = 0
    enchant: int = 0
    stacks: int = 0                # Grudgekeeper
    known: bool = True             # equipment: affixes revealed
    base_name: str = ""            # unadorned type name ("longsword")


# --- base equipment ----------------------------------------------------------
# name, dmg, str_req, min_depth
WEAPONS = [
    ("dagger", (2, 4), 0, 1),
    ("mace", (3, 6), 6, 3),
    ("longsword", (4, 7), 7, 4),
    ("war axe", (5, 8), 8, 6),
    ("warhammer", (6, 10), 10, 8),
]
# name, defense, min_depth
ARMORS = [
    ("leather armor", 2, 1),
    ("chain mail", 4, 4),
    ("plate armor", 7, 8),
]

# --- affixes -----------------------------------------------------------------
# key: (display, is_prefix, stat, min, max, allowed kinds)
AFFIXES = {
    "fiery":     ("Ember", True, "fire_damage", 2, 4, ("weapon",)),
    "accurate":  ("True", True, "accuracy", 5, 10, ("weapon", "ring")),
    "brutal":    ("Brutal", True, "dmg_bonus", 1, 3, ("weapon",)),
    "sturdy":    ("Sturdy", True, "defense", 1, 3, ("armor",)),
    "vigorous":  ("of Vigor", False, "hp_bonus", 5, 12, ("armor", "ring")),
    "fox":       ("of the Fox", False, "dodge", 3, 6, ("armor", "ring")),
    "leech":     ("of the Leech", False, "life_on_hit", 1, 3, ("weapon",)),
    "luminous":  ("of Light", False, "light_radius", 1, 2, ("ring",)),
    "scholar":   ("of the Scholar", False, "xp_pct", 10, 25, ("ring",)),
    "thorns":    ("of Thorns", False, "thorns", 1, 3, ("armor",)),
    "fireproof": ("Fireproof", True, "fire_immune", 1, 1, ("armor", "ring")),
    "venom":     ("of the Antidote", False, "poison_resist", 1, 1, ("armor", "ring")),
    "swift":     ("of Swiftness", False, "swift", 15, 25, ("ring",)),
    "lucky":     ("Lucky", True, "lucky", 3, 5, ("ring",)),
}

# --- consumables --------------------------------------------------------------
POTIONS = {
    "heal":        "potion of healing",
    "strength":    "potion of strength",
    "life":        "potion of life",
    "telepathy":   "potion of telepathy",
    "incineration": "potion of incineration",
    "confusion":   "potion of confusion",
    "blindness":   "potion of blindness",
}
GOOD_POTIONS = ("heal", "strength", "life", "telepathy")

SCROLLS = {
    "identify": "scroll of identify",
    "enchant_weapon": "scroll of enchant weapon",
    "enchant_armor": "scroll of enchant armor",
    "teleport": "scroll of teleportation",
    "magic_mapping": "scroll of magic mapping",
    "fear": "scroll of fear",
}

STAVES = {
    "firebolt": ("staff of firebolt", 4),
    "blink": ("staff of blink", 3),
    "lightning": ("staff of lightning", 4),
}

KIND_GLYPHS = {
    "weapon": (")", (210, 200, 190)),
    "armor": ("[", (190, 180, 170)),
    "ring": ("o", (230, 190, 90)),
    "potion": ("!", (220, 90, 160)),
    "scroll": ("?", (215, 200, 160)),
    "staff": ("/", (170, 120, 220)),
    "heart": ("&", (250, 80, 40)),
}


# --- legendaries ---------------------------------------------------------------
def _legendary(legendary_id: str) -> Item:
    L = LEGENDARIES[legendary_id]
    item = Item(
        kind=L["kind"], name=L["name"], ch=KIND_GLYPHS[L["kind"]][0],
        color=RARITY_COLORS["legendary"], slot=L["kind"],
        dmg=L.get("dmg", (0, 0)), defense=L.get("defense", 0),
        str_req=L.get("str_req", 0), rarity="legendary",
        legendary_id=legendary_id, known=False,
        base_name=L.get("base", L["kind"]),
    )
    return item


LEGENDARIES = {
    "emberbrand": dict(name="Emberbrand", kind="weapon", dmg=(4, 7), str_req=7,
                       base="longsword",
                       blurb="its hits ignite flesh and terrain alike"),
    "gloomward": dict(name="Gloomward", kind="armor", defense=7, base="plate armor",
                      blurb="fire and gas cannot touch you, but the dark closes in"),
    "stormcall": dict(name="Stormcall", kind="weapon", dmg=(6, 10), str_req=10,
                      base="warhammer",
                      blurb="every blow arcs lightning to nearby foes"),
    "salamander_ring": dict(name="Ring of the Salamander", kind="ring", base="ring",
                            blurb="walk through lava; flame itself heals you"),
    "whisperfang": dict(name="Whisperfang", kind="weapon", dmg=(2, 4), base="dagger",
                        blurb="triples damage against enemies that haven't seen you"),
    "bulwark": dict(name="Bulwark of the Deep", kind="armor", defense=9,
                    base="plate armor",
                    blurb="a wall of steel, at the cost of accuracy"),
    "echoes_ring": dict(name="Ring of Echoes", kind="ring", base="ring",
                        blurb="your kills may raise a friendly shade"),
    "grudgekeeper": dict(name="Grudgekeeper", kind="weapon", dmg=(5, 8), str_req=8,
                         base="war axe",
                         blurb="every wound you suffer feeds its edge"),
}


# --- construction --------------------------------------------------------------
def _roll_rarity(depth: int, rng) -> str:
    normal = max(15, 72 - 4 * depth)
    magic = 22 + 3 * depth
    rare = 4 + 2 * depth
    roll = rng.uniform(0, normal + magic + rare)
    if roll < normal:
        return "normal"
    if roll < normal + magic:
        return "magic"
    return "rare"


def _roll_affixes(kind: str, rarity: str, rng) -> list:
    count = {"normal": 0, "magic": rng.randint(1, 2), "rare": rng.randint(3, 4)}[rarity]
    pool = [k for k, a in AFFIXES.items() if kind in a[5]]
    rng.shuffle(pool)
    out = []
    for key in pool[:count]:
        a = AFFIXES[key]
        out.append((key, rng.randint(a[3], a[4])))
    return out


def _equipment_name(base: str, affixes: list, enchant: int) -> str:
    name = base
    for key, _ in affixes:
        if AFFIXES[key][1]:  # prefix
            name = f"{AFFIXES[key][0]} {name}"
            break
    for key, _ in affixes:
        if not AFFIXES[key][1]:  # suffix
            name = f"{name} {AFFIXES[key][0]}"
            break
    if enchant:
        name = f"+{enchant} {name}"
    return name


def make_equipment(kind: str, depth: int, rng) -> Item:
    rarity = _roll_rarity(depth, rng)
    if kind == "weapon":
        options = [w for w in WEAPONS if w[3] <= depth] or [WEAPONS[0]]
        name, dmg, str_req, _ = options[rng.randrange(len(options))]
        item = Item("weapon", name, *KIND_GLYPHS["weapon"], slot="weapon",
                    dmg=dmg, str_req=str_req)
    elif kind == "armor":
        options = [a for a in ARMORS if a[2] <= depth] or [ARMORS[0]]
        name, defense, _ = options[rng.randrange(len(options))]
        item = Item("armor", name, *KIND_GLYPHS["armor"], slot="armor", defense=defense)
    else:
        item = Item("ring", "ring", *KIND_GLYPHS["ring"], slot="ring")
        if rarity == "normal":
            rarity = "magic"  # a plain ring is useless; always at least magic
    item.base_name = item.name
    item.rarity = rarity
    item.affixes = _roll_affixes(kind, rarity, rng)
    item.color = RARITY_COLORS[rarity]
    if item.affixes:
        item.known = False
    item.name = _equipment_name(item.name, item.affixes if item.known else [], 0)
    return item


def make_consumable(kind: str, effect: str) -> Item:
    ch, color = KIND_GLYPHS[kind]
    if kind == "potion":
        return Item("potion", POTIONS[effect], ch, color, effect=effect)
    if kind == "scroll":
        return Item("scroll", SCROLLS[effect], ch, color, effect=effect)
    name, charges = STAVES[effect]
    return Item("staff", name, ch, color, effect=effect, charges=charges)


def make_heart() -> Item:
    return Item("heart", "the Emberheart", *KIND_GLYPHS["heart"])


def make_loot(depth: int, rng, spawned_legendaries: set) -> Item:
    """One random depth-appropriate drop."""
    remaining = [k for k in LEGENDARIES if k not in spawned_legendaries]
    if remaining and rng.random() < 0.03:
        key = remaining[rng.randrange(len(remaining))]
        spawned_legendaries.add(key)
        return _legendary(key)

    roll = rng.random()
    if roll < 0.18:
        return make_equipment("weapon", depth, rng)
    if roll < 0.30:
        return make_equipment("armor", depth, rng)
    if roll < 0.40:
        return make_equipment("ring", depth, rng)
    if roll < 0.68:
        effect = list(POTIONS)[rng.randrange(len(POTIONS))]
        return make_consumable("potion", effect)
    if roll < 0.88:
        effect = list(SCROLLS)[rng.randrange(len(SCROLLS))]
        return make_consumable("scroll", effect)
    effect = list(STAVES)[rng.randrange(len(STAVES))]
    return make_consumable("staff", effect)


def place_items(game_map, depth: int, rng, spawned_legendaries: set) -> None:
    ux, uy = game_map.up_stairs
    avoid = {(ux, uy)}
    for _ in range(rng.randint(4, 7)):
        pos = game_map.random_walkable(rng, avoid=avoid)
        if pos:
            game_map.items.append((pos[0], pos[1], make_loot(depth, rng, spawned_legendaries)))


# --- derived player stats -------------------------------------------------------
def derived_stats(state) -> dict:
    p = state.player
    eq = p.equipment or {}
    weapon = eq.get("weapon")
    armor = eq.get("armor")
    worn = [weapon, armor, eq.get("ring1"), eq.get("ring2")]

    dmg_min, dmg_max = (weapon.dmg if weapon else PLAYER_FIST_DMG)
    dmg_bonus = weapon.enchant if weapon else 0
    stats = {
        "dmg_min": dmg_min + dmg_bonus,
        "dmg_max": dmg_max + dmg_bonus,
        "strength": p.strength,
        "accuracy": PLAYER_ACCURACY + p.acc_bonus,
        "dodge": PLAYER_DODGE,
        "defense": (armor.defense + armor.enchant) if armor else 0,
        "hp_bonus": 0,
        "light_radius": BASE_LIGHT_RADIUS + (HEART_LIGHT_BONUS if state.has_heart else 0),
        "fire_damage": 0,
        "life_on_hit": 0,
        "thorns": 0,
        "xp_mult": 1.0,
        "poison_resist": False,
        "fire_immune": p.fire_immune,
        "lava_walk": False,
        "fire_heals": False,
        "gas_immune": False,
        "echo_shade": False,
        "swift": 0,
        "weapon": weapon,
    }
    for item in worn:
        if item is None:
            continue
        for key, value in item.affixes:
            stat = AFFIXES[key][2]
            if stat == "dmg_bonus":
                stats["dmg_min"] += value
                stats["dmg_max"] += value
            elif stat == "xp_pct":
                stats["xp_mult"] += value / 100.0
            elif stat in ("fire_immune", "poison_resist"):
                stats[stat] = True
            elif stat in ("accuracy", "dodge", "defense", "hp_bonus", "light_radius",
                          "fire_damage", "life_on_hit", "thorns", "swift"):
                stats[stat] += value
        if item.legendary_id == "emberbrand":
            stats["fire_damage"] += 4
        elif item.legendary_id == "gloomward":
            stats["fire_immune"] = True
            stats["gas_immune"] = True
            stats["light_radius"] = max(3, stats["light_radius"] - 2)
        elif item.legendary_id == "salamander_ring":
            stats["lava_walk"] = True
            stats["fire_heals"] = True
            stats["fire_immune"] = True
        elif item.legendary_id == "bulwark":
            stats["accuracy"] -= 10
        elif item.legendary_id == "echoes_ring":
            stats["echo_shade"] = True

    if weapon and stats["strength"] < weapon.str_req:
        stats["accuracy"] -= 25  # too heavy to wield well
    stats["light_radius"] = max(3, stats["light_radius"])
    return stats
