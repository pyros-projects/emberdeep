# Emberdeep — Player's Guide

*A small Brogue-like. Take the Emberheart. Come back alive.*

## The idea

Somewhere under the mountain burns the **Emberheart**, and you have decided
— foolishly — to fetch it. Descend 15 levels of dark, jewel-toned dungeon,
grab it, and climb all the way back out. The way down is only half the game:
the way up is the other half, and the deep remembers you.

There are no saves. Death is permanent. Every run is a new dungeon.

The dungeon itself is your biggest enemy and your best weapon. Lichen
catches fire. Gas pockets explode. Water saves your life. Learn to fight
*with* the terrain and you might see daylight again.

## Running the game

```sh
.venv/bin/python -m emberdeep
```

(First time only: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`)

## Reading the screen

| glyph | meaning |
|---|---|
| `@` | you |
| `#` | stone wall |
| `.` | floor |
| `"` | lichen (flammable!) |
| `%` | glowfungus (flammable!) |
| `~` | water |
| `=` | lava |
| `:` | gas vent |
| `<` `>` | stairs up / down |
| `!` | potion |
| `?` | scroll |
| `)` | weapon |
| `[` | armor |
| `o` | ring |
| `/` | staff |
| `&` | the Emberheart |
| `*` | fire |
| letters | monsters — each kind has its own letter and color |

Cells you can see are lit, brightest near you. Cells you merely *remember*
are dim and gray. Everything else is black. Green-tinted cells are full of
flammable gas — mind your firebolts.

The bottom panel shows your HP, XP, level, any conditions (BURNING,
POISONED...), your gear, and the message log. Read the log. The game tells
you everything that matters, once.

## Controls

| key | action |
|---|---|
| arrows / numpad / `hjkl` + `yubn` | move (walk into a monster to attack) |
| `.` or numpad `5` | wait one turn |
| `>` | descend stairs |
| `<` | ascend stairs |
| `g` | pick up what's under you |
| `i` | inventory — letter to use/equip, `d` then letter to drop, esc to close |
| `x` | look around (move the cursor, esc to stop) |
| `q` | abandon the run |

## Turns, fighting, dying

Everything moves when you move. Stand still and the world holds its breath;
step, and every monster gets a turn too.

Walk into a monster to hit it. Damage depends on your weapon, your strength,
and its armor; whether you *hit* depends on accuracy vs dodge. Kills grant
XP, and each level-up lets you pick **+strength**, **+accuracy**, or
**+max HP**.

Monsters have personalities. Goblins rout when hurt. Jellies split. Imps
throw fire — and fire spreads. Ogres are slow but take half your health in
one swing. The deeper you go, the tougher the same breeds become.

## Items and identification

Most of what you find is **unidentified**. A potion is just "a murky
crimson potion" until you drink one like it — then you know that color for
the rest of the run. Some potions heal. Some are incineration. That's the
game. Scrolls of identify remove the gamble; drinking on a full stomach at
full HP next to water is the other way to hedge it.

Equipment with a magical glow shows as "an unusual longsword" (or "an
ornate..." for something truly special) until you wear it once.

Gear comes in rarities — **normal**, **magic** (blue, 1–2 enchantments),
**rare** (yellow, 3–4), and **legendary** (orange, unique). Enchantments
add damage, accuracy, defense, health, light, lifesteal, fire, swiftness
and more.

Eight **legendaries** exist, one copy each per run:

- **Emberbrand** — hits set enemies *and the terrain* on fire
- **Stormcall** — blows arc lightning to nearby foes
- **Whisperfang** — triple damage against enemies that haven't spotted you
- **Grudgekeeper** — every wound you suffer makes it hit harder
- **Gloomward** — immune to fire and gas, but your light shrinks
- **Bulwark of the Deep** — a wall of steel, at the cost of accuracy
- **Ring of the Salamander** — lava and flame *heal* you
- **Ring of Echoes** — your kills may raise a shade that fights for you

## Survival tips

- Fire spreads one tile per turn through lichen. You can outrun it, funnel
  it, or start it. Monsters usually can't path through it.
- A gas pocket plus one spark equals a room-sized bomb. Lure monsters in
  first. Don't be in it yourself.
- Burning? Get to water. Standing in water also blocks fire spread.
- Lava hurts. A lot. Everything that isn't you avoids it — use that.
- Enemies that haven't noticed you yet take triple damage from a certain
  dagger. Watch for monsters that wander.
- Quaffing an unknown potion next to a gas vent is a way to die that has
  its own epitaph.
- The Emberheart shines with its own light once you carry it — and every
  monster on the level knows exactly where you are. The climb out is the
  hard part.

Good luck. The deep is patient.
