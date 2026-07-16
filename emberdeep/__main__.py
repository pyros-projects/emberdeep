"""Entry point: tileset loading, the tcod context, and the input state machine.

Input modes: title → play ⇄ inventory / look / target / levelup → dead|victory.
"""

from __future__ import annotations

import os

import tcod
from tcod.event import KeySym

from . import actions, render, screens, ui
from .constants import CONSOLE_H, CONSOLE_W, MAP_H
from .engine import State

FONT_CANDIDATES = [
    "/System/Library/Fonts/SFNSMono.ttf",
    "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "C:\\Windows\\Fonts\\consola.ttf",
    "C:\\Windows\\Fonts\\cour.ttf",
]

MOVES = {
    KeySym.UP: (0, -1), KeySym.DOWN: (0, 1), KeySym.LEFT: (-1, 0), KeySym.RIGHT: (1, 0),
    KeySym.KP_8: (0, -1), KeySym.KP_2: (0, 1), KeySym.KP_4: (-1, 0), KeySym.KP_6: (1, 0),
    KeySym.KP_7: (-1, -1), KeySym.KP_9: (1, -1), KeySym.KP_1: (-1, 1), KeySym.KP_3: (1, 1),
    ord("h"): (-1, 0), ord("j"): (0, 1), ord("k"): (0, -1), ord("l"): (1, 0),
    ord("y"): (-1, -1), ord("u"): (1, -1), ord("b"): (-1, 1), ord("n"): (1, 1),
}

def load_tileset() -> tcod.tileset.Tileset:
    candidates = [os.environ.get("EMBERDEEP_FONT"), *FONT_CANDIDATES]
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            return tcod.tileset.load_truetype_font(path, 9, 16)
        except Exception:
            continue
    raise SystemExit(
        "Emberdeep: no usable font found. Set EMBERDEEP_FONT=/path/to/mono.ttf"
    )


def main() -> None:
    tileset = load_tileset()
    with tcod.context.new(
        columns=CONSOLE_W, rows=CONSOLE_H, tileset=tileset,
        title="Emberdeep", vsync=True,
    ) as context:
        root = tcod.console.Console(CONSOLE_W, CONSOLE_H, order="F")
        mode = "title"
        state: State | None = None
        look = [0, 0]
        inv_purpose = "use"

        while True:
            root.clear()
            if mode == "title":
                screens.draw_title(root)
            else:
                render.render_map(state, root)
                ui.draw_panel(root, state)
                if mode == "inventory":
                    ui.draw_inventory(root, state, inv_purpose)
                elif mode == "look":
                    render.highlight_cell(root, look[0], look[1])
                    ui.draw_look_bar(root, state, look[0], look[1])
                elif mode == "target":
                    t = state.targeting
                    ui.draw_target_line(root, state, t["x"], t["y"])
                    render.highlight_cell(root, t["x"], t["y"], color=(80, 40, 30))
                elif mode == "levelup":
                    ui.draw_levelup(root, state)
                elif mode == "dead":
                    screens.draw_death(root, state)
                elif mode == "victory":
                    screens.draw_victory(root, state)
            context.present(root)

            for event in tcod.event.wait():
                if isinstance(event, tcod.event.Quit):
                    return
                if not isinstance(event, tcod.event.KeyDown):
                    continue
                sym = event.sym

                if mode == "title":
                    if sym in (KeySym.RETURN, KeySym.KP_ENTER):
                        state = State()
                        mode = "play"
                    elif sym == ord("q"):
                        return

                elif mode in ("dead", "victory"):
                    mode = "title"

                elif mode == "levelup":
                    choice = {ord("s"): "s", ord("a"): "a", ord("v"): "v"}.get(sym)
                    if choice:
                        state.apply_level_choice(choice)
                        if state.pending_levels <= 0:
                            mode = "play"

                elif mode == "play":
                    spent = False
                    if sym in MOVES:
                        spent = actions.move(state, *MOVES[sym])
                    elif sym in (KeySym.PERIOD, KeySym.KP_5):
                        spent = actions.wait(state)
                    elif sym == ord(">"):
                        spent = actions.descend(state)
                    elif sym == ord("<"):
                        spent = actions.ascend(state)
                    elif sym == ord("g"):
                        spent = actions.pickup(state)
                    elif sym == ord("i"):
                        inv_purpose = "use"
                        mode = "inventory"
                    elif sym == ord("x"):
                        look = [state.player.x, state.player.y]
                        mode = "look"
                    elif sym == ord("q"):
                        mode = "title"
                        continue
                    if spent:
                        state.spend_turn()
                        if state.game_over:
                            mode = "dead"
                        elif state.victory:
                            mode = "victory"
                        elif state.pending_levels > 0:
                            mode = "levelup"
                        elif state.targeting:
                            mode = "target"
                        elif state.pending_identify:
                            inv_purpose = "identify"
                            mode = "inventory"

                elif mode == "look":
                    if sym in MOVES:
                        dx, dy = MOVES[sym]
                        look[0] = min(max(look[0] + dx, 0), state.map.width - 1)
                        look[1] = min(max(look[1] + dy, 0), state.map.height - 1)
                    elif sym in (KeySym.ESCAPE, ord("x"), KeySym.RETURN):
                        mode = "play"

                elif mode == "target":
                    t = state.targeting
                    if sym in MOVES:
                        dx, dy = MOVES[sym]
                        t["x"] = min(max(t["x"] + dx, 0), state.map.width - 1)
                        t["y"] = min(max(t["y"] + dy, 0), state.map.height - 1)
                    elif sym in (KeySym.RETURN, KeySym.KP_ENTER, ord("f")):
                        item = t["item"]
                        state.targeting = None
                        mode = "play"
                        if actions.fire_staff(state, item, t["x"], t["y"]):
                            state.spend_turn()
                            if state.game_over:
                                mode = "dead"
                            elif state.victory:
                                mode = "victory"
                            elif state.pending_levels > 0:
                                mode = "levelup"
                    elif sym == KeySym.ESCAPE:
                        state.targeting = None
                        mode = "play"

                elif mode == "inventory":
                    inv = state.player.inventory
                    if sym == KeySym.ESCAPE:
                        state.pending_identify = None
                        mode = "play"
                    elif sym == ord("d") and inv_purpose == "use":
                        inv_purpose = "drop"
                    elif ord("a") <= sym <= ord("z"):
                        idx = sym - ord("a")
                        if idx < len(inv):
                            item = inv[idx]
                            if inv_purpose == "identify":
                                # apply_identify spends the turn itself
                                actions.apply_identify(state, state.pending_identify, item)
                                mode = "play"
                            elif inv_purpose == "drop":
                                if actions.drop(state, item):
                                    state.spend_turn()
                                mode = "play"
                            else:
                                spent = actions.equip_or_use(state, item)
                                if state.targeting:
                                    mode = "target"
                                elif state.pending_identify:
                                    inv_purpose = "identify"
                                else:
                                    mode = "play"
                                if spent:
                                    state.spend_turn()
                                    if state.game_over:
                                        mode = "dead"
                                    elif state.pending_levels > 0:
                                        mode = "levelup"


if __name__ == "__main__":
    main()
