"""A full-viewport dark backdrop shown behind modal confirmation dialogs.

DearPyGui's own modal dimming isn't reliable with the frameless windows this
app uses, so the dialogs that need it (delete case, remove attachment) call
`show()`/`hide()` themselves around their own show/hide.
"""

import dearpygui.dearpygui as dpg


def build():
    """Create the backdrop once, hidden."""
    with dpg.window(tag="scrim", show=False, no_title_bar=True, no_resize=True,
                    no_move=True, no_collapse=True, no_scrollbar=True,
                    no_scroll_with_mouse=True, no_background=True,
                    no_bring_to_front_on_focus=True):
        dpg.add_drawlist(tag="scrim_art", width=10, height=10)


def show():
    try:
        width = dpg.get_viewport_client_width()
        height = dpg.get_viewport_client_height()
    except Exception:
        width, height = 1500, 940
    dpg.configure_item("scrim", show=True, pos=(0, 0), width=width, height=height)
    dpg.configure_item("scrim_art", width=width, height=height)
    dpg.delete_item("scrim_art", children_only=True)
    dpg.push_container_stack("scrim_art")
    dpg.draw_rectangle((0, 0), (width, height), fill=(0, 0, 0, 150), color=(0, 0, 0, 0))
    dpg.pop_container_stack()


def hide():
    dpg.configure_item("scrim", show=False)
