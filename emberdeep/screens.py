"""Title, death, and victory screens. Pure ASCII — the tileset has nothing else."""

from __future__ import annotations

from .constants import CONSOLE_H, CONSOLE_W, GOLD, IVORY, LOG_FRESH, LOG_STALE

TITLE_ART = [
    " ___ __  __ ___  ___ ___  ___  ___ ___ ___ ",
    "| __|  \\/  | _ )| __| _ \\|   \\| __| __| _ \\",
    "| _|| |\\/| | _ \\| _||   /| |) | _|| _||  _/",
    "|___|_|  |_|___/|___|_|_\\|___/|___|___|_|  ",
]

TAGLINE = "a small brogue-like. take the emberheart. come back alive."


def _center(console, y: int, text: str, fg=LOG_FRESH) -> None:
    console.print(max(0, (CONSOLE_W - len(text)) // 2), y, text, fg=fg)


def draw_title(console) -> None:
    y = CONSOLE_H // 2 - 8
    for i, line in enumerate(TITLE_ART):
        _center(console, y + i, line, fg=(240 - i * 20, 120 + i * 10, 40))
    _center(console, y + 6, TAGLINE, fg=LOG_STALE)
    _center(console, y + 9, "press ENTER to descend", fg=IVORY)
    _center(console, y + 10, "press q to quit", fg=LOG_STALE)
    controls = "move: arrows / numpad / hjkl+yubn   > descend   < ascend   g grab   i pack   x look"
    _center(console, y + 13, controls, fg=LOG_STALE)


def draw_death(console, state) -> None:
    _overlay(console)
    y = CONSOLE_H // 2 - 4
    import random as _r

    from .engine import EPITAPHS

    _center(console, y, "Y O U   D I E D", fg=(220, 60, 40))
    _center(console, y + 2, f"slain by {state.death_cause} on depth {state.depth}", fg=LOG_FRESH)
    epitaph = EPITAPHS[state.seed % len(EPITAPHS)]
    _center(console, y + 3, epitaph, fg=LOG_STALE)
    _center(console, y + 5, f"score {state.score()}   level {state.player.level}   {state.turn} turns",
            fg=GOLD)
    _center(console, y + 7, "press any key", fg=LOG_STALE)


def draw_victory(console, state) -> None:
    _overlay(console)
    y = CONSOLE_H // 2 - 4
    _center(console, y, "* * *  Y O U   E S C A P E D  * * *", fg=GOLD)
    _center(console, y + 2, "the Emberheart pulses warmly in your pack", fg=LOG_FRESH)
    _center(console, y + 3, "the deep will remember your name", fg=LOG_STALE)
    _center(console, y + 5, f"score {state.score()}   level {state.player.level}   {state.turn} turns",
            fg=GOLD)
    _center(console, y + 7, "press any key", fg=LOG_STALE)


def _overlay(console) -> None:
    console.rgb["fg"][:] = console.rgb["fg"][:] // 3
    console.rgb["bg"][:] = console.rgb["bg"][:] // 3
