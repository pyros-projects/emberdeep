"""Offscreen rendering: tcod.Consoles are pure data, no window required."""

import tcod

from emberdeep import render, screens, ui
from emberdeep.constants import CONSOLE_H, CONSOLE_W, MAP_H
from emberdeep.engine import State


def _console():
    return tcod.console.Console(CONSOLE_W, CONSOLE_H, order="F")


def test_render_map_and_panel_offscreen():
    import numpy as np

    state = State(seed=777)
    con = _console()
    render.render_map(state, con)
    ui.draw_panel(con, state)
    # the player glyph must be on the console
    assert con.rgb["ch"][state.player.x, state.player.y] == ord("@")
    # visible cells are lit; unexplored cells stay black
    unexplored = np.argwhere(~state.map.explored)
    assert len(unexplored) > 0
    ux, uy = unexplored[0]
    assert con.rgb["fg"][ux, uy].max() == 0
    lit = np.argwhere(state.visible)
    lx, ly = lit[0]
    assert con.rgb["fg"][lx, ly].max() > 0


def test_all_screens_draw_offscreen():
    state = State(seed=778)
    con = _console()
    render.render_map(state, con)
    ui.draw_panel(con, state)
    ui.draw_inventory(con, state, "use")
    ui.draw_levelup(con, state)
    ui.draw_look_bar(con, state, state.player.x, state.player.y)
    screens.draw_title(con)
    screens.draw_death(con, state)
    screens.draw_victory(con, state)


def test_panel_layout_spacing():
    """Wide HP values must not jam into the XP label; statuses must not
    collide with LV — they live on the gear row."""
    state = State(seed=780)
    p = state.player
    p.max_hp = p.hp = 130
    p.statuses["burning"] = 3
    con = _console()
    ui.draw_panel(con, state)
    stat_row = "".join(chr(c) for c in con.rgb["ch"][:, MAP_H + 1])
    assert "130/130  XP" in stat_row
    assert "LV 1" in stat_row
    gear_row = "".join(chr(c) for c in con.rgb["ch"][:, MAP_H + 2])
    assert "W: fists" in gear_row
    assert "BURNING" in gear_row


def test_fire_and_gas_render():
    state = State(seed=779)
    con = _console()
    # a visible neighbor of the player (the player's own cell is overdrawn by @)
    x, y = state.player.x + 1, state.player.y
    assert state.visible[x, y]
    state.map.fire[x, y] = 3
    state.map.gas[x, y + 1] = 3
    render.render_map(state, con)
    assert con.rgb["ch"][x, y] == ord("*")
