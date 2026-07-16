"""The game state and turn engine.

Turn order: player action → world tick (fire/gas simulation, terrain hazards,
status effects) → monster turns. All randomness flows through one seeded
``random.Random`` so runs are reproducible and tests are deterministic.
"""

from __future__ import annotations

import random
import time

import numpy as np
import tcod

from . import combat, dungeon, entities, identify, items, terrain
from .constants import MAX_DEPTH, PLAYER_HP, PLAYER_STR
from .terrain import Terrain

EPITAPHS = [
    "the deep keeps what it takes",
    "another name the stone forgets",
    "the ember fades to black",
    "the dungeon is patient. it can wait",
    "ashes settle where you fell",
]


class State:
    def __init__(self, seed: int | None = None):
        self.seed = seed if seed is not None else int(time.time() * 1000) % (2**31)
        self.rng = random.Random(self.seed)
        self.depth = 1
        self.maps: dict[int, dungeon.GameMap] = {}
        self.turn = 0
        self.messages: list[dict] = []
        self.identified: set[str] = set()
        self.appearances = identify.make_appearances(self.rng)
        self.legendaries_spawned: set[str] = set()
        self.has_heart = False
        self.pending_levels = 0
        self.game_over = False
        self.victory = False
        self.death_cause = ""
        self.visible = np.zeros((0, 0), dtype=bool)
        # UI state handled by __main__: pending scroll-of-identify selection,
        # active staff targeting cursor
        self.pending_identify = None
        self.targeting = None

        self.player = entities.Actor(
            x=0, y=0, ch="@", color=(238, 226, 200), name="you",
            hp=PLAYER_HP, max_hp=PLAYER_HP, dmg=(1, 3), accuracy=80, dodge=10,
            defense=0, xp_value=0, faction="player", is_player=True,
            inventory=[], equipment={}, strength=PLAYER_STR,
            xp_next=combat.xp_to_next(1),
        )
        self._enter_map(1, arriving_from="below")
        self.log("you descend into the Emberdeep, seeking the Emberheart.", warn=True)
        self.log("retrieve it from depth 15 and return alive.", dim=True)

    # --- maps ---------------------------------------------------------------
    @property
    def map(self) -> dungeon.GameMap:
        return self.maps[self.depth]

    def _enter_map(self, depth: int, arriving_from: str) -> None:
        if depth not in self.maps:
            m = dungeon.generate(depth, self.rng)
            entities.populate(m, depth, self.rng)
            items.place_items(m, depth, self.rng, self.legendaries_spawned)
            if depth == MAX_DEPTH:
                self._place_heart(m)
            self.maps[depth] = m
        self.depth = depth
        m = self.map
        if arriving_from == "below":
            self.player.x, self.player.y = m.up_stairs
        else:
            self.player.x, self.player.y = m.down_stairs or m.up_stairs
        self.recompute_fov()

    def _place_heart(self, m: dungeon.GameMap) -> None:
        room = m.rooms[-1]
        hx, hy = room.center
        m.terrain[hx, hy] = Terrain.FLOOR
        m.items.append((hx, hy, items.make_heart()))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            wx, wy = hx + dx, hy + dy
            if m.is_walkable(wx, wy):
                m.monsters.append(entities.spawn("warden", wx, wy))
                break

    # --- logging --------------------------------------------------------------
    def log(self, text: str, warn: bool = False, dim: bool = False) -> None:
        self.messages.append({"text": text, "turn": self.turn, "warn": warn, "dim": dim})
        del self.messages[:-80]

    # --- FOV --------------------------------------------------------------------
    def recompute_fov(self) -> None:
        from .items import derived_stats

        radius = derived_stats(self)["light_radius"]
        if self.player.statuses.get("blind", 0) > 0:
            radius = 1
        transparency = np.vectorize(lambda v: terrain.transparent(Terrain(int(v))))(
            self.map.terrain
        )
        self.visible = tcod.map.compute_fov(
            transparency,
            (self.player.x, self.player.y),
            radius=radius,
            light_walls=True,
            algorithm=tcod.constants.FOV_SYMMETRIC_SHADOWCAST,
        )
        self.map.explored |= self.visible

    # --- turn flow ----------------------------------------------------------------
    def spend_turn(self) -> None:
        """Run after any successful player action."""
        if self.game_over:
            return
        self.turn += 1
        self.world_tick()
        from .items import derived_stats

        stats = derived_stats(self)
        skip_monsters = stats["swift"] and self.rng.randint(1, 100) <= stats["swift"]
        if skip_monsters:
            self.log("you move like quicksilver.", dim=True)
        if not self.game_over and not skip_monsters:
            self.monsters_act()
        self.recompute_fov()

    def world_tick(self) -> None:
        terrain.tick(self)
        m = self.map
        for actor in [self.player, *m.monsters]:
            if not actor.is_alive:
                continue
            self._hazards(actor)
            self._tick_statuses(actor)
        m.monsters = [a for a in m.monsters if a.is_alive]

    def _hazards(self, actor) -> None:
        from .items import derived_stats

        m = self.map
        x, y = actor.x, actor.y
        fire_immune = actor.fire_immune
        lava_walk = False
        fire_heals = False
        gas_immune = False
        if actor.is_player:
            stats = derived_stats(self)
            fire_immune = fire_immune or stats["fire_immune"]
            lava_walk = stats["lava_walk"]
            fire_heals = stats["fire_heals"]
            gas_immune = stats["gas_immune"]
        t = Terrain(int(m.terrain[x, y]))
        if m.fire[x, y] > 0 and t != Terrain.WATER:
            if fire_heals:
                actor.hp = min(actor.max_hp, actor.hp + 2)
            elif not fire_immune:
                self.damage_actor(actor, self.rng.randint(2, 4), source="the flames")
                combat.add_status(actor, "burning", 2)
        if actor.is_alive and t == Terrain.LAVA:
            if fire_heals or lava_walk:
                actor.hp = min(actor.max_hp, actor.hp + 3)
            else:
                self.damage_actor(actor, self.rng.randint(8, 12), source="the lava")
                combat.add_status(actor, "burning", 3)
        if actor.is_alive and t == Terrain.WATER and actor.statuses.get("burning"):
            del actor.statuses["burning"]
            if actor.is_player:
                self.log("the water douses the flames.", dim=True)
        if actor.is_alive and m.gas[x, y] > 0 and not gas_immune:
            self.damage_actor(actor, 1, source="the choking gas")

    def _tick_statuses(self, actor) -> None:
        for key in list(actor.statuses):
            if not actor.is_alive:
                break
            if key == "burning":
                self.damage_actor(actor, 2, source="burning")
            elif key == "poison":
                self.damage_actor(actor, 1, source="poison")
            elif key == "fade":
                pass
            actor.statuses[key] -= 1
            if actor.statuses[key] <= 0:
                if key == "fade" and actor.is_alive:
                    actor.hp = 0
                    actor.statuses.pop(key, None)
                    if self.visible[actor.x, actor.y]:
                        self.log(f"the {actor.name} dissipates into nothing.", dim=True)
                    continue
                actor.statuses.pop(key, None)

    def monsters_act(self) -> None:
        for actor in list(self.map.monsters):
            if not actor.is_alive or not self.player.is_alive:
                continue
            entities.act(self, actor)
            if actor.fast and actor.is_alive and self.rng.random() < 0.3:
                entities.act(self, actor)

    # --- damage & death -------------------------------------------------------------
    def damage_actor(self, actor, amount: int, source: str = "") -> None:
        if not actor.is_alive or amount <= 0:
            return
        actor.hp -= amount

        if actor.is_player:
            weapon = (actor.equipment or {}).get("weapon")
            if weapon is not None and weapon.legendary_id == "grudgekeeper":
                weapon.stacks = min(weapon.stacks + 1, 12)
            if actor.hp <= 0:
                actor.hp = 0
                self.game_over = True
                self.death_cause = source or "the deep"
                self.log(f"you die, slain by {self.death_cause}...", warn=True)
            return

        # monsters --------------------------------------------------------------
        if actor.is_alive:
            if actor.can_split and actor.hp > 2:
                self._split_jelly(actor)
            if actor.is_alive and actor.teleport_on_hit and self.rng.random() < 0.5:
                self._teleport_monster(actor)
            return

        # it died ----------------------------------------------------------------
        if self.visible[actor.x, actor.y]:
            self.log(f"the {actor.name} dies.", dim=True)
        combat.award_xp(self, actor.xp_value)

        if source in ("you", "your thorns"):
            weapon = (self.player.equipment or {}).get("weapon")
            if weapon is not None and weapon.legendary_id == "grudgekeeper":
                weapon.stacks = 0
            from .items import derived_stats

            if derived_stats(self)["echo_shade"] and self.rng.random() < 0.25:
                self._raise_shade(actor)

        if self.rng.random() < 0.12 and self.map.item_at(actor.x, actor.y) is None:
            loot = items.make_loot(self.depth, self.rng, self.legendaries_spawned)
            self.map.items.append((actor.x, actor.y, loot))

    def _split_jelly(self, actor) -> None:
        actor.can_split = False
        for nx, ny in terrain.neighbors8(actor.x, actor.y):
            if self.map.is_walkable(nx, ny) and self.map.actor_at(nx, ny) is None:
                child = entities.spawn("jelly", nx, ny)
                child.can_split = False
                child.hp = child.max_hp = max(1, actor.hp // 2)
                actor.hp = max(1, actor.hp - child.hp)
                self.map.monsters.append(child)
                if self.visible[actor.x, actor.y]:
                    self.log("the jelly splits in two!", warn=True)
                return

    def _teleport_monster(self, actor) -> None:
        pos = self.map.random_walkable(self.rng)
        if pos and max(abs(pos[0] - self.player.x), abs(pos[1] - self.player.y)) > 2:
            actor.x, actor.y = pos
            actor.target = None
            if self.visible[actor.x, actor.y]:
                self.log(f"the {actor.name} flickers away!", dim=True)

    def _raise_shade(self, victim) -> None:
        for nx, ny in terrain.neighbors8(victim.x, victim.y):
            if self.map.is_walkable(nx, ny) and self.map.actor_at(nx, ny) is None:
                shade = entities.spawn("shade", nx, ny)
                combat.add_status(shade, "fade", 20)
                self.map.monsters.append(shade)
                self.log("an echoing shade rises to fight for you!", warn=True)
                return

    # --- level-ups ---------------------------------------------------------------------
    def apply_level_choice(self, choice: str) -> None:
        p = self.player
        if choice == "s":
            p.strength += 1
            self.log("your arms harden. +1 strength.", warn=True)
        elif choice == "a":
            p.acc_bonus += 3
            self.log("your strikes find their mark. +3 accuracy.", warn=True)
        else:
            p.max_hp += 6
            p.hp = min(p.max_hp, p.hp + 6)
            self.log("your vitality surges. +6 max HP.", warn=True)
        self.pending_levels = max(0, self.pending_levels - 1)

    # --- victory --------------------------------------------------------------------------
    def score(self) -> int:
        return self.depth * 10 + self.player.level * 5 + self.turn // 10
