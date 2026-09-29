"""Person detection: YOLO11 detection, tracking and the saved identity folders.

Each identity keeps a folder of raw and enhanced crops. Double-clicking a crop
opens it full size.
"""

import dearpygui.dearpygui as dpg
from .. import data, folders, layout, player, state, theme as th, widgets as w

TITLE = "Person detection"
CRUMB = ("CASE-2026-09A", "Detection")
ACTION = None

# Person boxes as fractions of the frame: x, y, width, height, label, tone.
BOXES = [
    (0.16, 0.26, 0.13, 0.60, "ID 1234", "green"),
    (0.42, 0.18, 0.16, 0.70, "ID 4321", "green"),
    (0.70, 0.34, 0.10, 0.50, "ID 0617", "amber"),
]

FRAME_H = 300


def build():
    with dpg.group(horizontal=True):
        _steps()
        _main()


def _steps():
    """Left rail: the detection pipeline."""
    with dpg.child_window(width=350, border=True) as panel:
        layout.register(panel, "left")
        w.title("Progress")
        w.spacer(4)
        dpg.add_separator()
        w.spacer(10)
        with dpg.child_window(tag="pp_steps", border=False, width=-1,
                              no_scrollbar=True, no_scroll_with_mouse=True):
            _fill_steps()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_steps():
    for name, model, badge, tone, prog in data.PEOPLE_STEPS:
        w.step_card(name, model, badge, tone, progress=prog)
        w.spacer(4)


def _main():
    """Centre column: the annotated frame and the saved folders."""
    with dpg.child_window(width=-1, border=True) as pane:
        layout.on_resize(lambda: state.rebuild("pp_main", _fill_main))
        with dpg.group(tag="pp_main"):
            _fill_main()
    dpg.bind_item_theme(pane, th.T["pane"])


def _fill_main():
    art = layout.content_width(has_right=False)
    with dpg.child_window(height=18 + FRAME_H + 10 + 30, border=True,
                          no_scrollbar=True, no_scroll_with_mouse=True) as box:
        w.video_frame(art, FRAME_H, "CAM04 . SEG-02", "2026-08-14 03:16:28",
                      boxes=BOXES, looks=_box_looks())
        w.spacer(10)
        player.bar("00:01:50", "00:04:23", progress=0.42,
                   marks=(0.22, 0.62, 0.68), width=art)
    dpg.bind_item_theme(box, th.T["card"])

    w.spacer(18)
    w.title("People found")
    w.spacer(10)

    # Two folder groups side by side, as in the approved layout.
    half = w.share(art, 2, gap=18)
    with dpg.group(horizontal=True):
        _folder_group("Saved Faces", "faces", half)
        dpg.add_spacer(width=18)
        _folder_group("Saved Gait", "gait", half)

    w.spacer(16)


def _box_looks():
    """Map the identity labels on the frame to their appearance."""
    return {ident: data.look(person) for ident, _tone, person in data.IDENTITIES}


def _folder_group(title, kind, width):
    """One bordered group of identity folders."""
    with dpg.child_window(width=width, auto_resize_y=True, border=True,
                          no_scrollbar=True, no_scroll_with_mouse=True) as box:
        w.text(title, "text", "ui", wrap=-1)
        w.spacer(8)

        def draw(i):
            ident, tone, _person = data.IDENTITIES[i]
            tile = w.folder_tile(ident, "clean + annotated", tone)
            state.on_click(tile, _open_folder, (kind, i))

        w.tile_grid(len(data.IDENTITIES), 2, draw)
    dpg.bind_item_theme(box, th.T["card_flat"])


def _open_folder(sender, app_data, user_data):
    """Open a folder in its own small window."""
    kind, index = user_data
    ident, _tone, person = data.IDENTITIES[index]
    folders.show(ident, kind, person)
