# Plan: EMBERDEEP — a small Brogue-like ASCII roguelike

A compact, true-color ASCII roguelike in the spirit of Brogue: dark jewel-toned
dungeons, field-of-view lighting, risky item identification, and terrain that
fights back (spreading fire, explosive gas, water, lava). Character power comes
from XP levels plus **Diablo-style itemization**: magic/rare items with rolled
affixes and a handful of gameplay-changing legendary artifacts.

## Stack & setup

- Python 3.11+, `python-tcod` (console rendering, FOV, pathfinding, input events)
- `requirements.txt` (`tcod`, dev: `pytest`), run via `python -m emberdeep`
- Target ~2k lines; no engine, no assets, no build step

## Project layout

```
kimitest/
├── requirements.txt
├── README.md                 # run instructions, controls, design notes
├── main.py                   # thin entry point
├── emberdeep/
│   ├── __main__.py           # tcod context, main loop wiring
│   ├── constants.py          # glyphs, palette, tuning tables
│   ├── engine.py             # GameState, turn scheduler (player → world → monsters)
│   ├── actions.py            # Move/Melee/Wait/Descend/UseItem/Drop/Target actions
│   ├── dungeon.py            # map gen: rooms+corridors, cave patches, terrain features, stairs
│   ├── terrain.py            # tile flags + fire/gas/water/lava simulation tick
│   ├── entities.py           # Actor, simple AI (chase/flee/erratic/ranged), bestiary
│   ├── combat.py             # attack/defense/damage rolls, XP & leveling
│   ├── items.py              # equipment, consumables, affixes, rarity rolls, legendaries
│   ├── identify.py           # per-run appearance shuffle, identification state
│   ├── render.py             # map/entity drawing, FOV lighting & tints, fire flicker
│   ├── ui.py                 # bottom panel (HP/depth/XP/log), inventory, look, targeting
│   └── screens.py            # title, death, victory
└── tests/
    ├── test_dungeon.py       # connectivity, stairs present, depth sanity
    ├── test_items.py         # affix/rarity rolls, legendary uniqueness (seeded)
    ├── test_identify.py      # shuffle stable per seed, use-identifies
    └── test_terrain.py       # fire spread/ burnout, gas ignition (seeded)
```

## Core loop & controls

- Turn-based, 8-direction movement (arrows + numpad + vi keys), bump-to-attack,
  `.` wait, `>` descend, `g` pick up, `i` inventory, `x` look mode, `q`/`Q` quit.
- Turn order: player action → world tick (fire spread, gas diffusion, status
  effects) → every monster acts. Simple and deterministic.
- 15 depths. Retrieve the **Emberheart** on depth 15, then ascend back to
  depth 1 to win (Brogue-style round trip). Death is permanent; no saves.

## Dungeon generation (`dungeon.py`)

- Random rooms joined by L-corridors, plus a cellular-automata cave patch or two
  per level for Brogue's organic feel. Rooms get themes: fungal grove
  (flammable grass), flooded chamber (water), gas pocket (vent tiles), and from
  depth 8+ lava channels.
- Guaranteed: up-stairs, down-stairs, full connectivity (BFS check, regenerate
  if disconnected — covered by test).
- 6–10 monsters and 4–7 items per level, both drawn from depth-scaled tables.

## Rendering & art direction (`render.py`, `constants.py`)

This is where the Brogue feel lives — treat it as a first-class feature:

- True-color console, 90×55, map viewport ~80×45. Unexplored = black.
- Palette: charcoal stone, muted moss, deep water blue, ember orange lava;
  items in bright jewel tones; player `@` warm ivory.
- FOV via tcod shadowcasting with distance falloff: visible cells tinted toward
  dark with distance; remembered cells drawn desaturated at ~30% brightness.
- Fire tiles flicker (per-frame brightness jitter); gas gets a sickly
  translucent green tint; water/lava shimmer via subtle per-tile hue variance.

## Combat & character (`combat.py`)

- Stats: HP, strength (damage + heavy-weapon requirements), defense (armor),
  accuracy/dodge. Damage = weapon range + str bonus − defense, with hit chance
  from accuracy vs dodge.
- XP from kills; level-up = +HP and choice of +str / +accuracy / +max HP.
- Status effects: burning (DoT + panic), poisoned, confused, telepathy
  (see monsters through walls). Delivered by monsters, items, and terrain.

## Monsters (`entities.py`)

~11 types, depth-scaled, each with one trick:

| Monster | Trick |
|---|---|
| Rat, Kobold | filler melee |
| Bat | erratic random movement |
| Goblin | flees at low HP |
| Spider | poison on hit |
| Jelly | splits once when hit |
| Imp | throws fire — ignites terrain |
| Wraith | teleports, evasive |
| Ogre | slow, huge damage |
| Naga | fast, guards treasure |
| Fire elemental | burning aura, leaves fire |
| Ember warden | depth-15 guardian of the Emberheart |

