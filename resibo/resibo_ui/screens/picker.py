"""Startup screen: pick a case, or add another one.

Cards are drawn, not themed, so they can grow and brighten under the cursor.
`tick()` runs from the render loop and eases each card toward its hover state.
"""

import dearpygui.dearpygui as dpg
from .. import data, state, theme as th, widgets as w

CARD_W, CARD_H = 210, 230
GAP = 22
EASE = 0.22            # how quickly a card settles into its hover state
GROW = 12              # extra pixels a card gains when hovered

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
            _settings()
        w.spacer(22)
        with dpg.group(tag="pk_grid"):
            _fill()
    dpg.bind_item_theme(pane, th.T["pane"])


def _settings():
    """A gear that opens the theme menu."""
    with dpg.group():
        w.spacer(8)
        with dpg.child_window(width=40, height=40, border=False,
                              no_scrollbar=True, no_scroll_with_mouse=True) as cell:
            gear = dpg.add_drawlist(width=40, height=40)
        dpg.bind_item_theme(cell, th.T["bare"])
        _draw_gear(gear)

        state.on_click(cell, _toggle_menu)


def _draw_gear(target):
    """A settings cog, drawn so it needs no icon font."""
    import math
    dpg.delete_item(target, children_only=True)
    dpg.push_container_stack(target)
    cx = cy = 20
    col = th.TEXT_DIM
    for i in range(8):                       # eight teeth around the rim
        angle = math.pi * i / 4
        dpg.draw_line((cx + math.cos(angle) * 9, cy + math.sin(angle) * 9),
                      (cx + math.cos(angle) * 14, cy + math.sin(angle) * 14),
                      color=col, thickness=3)
    dpg.draw_circle((cx, cy), 9, color=col, thickness=2.4)
    dpg.draw_circle((cx, cy), 3.4, color=col, thickness=2)
    dpg.pop_container_stack()


MENU_W, MENU_H = 200, 240
_menu_open = [False]


def build_menu():
    """The theme menu, created once and shown beside the gear."""
    with dpg.window(tag="theme_menu", show=False, no_title_bar=True, no_resize=True,
                    no_move=True, no_collapse=True, no_scrollbar=True,
                    no_scroll_with_mouse=True, width=MENU_W, height=MENU_H) as win:
        w.text("Theme", "dim", "ui_sm", wrap=-1)
        w.spacer(8)
        for name in th.ORDER:
            mark = ">  " if name == th.CURRENT[0] else "    "
            row = dpg.add_button(label=mark + name, width=MENU_W - 32,
                                 callback=_pick_theme, user_data=name)
            w.font(row, "mono_sm")
            dpg.bind_item_theme(row, th.T["pill_green"] if name == th.CURRENT[0]
                                else th.T["btn_ghost"])
            w.spacer(4)
    dpg.bind_item_theme(win, th.T["panel"])


def _toggle_menu(sender=None, app_data=None, user_data=None):
    if _menu_open[0]:
        hide_menu()
        return
    try:
        width = dpg.get_viewport_client_width()
    except Exception:
        width = 1500
    dpg.configure_item("theme_menu", show=True,
                       pos=(max(10, width - MENU_W - 30), 208))
    dpg.focus_item("theme_menu")     # keep it above the page behind it
    _menu_open[0] = True


def hide_menu(sender=None, app_data=None, user_data=None):
    if dpg.does_item_exist("theme_menu"):
        dpg.configure_item("theme_menu", show=False)
    _menu_open[0] = False


def menu_open():
    return _menu_open[0]


def menu_click_outside(mouse_x, mouse_y):
    """True if a click falls outside the open theme menu."""
    if not _menu_open[0]:
        return False
    x, y = dpg.get_item_pos("theme_menu")
    return not (x <= mouse_x <= x + MENU_W and y <= mouse_y <= y + MENU_H)


def _pick_theme(sender, app_data, name):
    hide_menu()
    if _set_theme[0]:
        _set_theme[0](name)


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
    """Ease every card toward its hover state. Called once per frame."""
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
