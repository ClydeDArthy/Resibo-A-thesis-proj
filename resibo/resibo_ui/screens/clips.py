"""Clips received: segments carved from the source footage, each hashed on arrival."""

import dearpygui.dearpygui as dpg
from .. import actions, data, db, layout, player, state, theme as th, uploads, video, widgets as w

TITLE = "Clips"
CRUMB = ("CASE-2026-09A", "Clips received")
ACTION = None


def build():
    with dpg.group(horizontal=True):
        _clip_list()
        _preview()


def _pick(sender, app_data, index):
    """Open a different segment in the preview."""
    state.SEL["clip"] = index
    state.rebuild("cl_list", _fill_list)
    state.rebuild("cl_main", _fill_main)


def refresh():
    """Redraw after the open case changes."""
    state.SEL["clip"] = 0
    state.rebuild("cl_list", _fill_list)
    state.rebuild("cl_main", _fill_main)


def _clip_list():
    """Left rail: every segment with its verification state."""
    with dpg.child_window(width=350, border=True) as panel:
        layout.register(panel, "left")
        w.title("Clips")
        w.mono(data.CLIPS_SUMMARY, "faint", small=True)
        w.spacer(6)
        dpg.add_separator()
        w.spacer(10)
        with dpg.child_window(tag="cl_list", border=False, width=-1, no_scrollbar=True, no_scroll_with_mouse=True):
            _fill_list()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_list():
    for i, clip in enumerate(data.CLIPS):
        selected = (i == state.SEL["clip"])
        # The clip on screen says so; the rest keep their verified badge.
        badge = "Viewing" if selected else clip["badge"]
        tone = "blue" if selected else clip["tone"]
        item = w.list_item(clip["id"], clip["event"], badge, tone, selected=selected)
        state.on_click(item, _pick, i)
        w.spacer(2)


def _preview():
    """Centre column: the selected clip plus the hash table for all clips."""
    with dpg.child_window(width=-1, border=True) as pane:
        layout.on_resize(lambda: state.rebuild("cl_main", _fill_main))
        with dpg.group(tag="cl_main"):
            _fill_main()
    dpg.bind_item_theme(pane, th.T["pane"])


def _sealed_video_path(case_number):
    """The first real video file sealed for this case, if any."""
    for row in db.evidence_for(case_number):
        if uploads.is_video(row["path"]):
            return row["path"]
    return None


def _fill_main():
    index = state.SEL["clip"]
    clip = data.CLIPS[index]
    case_number = data.CASES[state.SEL["case"]]["number"]

    w.title("Clips received", "h1")
    w.spacer(8)
    dpg.add_separator()
    w.spacer(14)

    w.text(clip["id"] + " preview", "text", "ui")
    w.spacer(8)
    with dpg.child_window(height=18 + 26 + 6 + 210 + 8 + 30, border=True,
                          no_scrollbar=True, no_scroll_with_mouse=True) as box:
        with dpg.table_row(parent=w.split_row(90)):
            w.mono("CAM04 . " + clip["id"], "dim")
            w.mono("clean copy", "faint", small=True)
        w.spacer(6)
        # No detections are drawn yet at this stage of the workflow. Show the
        # real sealed video if this case actually has one, otherwise the
        # illustrated placeholder.
        art = layout.content_width(has_right=False)
        path = _sealed_video_path(case_number)
        dl = path and video.draw(art, 210, path, at_fraction=0.36, play_badge=True)
        if not dl:
            w.video_frame(art, 210, "", "")
        else:
            state.on_click(dl, lambda s, a, u: actions.open_external(path))
        w.spacer(8)
        player.bar(clip["at"], clip["total"], progress=0.36, width=art)
    dpg.bind_item_theme(box, th.T["card"])

    w.spacer(16)
    rows = [(c["id"], c["span"], c["length"], (c["hash"], "dim"), ("", "green", True))
            for c in data.CLIPS]
    w.table(["Clip", "Time in the original", "Length", "Hash", ""],
            rows, weights=[1, 1.4, 0.8, 1.6, 0.2], highlight=index)

