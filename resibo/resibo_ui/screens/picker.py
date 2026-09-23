"""Startup screen: pick a case, or add another one.

Cards are drawn, not themed, so they can grow and brighten under the cursor.
`tick()` runs from the render loop and eases each card toward its hover state.
"""

import math

import dearpygui.dearpygui as dpg
from .. import data, state, theme as th, widgets as w

CARD_W, CARD_H = 210, 230
GAP = 22
EASE = 0.22            # how quickly a card settles into its hover state
GROW = 12              # extra pixels a card gains when hovered

# Light/dark switch: a sliding knob that crossfades between a sun and a moon.
SWITCH_W, SWITCH_H = 60, 28
KNOB_R = 11
PAD = 3
LEFT_CX = PAD + KNOB_R
RIGHT_CX = SWITCH_W - PAD - KNOB_R
LIGHT_TRACK = (247, 197, 115)
DARK_TRACK = (34, 40, 64)
KNOB_COL = (252, 250, 246)
SUN_COL = (255, 176, 44)
MOON_COL = (222, 226, 238)
SWITCH_EASE = 0.22

# app.run() supplies these.
_open_case = [None]
_new_case = [None]
_on_select = [None]
_set_theme = [None]

# Index of the highlighted case, or None. Selecting is one click; two opens it.
_selected = [None]

# One entry per card: cell, drawlist, kind ("case" or "add"), index, hover 0..1
_cards = []


def set_handlers(on_open, on_new, on_select=None, on_theme=None):
    _open_case[0] = on_open
    _new_case[0] = on_new
    _on_select[0] = on_select
    _set_theme[0] = on_theme


def selected():
    """Index of the highlighted case, or None."""
    return _selected[0]


def clear_selection():
    _selected[0] = None
    if _on_select[0]:
        _on_select[0](None)
    refresh()


def build():
    with dpg.child_window(width=-1, height=-1, border=True) as pane:
        dpg.add_spacer(height=40)
        # Heading on the left, the theme picker on the right.
        with dpg.table_row(parent=w.header_row(0)):
            with dpg.group():
                w.text("Select a case", "text", "h1", wrap=-1)
                w.spacer(4)
                w.mono("Click to select, double click to open.", "faint", small=True)
            _theme_toggle()
        w.spacer(22)
        with dpg.group(tag="pk_grid"):
            _fill()
    dpg.bind_item_theme(pane, th.T["pane"])


_switch = {"pos": 0.0, "target": 0.0, "pending": None, "track": None}


def _theme_toggle():
    """A pill switch: sun for light, moon for dark, sliding between the two."""
    with dpg.group():
        w.spacer(10)
        with dpg.child_window(width=SWITCH_W, height=SWITCH_H, border=False,
                              no_scrollbar=True, no_scroll_with_mouse=True) as cell:
            track = dpg.add_drawlist(width=SWITCH_W, height=SWITCH_H)
        dpg.bind_item_theme(cell, th.T["bare"])
        pos = 1.0 if th.CURRENT[0] == "Dark" else 0.0
        _switch.update(pos=pos, target=pos, pending=None, track=track)
        _draw_switch(track, pos)
        state.on_click(cell, _toggle_switch)
        with dpg.tooltip(cell):
            w.text("Switch to " + ("light" if th.CURRENT[0] == "Dark" else "dark"),
                  "text", "ui_sm", wrap=-1)


def _draw_switch(target, pos):
    """Redraw the switch at one point along its slide (0 = light, 1 = dark)."""
    dpg.delete_item(target, children_only=True)
    dpg.push_container_stack(target)
    track_col = _mix(LIGHT_TRACK, DARK_TRACK, pos)
    dpg.draw_rectangle((0, 0), (SWITCH_W, SWITCH_H), fill=track_col, color=th.BORDER,
                       thickness=1, rounding=SWITCH_H / 2)

    cx = LEFT_CX + (RIGHT_CX - LEFT_CX) * pos
    cy = SWITCH_H / 2
    dpg.draw_circle((cx, cy), KNOB_R, fill=KNOB_COL, color=(0, 0, 0, 0))

    sun_a, moon_a = 1.0 - pos, pos
    if sun_a > 0.02:
        col = SUN_COL + (int(255 * sun_a),)
        dpg.draw_circle((cx, cy), 4.4, fill=col, color=col)
        for i in range(8):                   # eight short rays around the disc
            angle = math.pi * i / 4
            dpg.draw_line((cx + math.cos(angle) * 6.5, cy + math.sin(angle) * 6.5),
                          (cx + math.cos(angle) * 9, cy + math.sin(angle) * 9),
                          color=col, thickness=1.4)
    if moon_a > 0.02:
        col = MOON_COL + (int(255 * moon_a),)
        cut = KNOB_COL + (int(255 * moon_a),)
        dpg.draw_circle((cx, cy), 6.2, fill=col, color=col)
        dpg.draw_circle((cx + 3.0, cy - 1.4), 5.2, fill=cut, color=cut)
    dpg.pop_container_stack()


def _toggle_switch(sender=None, app_data=None, user_data=None):
    """Start the slide; the theme itself switches once it settles (see tick())."""
    if _switch["pending"]:
        return
    going_dark = _switch["target"] < 0.5
    _switch["target"] = 1.0 if going_dark else 0.0
    _switch["pending"] = "Dark" if going_dark else "Light"


