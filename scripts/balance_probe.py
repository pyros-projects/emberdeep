"""Rough balance probe: average HP a depth-appropriate player loses per kill.

Not a test — a tuning tool. Run: .venv/bin/python scripts/balance_probe.py
"""

import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emberdeep import combat, entities, items
from emberdeep.engine import State


def duel(depth: int, mkey: str, trials: int = 40):
    losses, deaths = [], 0
    for t in range(trials):
        s = State(seed=9000 + t * 31 + depth)
        p = s.player
        p.level = depth
        p.max_hp = 30 + 6 * (depth // 2)
        p.hp = p.max_hp
        p.strength = 5 + depth // 2
        import random

        rng = random.Random(depth * 1000 + t)
        for kind in ("weapon", "armor"):
            it = items.make_equipment(kind, depth, rng)
            it.known = True
            p.equipment[kind] = it
        mon = entities._scale(entities.spawn(mkey, p.x + 1, p.y), depth)
        s.map.monsters.append(mon)
        start_hp = p.hp
        while mon.is_alive and p.is_alive:
            combat.attack(s, p, mon)
            if mon.is_alive:
                combat.attack(s, mon, p)
        if p.is_alive:
            losses.append(start_hp - p.hp)
        else:
            deaths += 1
    avg = statistics.mean(losses) if losses else float("inf")
    return avg, deaths


def main():
    print(f"{'monster':<15}{'depth':>6}{'avg HP lost':>12}{'deaths/40':>10}{'player HP':>10}")
    for depth in (1, 3, 5, 7, 9, 11, 13, 15):
        keys = [k for k, w, lo, hi in entities.SPAWN_TABLE if lo <= depth <= hi]
        for key in keys:
            avg, deaths = duel(depth, key)
            hp = 30 + 6 * (depth // 2)
            flag = "  <-- LETHAL" if deaths >= 4 else ""
            print(f"{key:<15}{depth:>6}{avg:>12.1f}{deaths:>10}{hp:>10}{flag}")
        print()


if __name__ == "__main__":
    main()
