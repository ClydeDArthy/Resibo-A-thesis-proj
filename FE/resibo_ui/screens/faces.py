"""Face enhancement: bounding box, landmarks, standard crop and enhancement.

Each stage keeps its own picture, so the chain from the raw detection to the
enhanced crop stays visible.
"""

import dearpygui.dearpygui as dpg
from .. import data, layout, live, state, theme as th, widgets as w

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
    """Show the current face stage from the live model runtime."""
    snapshot = live.snapshot()
    status = snapshot["pipelines"]["face"]
    w.text("Live face processing", "text", "ui", wrap=-1)
    w.mono("Detector / FR status: " + str(status), "green" if status in ("ready", "completed") else "amber", small=True)
    w.spacer(10)
    rows = []
    for track in snapshot["tracks"]:
        face = track.get("face") or {}
        cosine = face.get("score")
        rows.append((
            "master_id {}".format(track["master_id"]),
            track.get("frame_index", "-"),
            face.get("faces", 0),
            face.get("detector", "waiting"),
            face.get("candidate") or "not available",
            "{:.4f}".format(cosine) if cosine is not None else "-",
        ))
    if rows:
        w.table(
            ["Track", "Frame", "Faces", "Detector", "Top candidate", "Cosine"],
            rows,
            weights=[1.2, .8, .7, 1, 1.4, .9],
        )
    else:
        w.note(
            "Waiting for live face output",
            "No face result has been produced for the current tracked video. "
            "The previous reference-data face tiles are intentionally not shown.",
            "amber",
            wrap=layout.content_width(has_right=True),
        )

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
    """List live tracks instead of seeded identity folders."""
    tracks = live.tracks()
    if not tracks:
        w.note(
            "No live tracks",
            "Open a case with an accessible video and run the detection stage first.",
            "amber",
            wrap=layout.widths()[2] - 40,
        )
        return
    for track in tracks:
        face = track.get("face") or {}
        badge = face.get("candidate") or "No match"
        tone = "green" if face.get("candidate") else "amber"
        item = w.list_item(
            "master_id {}".format(track["master_id"]),
            "frame {}".format(track.get("frame_index", "-")),
            badge,
            tone,
        )
        state.on_click(item, _pick_person, track["master_id"])
        w.spacer(3)