def _tick_switch():
    track = _switch["track"]
    if track is None or not dpg.does_item_exist(track):
        return
    pos, target = _switch["pos"], _switch["target"]
    moved = (target - pos) * SWITCH_EASE
    pos = target if abs(moved) < 0.004 else pos + moved
    if pos != _switch["pos"]:
        _switch["pos"] = pos
        _draw_switch(track, pos)
    if pos == target and _switch["pending"]:
        theme = _switch["pending"]
        _switch["pending"] = None
        if _set_theme[0]:
            _set_theme[0](theme)


def refresh():
    state.rebuild("pk_grid", _fill)


def _fill():
    """One card per case, then the add tile."""
    _cards.clear()
    per_row = max(1, (layout_width() + GAP) // (CARD_W + GAP))
    tiles = [("case", i) for i in range(len(data.CASES))] + [("add", -1)]

    for start in range(0, len(tiles), per_row):
        with dpg.group(horizontal=True):
            for kind, index in tiles[start:start + per_row]:
                _card(kind, index)
        w.spacer(GAP)


def layout_width():
    # The picker has no rail and no side columns, so it gets the whole window.
    from .. import layout
    return layout.full_width()


def _card(kind, index):
    """A drawn tile that reacts to the cursor."""
    with dpg.child_window(width=CARD_W, height=CARD_H, border=False,
                          no_scrollbar=True, no_scroll_with_mouse=True) as cell:
        art = dpg.add_drawlist(width=CARD_W, height=CARD_H)
    dpg.bind_item_theme(cell, th.T["bare"])
    entry = {"cell": cell, "art": art, "kind": kind, "index": index, "hover": 0.0}
    _cards.append(entry)
    _draw(entry)
    state.on_click(cell, _click, (kind, index))
    state.on_double_click(cell, _double_click, (kind, index))


def _click(sender, app_data, user_data):
    """One click highlights a case; the add tile opens straight away."""
    kind, index = user_data
    if kind == "add":
        _selected[0] = None
        if _on_select[0]:
            _on_select[0](None)
        if _new_case[0]:
            _new_case[0]()
        return
    _selected[0] = None if _selected[0] == index else index
    if _on_select[0]:
        _on_select[0](_selected[0])
    for card in _cards:
        _draw(card)


def _double_click(sender, app_data, user_data):
    """Two clicks open the case."""
    kind, index = user_data
    if kind == "case" and _open_case[0]:
        _selected[0] = index
        _open_case[0](index)


def _draw(entry):
    """Repaint one card at its current hover amount."""
    h = entry["hover"]
    art = entry["art"]
    dpg.delete_item(art, children_only=True)
    dpg.push_container_stack(art)

    chosen = entry["kind"] == "case" and _selected[0] == entry["index"]
    lift = max(h, 1.0 if chosen else 0.0)     # a picked card stays raised
    pad = 10 - lift * GROW * 0.5              # the tile grows as it is hovered
    left, top = pad, pad
    right, bottom = CARD_W - pad, CARD_H - pad - 44

    if entry["kind"] == "add":
        edge = _mix(th.BORDER, th.GREEN, lift)
        dpg.draw_rectangle((left, top), (right, bottom), fill=th.BG_CARD,
                           color=edge, thickness=1.5, rounding=10)
        cx, cy = (left + right) / 2, (top + bottom) / 2
        arm = 22 + lift * 4
        dpg.draw_line((cx - arm, cy), (cx + arm, cy), color=edge, thickness=3)
        dpg.draw_line((cx, cy - arm), (cx, cy + arm), color=edge, thickness=3)
        label, sub, tone = "Add another case", "manual intake", edge
    else:
        case = data.CASES[entry["index"]]
        tone = th.GREEN if case["tone"] == "green" else th.BLUE
        edge = tone if chosen else _mix(th.BORDER, tone, h)
        body = _mix(th.BG_CARD, th.BG_CARD_HOVER, lift)
        dpg.draw_rectangle((left, top), (right, bottom), fill=body,
                           color=edge, thickness=2.5 if chosen else 1.5, rounding=10)

        # A folder mark, brighter as the card is hovered.
        cx, cy = (left + right) / 2, (top + bottom) / 2
        fw, fh = 54 + lift * 6, 40 + lift * 5
        mark = _mix(tuple(int(c * 0.55) for c in tone), tone, lift)
        dpg.draw_rectangle((cx - fw / 2, cy - fh / 2 - 8),
                           (cx - fw / 6, cy - fh / 2 - 1), fill=mark, color=mark)
        dpg.draw_rectangle((cx - fw / 2, cy - fh / 2), (cx + fw / 2, cy + fh / 2),
                           fill=mark, color=mark, rounding=4)
        dpg.draw_text((cx - 26, cy + fh / 2 + 10), "{} of {}".format(
            case["done"], len(data.STEPS)), size=14, color=th.TEXT_FAINT)

        label, sub = case["number"], case["place"]

    # Captions under the tile brighten with hover.
    name_col = _mix(th.TEXT_DIM, th.TEXT, lift)
    sub_col = _mix(th.TEXT_FAINT, th.TEXT_DIM, lift)
    dpg.draw_text((left, bottom + 12), label, size=17, color=name_col)
    dpg.draw_text((left, bottom + 34), sub, size=14, color=sub_col)
    dpg.pop_container_stack()


def _mix(a, b, t):
    """Blend two colours."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def tick():
    """Ease every card and the theme switch toward their target. Called once per frame."""
    for entry in _cards:
        if not dpg.does_item_exist(entry["cell"]):
            continue
        target = 1.0 if dpg.is_item_hovered(entry["cell"]) else 0.0
        moved = (target - entry["hover"]) * EASE
        if abs(moved) < 0.004:
            if entry["hover"] != target:
                entry["hover"] = target
                _draw(entry)
            continue
        entry["hover"] += moved
        _draw(entry)
    _tick_switch()
