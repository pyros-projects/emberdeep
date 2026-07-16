"""Offscreen rendering: tcod.Consoles are pure data, no window required."""

import tcod

from emberdeep import render, screens, ui
from emberdeep.constants import CONSOLE_H, CONSOLE_W
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
