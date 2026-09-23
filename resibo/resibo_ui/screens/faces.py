"""Face enhancement: bounding box, landmarks, standard crop and enhancement.

Each stage keeps its own picture, so the chain from the raw detection to the
enhanced crop stays visible.
"""

import dearpygui.dearpygui as dpg
from .. import data, layout, state, theme as th, widgets as w

TITLE = "Face enhancement"
CRUMB = ("CASE-2026-09A", "Face enhancement")
ACTION = None

PER_ROW = 3
TILE_H = 210


def build():
    with dpg.group(horizontal=True):
        _steps()
        _tiles()
        _persons()


def _pick_person(sender, app_data, index):
    """Switch the crops shown to another saved identity."""
    state.SEL["face_person"] = index
    state.rebuild("fc_tiles", _fill_tiles)
    state.rebuild("fc_persons", _fill_persons)


def _steps():
    """Left rail: the four stages of the face pipeline."""
    with dpg.child_window(width=350, border=True) as panel:
        layout.register(panel, "left")
        w.title("Steps")
        w.spacer(4)
        dpg.add_separator()
        w.spacer(10)
        # The step list never scrolls; it holds a fixed four cards.
        with dpg.child_window(tag="fc_list", border=False, width=-1,
                              no_scrollbar=True, no_scroll_with_mouse=True):
            _fill_steps()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_steps():
    for name, model, badge, tone, prog in data.FACE_STEPS:
        w.step_card(name, model, badge, tone, progress=prog)
        w.spacer(4)


def _tiles():
    """Centre column: one picture per stage."""
    with dpg.child_window(width=-450, border=True) as pane:
        layout.register(pane, "centre")
        layout.on_resize(lambda: state.rebuild("fc_tiles", _fill_tiles))
        w.title("Face enhancement", "h1")
        w.spacer(8)
        dpg.add_separator()
        w.spacer(14)
        with dpg.group(tag="fc_tiles"):
            _fill_tiles()
    dpg.bind_item_theme(pane, th.T["pane"])


def _fill_tiles():
    identity, _sub, _tone, person = data.FACE_PERSONS[state.SEL["face_person"]]
    frame = data.FACE_FRAMES[state.SEL["face_person"]]

    w.text("{} . frame {}".format(identity, frame), "text", "ui", wrap=-1)
    w.spacer(10)

    tile_w = w.share(layout.content_width(has_right=True), PER_ROW)
    for i in range(0, len(data.FACE_TILES), PER_ROW):
        with dpg.group(horizontal=True):
            for caption, sub, blurred, bbox, landmarks in data.FACE_TILES[i:i + PER_ROW]:
                w.face_tile(caption, sub, width=tile_w, height=TILE_H,
                            blurred=blurred, bbox=bbox, landmarks=landmarks,
                            look=data.look(person), centered=True)
        w.spacer(10)



def _persons():
    """Right rail: the saved identity folders the crops came from."""
    with dpg.child_window(width=-1, border=True) as panel:
        layout.register(panel, "right")
        w.title("Saved Persons")
        w.mono("one person each box", "faint", small=True)
        w.spacer(6)
        dpg.add_separator()
        w.spacer(10)
        with dpg.group(tag="fc_persons"):
            _fill_persons()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_persons():
    def draw(i):
        identity, sub, tone, _person = data.FACE_PERSONS[i]
        tile = w.folder_tile(identity, sub, tone,
                             selected=(i == state.SEL["face_person"]))
        state.on_click(tile, _pick_person, i)

    w.tile_grid(len(data.FACE_PERSONS), 2, draw)
