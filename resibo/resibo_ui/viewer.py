"""Full-size preview for one saved image.

Opens over the app; closes on the X, on Escape, or on a click outside it.
"""

import dearpygui.dearpygui as dpg
from . import theme as th, widgets as w

WIN_W, WIN_H = 620, 780
_open = [False]


def build():
    """Create the preview window once, hidden."""
    with dpg.window(tag="viewer", show=False, no_title_bar=True, no_resize=True,
                    no_move=True, no_collapse=True, no_scrollbar=True,
                    width=WIN_W, height=WIN_H) as win:
        with dpg.table_row(parent=w.split_row(0)):
            with dpg.group():
                w.font(dpg.add_text("", tag="viewer_title"), "h2")
                sub = dpg.add_text("", tag="viewer_sub")
                dpg.bind_item_theme(sub, th.T["txt_dim"])
                w.font(sub, "mono_sm")
            close = dpg.add_button(label="X", width=36, height=30, callback=hide)
            dpg.bind_item_theme(close, th.T["btn_ghost"])
        w.spacer(10)
        dpg.add_drawlist(tag="viewer_art", width=WIN_W - 40, height=WIN_H - 460)
        w.spacer(10)
        with dpg.group(tag="viewer_meta"):
            pass
    dpg.bind_item_theme(win, th.T["panel"])


def show(title, sub, look, enhanced, meta):
    """Open the preview for one image."""
    dpg.set_value("viewer_title", title)
    dpg.set_value("viewer_sub", sub)
    _draw(look, enhanced)

    dpg.delete_item("viewer_meta", children_only=True)
    dpg.push_container_stack("viewer_meta")
    for key, value, tone in meta:
        w.kv_row(key, value, tone, width=WIN_W - 60)
    dpg.pop_container_stack()

    width, height = _viewport()
    dpg.configure_item("viewer", show=True,
                       pos=((width - WIN_W) // 2, max(20, (height - WIN_H) // 2)))
    dpg.focus_item("viewer")
    _open[0] = True


def hide(sender=None, app_data=None, user_data=None):
    dpg.configure_item("viewer", show=False)
    _open[0] = False


def is_open():
    return _open[0]


def _viewport():
    try:
        return dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
    except Exception:
        return 1500, 940


def _draw(look, enhanced):
    """Paint the crop large, sharp when enhanced and soft when raw."""
    width = WIN_W - 40
    height = WIN_H - 460
    dpg.delete_item("viewer_art", children_only=True)
    dpg.push_container_stack("viewer_art")

    fade = 1.0 if enhanced else 0.70
    skin = tuple(int(c * fade) for c in look["skin"])
    hair = tuple(int(c * fade) for c in look["hair"])
    shirt = tuple(int(c * fade) for c in look["shirt"])

    dpg.draw_rectangle((0, 0), (width, height), fill=(18, 22, 26), color=th.BORDER)
    cx, cy = width / 2, height * 0.46
    head_r = height * 0.24 * look["build"]

    dpg.draw_ellipse((cx - head_r * 1.9, cy + head_r * 0.9),
                     (cx + head_r * 1.9, height), fill=shirt, color=shirt)
    dpg.draw_circle((cx, cy), head_r, fill=skin, color=skin)
    if look["hair_style"] == "long":
        dpg.draw_ellipse((cx - head_r, cy - head_r),
                         (cx + head_r, cy + head_r * 1.35), fill=hair, color=hair)
        dpg.draw_circle((cx, cy + head_r * 0.12), head_r * 0.80, fill=skin, color=skin)
    elif look["hair_style"] == "cap":
        dpg.draw_ellipse((cx - head_r * 1.08, cy - head_r * 1.1),
                         (cx + head_r * 1.08, cy + head_r * 0.05), fill=hair, color=hair)
    else:
        dpg.draw_circle((cx, cy - head_r * 0.28), head_r * 0.92, fill=hair, color=hair)

    if enhanced:                       # the enhanced copy resolves the eyes
        for dx in (-head_r * 0.38, head_r * 0.38):
            dpg.draw_circle((cx + dx, cy + head_r * 0.05), head_r * 0.13,
                            fill=(238, 240, 242), color=(238, 240, 242))
            dpg.draw_circle((cx + dx, cy + head_r * 0.05), head_r * 0.06,
                            fill=(20, 22, 26), color=(20, 22, 26))
    dpg.draw_text((14, height - 26), "enhanced" if enhanced else "raw",
                  size=14, color=th.GREEN if enhanced else th.TEXT_FAINT)
    dpg.pop_container_stack()


def click_outside(mouse_x, mouse_y):
    """True if a click at this point falls outside the open preview."""
    if not _open[0]:
        return False
    x, y = dpg.get_item_pos("viewer")
    return not (x <= mouse_x <= x + WIN_W and y <= mouse_y <= y + WIN_H)
