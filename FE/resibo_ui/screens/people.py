"""Person detection: YOLO11 detection, tracking and the saved identity folders.

Each identity keeps a folder of raw and enhanced crops. Double-clicking a crop
opens it full size.
"""

import dearpygui.dearpygui as dpg
from .. import data, folders, layout, live, obj_bridge, player, state, theme as th, widgets as w

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
_backend_key = None
_last_render_frame = -999999


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
    snapshot = live.snapshot()
    for label, key in (
        ("YOLO11 detection", "obj"),
        ("BoT-SORT tracking", "obj"),
        ("Face handoff", "face"),
        ("Gait handoff", "gait"),
    ):
        status = snapshot["pipelines"].get(key, "idle")
        tone = "green" if status in ("ready", "running", "completed") else "amber"
        w.step_card(label, "live runtime", str(status), tone, progress=1.0 if status == "completed" else 0.0)
        w.spacer(4)


def refresh_backend():
    """Refresh the People panel only when OBJ state actually changes."""
    global _backend_key, _last_render_frame
    status = obj_bridge.status()
    observation = obj_bridge.latest_observation()
    count = len(observation.people) if observation is not None else 0
    frame_index = observation.frame_index if observation is not None else -1
    if status["status"] == "running" and frame_index - _last_render_frame < 15:
        return
    key = (status["status"], frame_index, count)
    if key == _backend_key:
        return
    _backend_key = key
    _last_render_frame = frame_index
    if dpg.does_item_exist("pp_main"):
        state.rebuild("pp_main", _fill_main)
    if dpg.does_item_exist("pp_steps"):
        state.rebuild("pp_steps", _fill_steps)


def _backend_boxes():
    """Convert the latest real tracked boxes into the FE drawing format."""
    observation = obj_bridge.latest_observation()
    if observation is None or not observation.people:
        return BOXES

    height, width = observation.frame.shape[:2]
    if width <= 0 or height <= 0:
        return BOXES

    return [
        (
            p.person_box[0] / width,
            p.person_box[1] / height,
            (p.person_box[2] - p.person_box[0]) / width,
            (p.person_box[3] - p.person_box[1]) / height,
            "master_id {}".format(p.master_id),
            "green" if p.confidence >= 0.50 else "amber",
        )
        for p in observation.people
    ]


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
        observation = obj_bridge.latest_observation()
        if observation is not None:
            w.live_video_frame(
                observation.frame, art, FRAME_H, "LIVE . YOLO11 + BoT-SORT",
                "frame {:06d} . {:.3f}s".format(
                    observation.frame_index, observation.timestamp_ms / 1000.0
                ),
                boxes=_backend_boxes(),
            )
        else:
            w.video_frame(art, FRAME_H, "LIVE . waiting", "no frame yet", boxes=[])
        w.spacer(10)
        status = obj_bridge.status()
        w.mono(
            "Backend: {} . {} tracks".format(
                status["status"], len(live.tracks())
            ),
            "blue" if status["status"] in ("running", "completed") else "amber",
            small=True,
        )
    dpg.bind_item_theme(box, th.T["card"])

    w.spacer(18)
    w.title("People found")
    obj_status = obj_bridge.status()
    if obj_status["status"] == "running":
        w.mono("OBJ tracking: running", "blue", small=True)
    elif obj_status["status"] == "completed":
        result = obj_bridge.latest_result() or {}
        w.mono(
            "OBJ tracking: complete · {} master_id track(s)".format(
                len(result.get("tracks", {}))
            ),
            "green",
            small=True,
        )
    elif obj_status["status"] == "error":
        w.mono("OBJ tracking: error · " + str(obj_status["error"]), "amber", small=True)
    elif obj_status["status"] == "no_video":
        w.mono("OBJ tracking: no accessible video exhibit", "amber", small=True)
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
