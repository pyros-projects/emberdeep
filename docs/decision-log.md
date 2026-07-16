# Decision Log — how EMBERDEEP was built

This log records the original prompts and the decisions they produced, in
order, so anyone can recreate this project with an AI coding agent (it was
built with [Kimi Code](https://github.com/MoonshotAI/kimi-cli)) starting
from an empty directory. Everything here actually happened; the prompts are
verbatim.

The artifact each step produced is linked where it exists.

---

## Step 1 — Planning the game

**Prompt:**

> plan a small ASCII roguelike similar to brogue in its gameplay and art direction

The agent entered plan mode and, instead of guessing, asked two clarifying
questions. The answers shaped everything:

| question | answer |
|---|---|
| Language/platform? | **Python + python-tcod** (over Rust+bracket-lib, Python+curses, JS+rot.js) |
| Brogue systems in scope? | **Identify minigame**, **terrain interactions** (fire/gas/water/lava) |
| Custom addition (free text) | "I also want a powerful diablo like itemization with gameplay chaning legendary artifacts!" *[sic]* |

Notably, "item-based advancement" (Brogue's no-XP design) was *not* picked,
so the plan paired the Diablo itemization with classic **XP leveling**.

**Resulting design decisions** (full text in
[design-plan.md](design-plan.md)):

- 15 depths, permadeath; retrieve the **Emberheart** on depth 15 and ascend
  back out to win (Brogue's round trip).
- Terrain simulation: spreading fire, explosive gas pockets, water, lava.
- 8 legendaries with gameplay-changing hooks (Emberbrand, Stormcall,
  Whisperfang, Grudgekeeper, Gloomward, Bulwark of the Deep, Ring of the
  Salamander, Ring of Echoes).
- ~2,000 lines, modular package, seeded RNG everywhere, pytest for logic.
- Explicitly out of scope: allies, quests, mouse UI, saves, sound, tiles.

The plan was approved as written.

## Step 2 — Building it

No prompt needed — the agent executed the approved plan milestone by
milestone. Decisions that emerged *during* implementation:

- **Depth scaling for monsters.** A scripted balance probe
  (`scripts/balance_probe.py`) duels depth-appropriate players against every
  monster. First run showed zero deaths anywhere — flat monster stats made
  the player a demigod by depth 9. Fix: spawns scale with depth (+10% HP
  per depth, +damage and accuracy). Result: trash mobs chip 1–5 HP per
  kill, an ogre at depth 7 averages 23 of your 48 HP and sometimes kills.
- **Fonts.** `.ttc` font collections fail in SDL_ttf; plain `.ttf` works.
  The loader tries SF Mono → Andale Mono → Courier New (macOS), DejaVu /
  Liberation (Linux), Consolas / Courier (Windows), then tells you to set
  `EMBERDEEP_FONT`.
- **A real bug the tests caught:** gas explosions only damaged monsters,
  never the player (`actor_at` didn't include them). Found by
  `test_gas_explodes_with_fire`, fixed before anyone got singed unfairly.
- Verification was entirely headless: 26 seeded pytest tests, offscreen
  rendering, and a bot that dove to depth 15, took the Heart, and won.

## Step 3 — Documentation

**Prompt:**

> can you copy the plan into a docs/ folder in this project, and also write a small documentation for end users? like game ideas, controls, and so on

Decisions:

- The approved plan was copied **verbatim** to
  [design-plan.md](design-plan.md) — history, not a living spec.
- The end-user doc ([guide.md](guide.md)) was written for players, not
  devs: premise first, a glyph/color legend for reading ASCII, controls,
  then the identification system, rarity tiers, legendaries, and survival
  tips built around terrain.

## Step 4 — The banner

**Prompt:**

> and for the README it would be cool if it would lead with a sick banner image

Decisions:

- **Generate it from the game itself**, not clip art:
  `scripts/make_banner.py` builds a real depth-10 dungeon with the game's
  own palette and light falloff, stages a scene (glowing `@`, an imp next
  to a lichen fire, monsters, loot, a gas vent, self-lit lava), and
  overlays an ember-gradient title with a blurred glow.
- It took three iterations, each checked visually: v1 was nearly black
  (vignette + falloff too harsh), v2 hid the player under the title band,
  v3 is what ships. Seed **13**, deterministic:
  `.venv/bin/python scripts/make_banner.py 13`
- `pillow` was added as a dev-only dependency for this.

---

## Remake recipe

Paste these into a fresh agent session, in an empty directory, in order:

1. `plan a small ASCII roguelike similar to brogue in its gameplay and art direction`
   — when asked, pick **Python + python-tcod**, the **identify minigame**
   and **terrain interactions**, and add: *"I also want powerful
   diablo-like itemization with gameplay-changing legendary artifacts."*
   Approve the plan.
2. `copy the plan into a docs/ folder, and write a small documentation for end users — game ideas, controls, and so on`
3. `make the README lead with a sick banner image`

You won't get byte-identical output (the agent makes its own small choices
en route), but you'll get the same game: same structure, same systems,
same look.

---

*After the banner, the project was committed, pushed, and published to
GitHub with description and topics — ordinary release chores, omitted here
since they're not part of recreating the game.*
