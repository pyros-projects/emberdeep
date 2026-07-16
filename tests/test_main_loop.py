"""Drive the real main() event loop headless with scripted key events.

Regression test for the tcod 21 (SDL3) port: letter keysyms are plain
codepoints (``ord("h")`` style), and ``ui.draw_panel`` takes (console, state).
Both bugs crashed the SDL loop on startup while the offscreen tests stayed
green, because none of them went through __main__.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import tcod  # noqa: E402

import emberdeep.__main__ as game  # noqa: E402
from emberdeep import items  # noqa: E402


def _key(sym):
    return tcod.event.KeyDown(
        sym=sym,
        scancode=tcod.event.Scancode.UNKNOWN,
        mod=tcod.event.Modifier.NONE,
        repeat=False,
    )


def test_main_loop_full_input_cycle(monkeypatch):
    """title -> play -> levelup -> move/pickup/inventory/look/target -> title."""
    monkeypatch.setattr(game, "load_tileset", lambda: None)

    orig_state = game.State

    def patched_state():
        s = orig_state(seed=42)
        s.pending_levels = 1  # force the level-up branch
        s.player.inventory.append(items.make_consumable("staff", "blink"))
        return s

    monkeypatch.setattr(game, "State", patched_state)

    KeySym = tcod.event.KeySym
    script = [
        _key(KeySym.RETURN),   # title -> play (State created)
        _key(KeySym.PERIOD),   # wait -> spend_turn -> level-up mode
        _key(ord("s")),        # level-up: +1 strength -> play
        _key(ord("h")),        # move via vi-keys
        _key(ord("g")),        # pickup attempt
        _key(ord("i")),        # open inventory
        _key(ord("d")),        # drop mode
        _key(KeySym.ESCAPE),   # close inventory
        _key(ord("x")),        # look mode
        _key(ord("j")),        # move look cursor
        _key(KeySym.ESCAPE),   # exit look
        _key(ord("i")),        # inventory again
        _key(ord("a")),        # select staff -> targeting mode
        _key(ord("l")),        # move target cursor
        _key(ord("f")),        # fire staff -> turn spent
        _key(ord(">")),        # descend attempt (standing on up-stairs)
        _key(ord("q")),        # abandon run -> title
        tcod.event.Quit(),     # exit
    ]
    monkeypatch.setattr(
        game.tcod.event, "wait", lambda: iter([script.pop(0)])
    )

    game.main()
    assert not script, f"main() returned early: {len(script)} events unconsumed"
