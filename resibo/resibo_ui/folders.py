"""A small window showing what one identity folder holds.

Behaves like a file window: opens on a folder, lists its crops, and closes on
the X or a click outside. Double-clicking a crop opens the full-size preview.
"""

import dearpygui.dearpygui as dpg
from . import data, state, theme as th, viewer, widgets as w, widgets_plot as wp

WIN_W, WIN_H = 760, 560
PER_ROW = 3
TILE_H = 186

_open = [False]


def build():
    """Create the folder window once, hidden."""
    with dpg.window(tag="folder_win", show=False, no_title_bar=True, no_resize=True,
                    no_move=True, no_collapse=True, no_scrollbar=True,
                    width=WIN_W, height=WIN_H) as win:
        with dpg.table_row(parent=w.split_row(0)):
            with dpg.group():
                w.font(dpg.add_text("", tag="folder_title"), "h2")
                sub = dpg.add_text("", tag="folder_sub")
                dpg.bind_item_theme(sub, th.T["txt_dim"])
                w.font(sub, "mono_sm")
            close = dpg.add_button(label="X", width=36, height=30, callback=hide)
            dpg.bind_item_theme(close, th.T["btn_ghost"])
        w.spacer(6)
        dpg.add_separator()
        w.spacer(12)
        with dpg.group(tag="folder_grid"):
            pass
    dpg.bind_item_theme(win, th.T["panel"])


def show(ident, kind, person):
    """Open the window on one identity folder.

    A face folder lists its crops; a gait folder reports the walk instead.
    """
    dpg.set_value("folder_title", ident)
    dpg.delete_item("folder_grid", children_only=True)
    dpg.push_container_stack("folder_grid")
    if kind == "gait":
        dpg.set_value("folder_sub", "walk pattern . " + str(len(data.gait_metrics(person)))
                      + " measurements")
        _fill_gait(person)
    else:
        dpg.set_value("folder_sub", "face crops . {} items . double click to open"
                      .format(len(data.FOLDER_ITEMS)))
        _fill_crops(ident, person)
    dpg.pop_container_stack()

    width, height = _viewport()
    dpg.configure_item("folder_win", show=True,
                       pos=((width - WIN_W) // 2, max(20, (height - WIN_H) // 2)))
    dpg.focus_item("folder_win")
    _open[0] = True


def _fill_crops(ident, person):
    """The raw and enhanced crops saved for this identity."""
    look = data.look(person)
    tile = w.share(WIN_W - 56, PER_ROW)
    for start in range(0, len(data.FOLDER_ITEMS), PER_ROW):
        with dpg.group(horizontal=True):
            for frame, enhanced in data.FOLDER_ITEMS[start:start + PER_ROW]:
                item = w.face_tile("enhanced" if enhanced else "raw",
                                   "frame " + frame, width=tile, height=TILE_H,
                                   blurred=not enhanced, look=look, centered=True)
                state.on_double_click(item, _preview,
                                      (ident, frame, enhanced, person))
        w.spacer(10)


def _fill_gait(person):
    """Gait output for this identity: the measurements and the ankle chart."""
    w.text("Gait output - movement", "text", "ui", wrap=-1)
    w.spacer(10)
    metrics = data.gait_metrics(person)
    box_w = w.share(WIN_W - 56, len(metrics))
    with dpg.group(horizontal=True):
        for label, value, sub, tone in metrics:
            w.stat_box(label, value, tone, sub, width=box_w)
    w.spacer(14)
    wp.gait_chart_frame()


def _preview(sender, app_data, user_data):
    ident, frame, enhanced, person = user_data
    viewer.show(ident, "frame " + frame, data.look(person), enhanced,
                data.folder_meta(ident, frame, enhanced))


def hide(sender=None, app_data=None, user_data=None):
    dpg.configure_item("folder_win", show=False)
    _open[0] = False


def is_open():
    return _open[0]


def _viewport():
    try:
        return dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
    except Exception:
        return 1500, 940


def click_outside(mouse_x, mouse_y):
    """True if a click at this point falls outside the open folder window."""
    if not _open[0]:
        return False
    x, y = dpg.get_item_pos("folder_win")
    return not (x <= mouse_x <= x + WIN_W and y <= mouse_y <= y + WIN_H)