## Items (`items.py`)

**Equipment:** weapon, armor, 2 ring slots. Base types per slot with
depth-scaled stats (dagger → longsword → warhammer; leather → chain → plate;
rings have no base stats, only affixes).

**Rarity & affixes (Diablo-style):**
- Normal (no affix), Magic (1–2 affixes), Rare (3–4 affixes), Legendary (fixed
  unique). Drop weights shift toward higher rarity with depth.
- Affix pool (~14): +damage, +accuracy, +strength, +defense, +max HP, life on
  hit, fire damage (ignites target — terrain synergy), poison resist, +light
  radius, +XP gain, thorns, +move speed on kill, burning immunity, lucky dodge.
- Names generated from affixes: "Ember Longsword of the Fox".

**Legendaries (8, unique per run, each changes how you play):**
- *Emberbrand* (sword) — hits ignite target and adjacent flammable terrain
- *Gloomward* (armor) — immune to fire/gas, but −2 light radius
- *Stormcall* (hammer) — hits chain lightning to 2 nearest enemies
- *Ring of the Salamander* — walk through lava unharmed; fire heals you
- *Whisperfang* (dagger) — +300% damage when attacking from out of the
  target's view (backstab)
- *Bulwark of the Deep* (armor) — knockback immunity, +huge defense, −accuracy
- *Ring of Echoes* — your kills have 25% chance to raise a friendly shade
- *Grudgekeeper* (axe) — +damage stacking each time you're hit, resets on kill

**Consumables:** potions (heal, extra life?, fire, confusion, blindness,
telepathy, strength) and scrolls (identify, enchant weapon/armor, teleport,
magic mapping, fear). Plus 3 staves with charges: firebolt, blink, lightning —
these introduce the reusable targeting UI.

## Identify minigame (`identify.py`)

- Per run, potion colors and scroll titles are shuffled ("a murky crimson
  potion"). Using an item identifies its type for the rest of the run;
  scroll of identify reveals without risk.
- Bad outcomes exist: drinking incineration sets you (and the floor) ablaze.
- Equipment with affixes shows as "unusual longsword" until equipped once
  (Brogue-style equip-to-identify, softened: no curses in this game).

## Terrain simulation (`terrain.py`)

- Tile flags: `flammable` (grass, fungus), `gas` (vent emission), `liquid`
  (water/lava), plus per-cell fire state (fuel remaining).
- Each world tick: burning cells damage occupants, lose fuel, and roll to ignite
  adjacent flammables. Gas cells drift 1 tile per turn up to a small radius;
  fire touching gas detonates it in a 2-tile blast. Water extinguishes actors
  and blocks fire spread; lava damages and ignites anything entering.
- Simulation is budgeted: only cells on an "active" list are processed, so late
  turns on a settled level cost nothing.

## UI (`ui.py`, `screens.py`)

- Bottom panel: HP bar, depth, XP, level, equipped weapon/armor, 5-line message
  log with Brogue-ish flavor ("the kobold hits you. the grass catches fire.")
- Inventory: list with identify state; use / equip / drop; staves show charges.
- Look mode (`x`): move cursor, describes tile/monster/item under it.
- Targeting mode for staves/scrolls: line preview, confirm/fire, esc cancel.
- Title screen, death screen (killer + depth + epitaph), victory screen.

## Explicitly out of scope

Allies, quests, mouse UI, save/restore, sound, tiles/sprites, ranged weapons
for the player, cursed items, in-game seed selection.

## Milestones (in order, each independently verifiable)

1. **Scaffold** — venv, requirements, `python -m emberdeep` opens a tcod window
   with a walking `@` on a hardcoded room.
2. **Dungeon + descent** — generation, connectivity check, stairs, 15 depths.
3. **Brogue look** — FOV, palette, lighting falloff, remembered map, flicker.
4. **Combat core** — monsters, AI, bump combat, HP, XP/levels, permadeath,
   death screen.
5. **Items & inventory** — pickup, equip, consumables, loot tables, UI.
6. **Identify** — per-run shuffle, use-to-identify, scroll of identify.
7. **Itemization** — affixes, rarity, the 8 legendaries and their effects.
8. **Terrain** — fire/gas/water/lava simulation, imp fireballs, staff synergy,
   Emberheart + ascent victory.
9. **Polish** — look mode, message flavor, balance pass (depth difficulty
   curve), README.
10. **Tests** — the 4 pytest files above, run with `pytest`; all logic tests
    use seeded RNG, no window required.

## Verification

- `pytest` green at each milestone ≥4.
- Manual playthrough smoke checks per milestone: reach depth 3 (M4), identify a
  potion by drinking (M6), equip a legendary and see its effect fire (M7),
  ignite a gas pocket with an imp's fireball (M8), die and restart (M4+).
