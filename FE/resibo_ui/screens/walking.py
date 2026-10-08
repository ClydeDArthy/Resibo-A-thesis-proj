"""Live gait analysis screen.

The screen follows the same master_id/frame state produced by OBJ and Gait.
Reference gait tables are never displayed as if they were current model output.
"""
import dearpygui.dearpygui as dpg
from .. import layout, live, state, theme as th, widgets as w

TITLE = "Walking"
CRUMB = ("CASE-2026-09A", "Walking")
ACTION = None


def build():
    with dpg.group(horizontal=True):
        _results()
        _analysis()
        _detail()


def refresh_live():
    if dpg.does_item_exist("wk_list"):
        state.rebuild("wk_list", _fill_list)
    if dpg.does_item_exist("wk_main"):
        state.rebuild("wk_main", _fill_main)
    if dpg.does_item_exist("wk_detail"):
        state.rebuild("wk_detail", _fill_detail)


def _results():
    with dpg.child_window(width=300, border=True) as panel:
        layout.register(panel, "left")
        w.title("Live gait results")
        w.mono("one row per tracked master_id", "faint", small=True)
        w.spacer(6)
        dpg.add_separator()
        w.spacer(10)
        with dpg.child_window(tag="wk_list", border=False, width=-1,
                              no_scrollbar=True, no_scroll_with_mouse=True):
            _fill_list()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_list():
    tracks = live.tracks()
    if not tracks:
        w.note(
            "Waiting",
            "No tracked person has produced a gait result yet.",
            "amber",
            wrap=250,
        )
        return
    for i, track in enumerate(tracks):
        gait = track.get("gait") or {}
        status = gait.get("status", "waiting")
        tone = "green" if status == "inferred" else "amber"
        item = w.list_item(
            "master_id {}".format(track["master_id"]),
            "{} frames".format(gait.get("frame_count", 0)),
            status,
            tone,
            selected=(i == state.SEL["walk"]),
        )
        state.on_click(item, _pick, i)
        w.spacer(2)


def _pick(sender, app_data, index):
    state.SEL["walk"] = index
    state.rebuild("wk_list", _fill_list)
    state.rebuild("wk_main", _fill_main)
    state.rebuild("wk_detail", _fill_detail)


def _analysis():
    with dpg.child_window(width=-390, border=True) as pane:
        layout.register(pane, "centre")
        layout.on_resize(lambda: state.rebuild("wk_main", _fill_main))
        with dpg.group(tag="wk_main"):
            _fill_main()
    dpg.bind_item_theme(pane, th.T["pane"])


def _fill_main():
    tracks = live.tracks()
    status = live.pipeline_status().get("gait", "idle")
    with dpg.table_row(parent=w.header_row(130)):
        with dpg.group():
            w.title("Walking analysis", "h1")
            w.mono("GaitBase sequence state for the current OBJ tracks.", "dim")
        w.pill(status, "green" if status in ("ready", "completed") else "amber")
    w.spacer(12)
    dpg.add_separator()
    w.spacer(14)

    rows = []
    for track in tracks:
        gait = track.get("gait") or {}
        resolution = track.get("resolution")
        rows.append((
            "master_id {}".format(track["master_id"]),
            gait.get("frame_count", 0),
            gait.get("status", "waiting"),
            "yes" if gait.get("embedding_ready") else "no",
            getattr(resolution, "state", "-") if resolution else "-",
            getattr(resolution, "candidate_id", "-") if resolution else "-",
        ))
    if rows:
        w.table(
            ["Track", "Frames", "Gait state", "Embedding", "RESIBO", "Candidate"],
            rows,
            weights=[1.2, .8, 1.3, 1, 1, 1.4],
        )
    else:
        w.note(
            "No live gait output",
            "Gait analysis begins from the person crops emitted by YOLO11 + BoT-SORT.",
            "amber",
            wrap=layout.content_width(has_right=True),
        )

    w.spacer(18)
    w.section("Recognition handoff", "gait output is only passed to RESIBO after GaitBase inference")
    if not rows:
        w.mono("Waiting for a tracked sequence.", "faint", small=True)
    else:
        for track in tracks:
            gait = track.get("gait") or {}
            if gait.get("embedding_ready"):
                w.mono(
                    "master_id {} · GaitBase embedding ready · {} frames".format(
                        track["master_id"], gait.get("frame_count", 0)
                    ),
                    "green",
                    small=True,
                )
            else:
                w.mono(
                    "master_id {} · {}".format(
                        track["master_id"], gait.get("status", "waiting")
                    ),
                    "amber",
                    small=True,
                )


def _detail():
    with dpg.child_window(width=-1, border=True) as panel:
        layout.register(panel, "right")
        with dpg.group(tag="wk_detail"):
            _fill_detail()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_detail():
    tracks = live.tracks()
    if not tracks:
        w.title("No live track")
        return
    index = min(max(state.SEL["walk"], 0), len(tracks) - 1)
    track = tracks[index]
    gait = track.get("gait") or {}
    resolution = track.get("resolution")

    w.title("master_id {}".format(track["master_id"]))
    w.mono("frame {}".format(track.get("frame_index", "-")), "faint", small=True)
    w.spacer(8)
    w.kv_row("Gait state", gait.get("status", "waiting"),
             "green" if gait.get("status") == "inferred" else "amber")
    w.kv_row("Frames", gait.get("frame_count", 0), "text")
    w.kv_row("Embedding", "ready" if gait.get("embedding_ready") else "not ready",
             "green" if gait.get("embedding_ready") else "amber")
    if resolution is not None:
        w.kv_row("RESIBO", resolution.state,
                 "green" if resolution.state == "resolved" else "amber")
        w.kv_row("Candidate", resolution.candidate_id or "-", "text")
        w.kv_row("Fused score", resolution.fused_score if resolution.fused_score is not None else "-", "text")
