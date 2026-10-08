"""Case progress: every workflow step as a button that opens its stage.

Clicking a step expands its flags in place; the Open button jumps to the
screen that produced them.
"""

import dearpygui.dearpygui as dpg
from .. import data, state, theme as th, widgets as w

TITLE = "Progress"
CRUMB = ("CASE-2026-09A", "Progress")
ACTION = None

# app.run() supplies this so a step can switch screens by name.
_open_screen = [None]
_expanded = {"step": None}


def set_opener(fn):
    _open_screen[0] = fn


def build():
    with dpg.group(horizontal=True):
        _steps()
        _details()


def refresh_live():
    if dpg.does_item_exist("pg_steps"):
        state.rebuild("pg_steps", _fill_steps)


def _toggle(sender, app_data, index):
    """Open one step's flags, closing whichever was open."""
    _expanded["step"] = None if _expanded["step"] == index else index
    state.rebuild("pg_steps", _fill_steps)


def _open(sender, app_data, screen):
    if _open_screen[0]:
        _open_screen[0](screen)


def _steps():
    """Centre column: the case header and the eight workflow steps."""
    with dpg.child_window(width=-360, border=True) as pane:
        with dpg.group(tag="pg_steps"):
            _fill_steps()
    dpg.bind_item_theme(pane, th.T["pane"])


def _fill_steps():
    case = data.CASES[state.SEL["case"]]
    total_flags = sum(len(s["flags"]) for i, s in enumerate(data.STEPS)
                      if i < case["done"])

    with dpg.table_row(parent=w.header_row(200)):
        with dpg.group():
            w.title(case["name"], "h1")
            w.mono(case["number"] + "  .  " + case["place"], "dim")
        with dpg.group(horizontal=True):
            with dpg.group():
                w.text("Flags", "dim", "ui_sm")
                w.text(str(total_flags), "amber" if total_flags else "green", "h2")
            dpg.add_spacer(width=30)
            with dpg.group():
                w.text("Chain", "dim", "ui_sm")
                w.text(case["chain"], "green", "mono")

    w.spacer(10)
    dpg.add_separator()
    w.spacer(14)
    w.section("Progress", "click a step to see its flags")

    for i, step in enumerate(data.STEPS):
        badge, tone = data.step_state(i, case)
        _step_card(i, step, badge, tone, case)
        w.spacer(4)


def _step_card(index, step, badge, tone, case):
    """One step: number, label, status pill, and its flags when expanded."""
    started = index <= case["done"]
    open_now = _expanded["step"] == index
    flags = step["flags"] if index < case["done"] else []

    with dpg.child_window(auto_resize_y=True, border=True, no_scrollbar=True,
                          no_scroll_with_mouse=True) as card:
        with dpg.group() as header:
            with dpg.table_row(parent=w.header_row(w.pill_width(badge))):
                with dpg.group(horizontal=True):
                    with dpg.drawlist(width=36, height=38):
                        col = th.GREEN if tone == "green" else th.AMBER if tone == "amber" \
                            else th.BLUE if tone == "blue" else th.TEXT_FAINT
                        dpg.draw_circle((17, 19), 13, color=col, thickness=1.2)
                        dpg.draw_text((13, 11), str(index + 1), size=14, color=col)
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            w.text("v" if open_now else ">", "green" if open_now else "faint",
                                   "mono", wrap=-1)
                            w.text(step["label"], "text" if started else "dim", "ui", wrap=-1)
                        w.text(step["note"], "faint", "mono_sm", wrap=-1)
                with dpg.group():
                    w.spacer(4)
                    w.pill(badge, tone)

        if open_now:
            w.spacer(6)
            dpg.add_separator()
            w.spacer(6)
            if flags:
                for message, flag_tone in flags:
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=36)
                        w.dot(flag_tone)
                        w.text(message, flag_tone if flag_tone != "gray" else "dim",
                               "ui_sm", wrap=-1)
            else:
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=36)
                    w.text("No flags raised at this step." if started
                           else "This step has not run yet.", "faint", "ui_sm", wrap=-1)
            w.spacer(8)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=36)
                btn = dpg.add_button(label="Open " + step["screen"] + "  >",
                                     callback=_open, user_data=step["screen"])
                dpg.bind_item_theme(btn, th.T["btn_primary"] if started else th.T["btn_ghost"])

    dpg.bind_item_theme(card, th.T["card_sel"] if open_now else th.T["card"])
    # Only the header toggles the card - the whole card would also swallow
    # clicks meant for the "Open ... >" button nested below it.
    state.on_click(header, _toggle, index)


def _details():
    """Right rail: who is working the case and the case identifiers."""
    with dpg.child_window(width=-1, border=True) as panel:
        with dpg.group(tag="pg_details"):
            _fill_details()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_details():
    case = data.CASES[state.SEL["case"]]
    w.title("Case details")
    w.spacer(4)
    dpg.add_separator()
    w.spacer(10)

    w.text("Examiner", "text", "ui")
    w.spacer(6)
    w.kv_row("Name", case.get("examiner", "-"))
    w.kv_row("Status", case["status"], "blue")

    w.spacer(12)
    w.text("Case", "text", "ui")
    w.spacer(6)
    w.kv_row("Number", case["number"])
    w.kv_row("Opened", case["opened"])
    w.kv_row("Exhibits", case["exhibits"])
    w.kv_row("Chain", case["chain"], "green")


def refresh():
    """Redraw after the open case changes."""
    _expanded["step"] = None
    state.rebuild("pg_steps", _fill_steps)
    state.rebuild("pg_details", _fill_details)