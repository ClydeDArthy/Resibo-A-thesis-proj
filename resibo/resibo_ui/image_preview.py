"""In-app image preview: shows a real uploaded still at full size.

Opens over the app, like `viewer.py`. Closes on the X or on a click outside it.
"""

import os
import dearpygui.dearpygui as dpg
from . import theme as th, widgets as w

WIN_W, WIN_H = 720, 640
ART_W, ART_H = WIN_W - 40, WIN_H - 100
_open = [False]


def build():
    """Create the preview window once, hidden."""
    with dpg.window(tag="image_preview", show=False, no_title_bar=True, no_resize=True,
                    no_move=True, no_collapse=True, no_scrollbar=True,
                    width=WIN_W, height=WIN_H) as win:
        with dpg.table_row(parent=w.split_row(0)):
            w.font(dpg.add_text("", tag="imgprev_title"), "h2")
            close = dpg.add_button(label="X", width=36, height=30, callback=hide)
            dpg.bind_item_theme(close, th.T["btn_ghost"])
        w.spacer(10)
        dpg.add_drawlist(tag="imgprev_art", width=ART_W, height=ART_H)
    dpg.bind_item_theme(win, th.T["panel"])


def show(path):
    """Open the preview for one real image file."""
    if not path or not os.path.isfile(path):
        return
    dpg.set_value("imgprev_title", os.path.basename(path))
    dpg.delete_item("imgprev_art", children_only=True)

    found = w.image_texture(path)
    if found:
        tag, iw, ih = found
        scale = min(ART_W / iw, ART_H / ih)
        draw_w, draw_h = iw * scale, ih * scale
        left, top = (ART_W - draw_w) / 2, (ART_H - draw_h) / 2
        dpg.push_container_stack("imgprev_art")
        dpg.draw_image(tag, (left, top), (left + draw_w, top + draw_h))
        dpg.pop_container_stack()

    width, height = _viewport()
    dpg.configure_item("image_preview", show=True,
                       pos=((width - WIN_W) // 2, max(20, (height - WIN_H) // 2)))
    dpg.focus_item("image_preview")
    _open[0] = True


def hide(sender=None, app_data=None, user_data=None):
    dpg.configure_item("image_preview", show=False)
    _open[0] = False


def is_open():
    return _open[0]


def click_outside(mouse_x, mouse_y):
    if not _open[0]:
        return False
    x, y = dpg.get_item_pos("image_preview")
    return not (x <= mouse_x <= x + WIN_W and y <= mouse_y <= y + WIN_H)


def _viewport():
    try:
        return dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
    except Exception:
        return 1500, 940
