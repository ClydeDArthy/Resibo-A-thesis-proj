"""Face module: the detected person, their face outputs over the case video, and the gait output."""

import dearpygui.dearpygui as dpg
from .. import (data, layout, state, theme as th, video, video_preview, viewer,
                widgets as w)

TITLE = "Face module"
CRUMB = ("CASE-2026-09A", "Face module")
ACTION = None

PER_ROW = 3
TILE_H = 186
STAGE_H = 196
RAIL_SCALE = 0.5
ICON_MAX = 96
HIDDEN_STAGES = {"Walk cycles", "Walk pattern"}


def build():
    with dpg.group(horizontal=True):
        _detected()
        _outputs()


def refresh():
    state.SEL["face_module"] = 0
    _redraw()


def _redraw():
    state.rebuild("fm_detected", _fill_detected)
    state.rebuild("fm_main", _fill_main)


def _pick(sender, app_data, index):
    state.SEL["face_module"] = index
    _redraw()


def _current():
    if not data.FACE_PERSONS:
        return None
    index = min(state.SEL["face_module"], len(data.FACE_PERSONS) - 1)
    return index, data.FACE_PERSONS[index]


def _start_of(person):
    tracks = data.PEOPLE_TRACKS.get(person) or []
    return min((seg[0] for seg in tracks), default=0.0)


def _detected():
    with dpg.child_window(width=350, border=True) as panel:
        layout.register(panel, "left", RAIL_SCALE)
        layout.on_resize(lambda: state.rebuild("fm_detected", _fill_detected))
        with dpg.group(tag="fm_detected"):
            _fill_detected()
    dpg.bind_item_theme(panel, th.T["panel"])


def _rail_width():
    return int(layout.widths()[0] * RAIL_SCALE)


def _fill_detected():
    w.text("Persons detected", "text", "ui_sm", wrap=_rail_width() - 24)
    w.spacer(4)
    dpg.add_separator()
    w.spacer(8)
    current = _current()
    if current is None:
        w.mono("none yet", "faint", small=True)
        return
    index = current[0]
    for i, (ident, _sub, tone, person) in enumerate(data.FACE_PERSONS):
        _icon(i, ident, person, tone, selected=(i == index))
        w.spacer(4)


def _icon(i, ident, person, tone, selected):
    cell = _rail_width() - 26
    inner = cell - 16
    size = min(ICON_MAX, inner)
    with dpg.child_window(width=cell, height=size + 40, border=False,
                          no_scrollbar=True, no_scroll_with_mouse=True) as tile:
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=max(0, (inner - size) // 2))
            with dpg.drawlist(width=size, height=size):
                fill = th.BG_CARD_HOVER if selected else th.BG_CARD
                dpg.draw_rectangle((1, 1), (size - 1, size - 1), fill=fill,
                                   color=th.GREEN if selected else th.BORDER,
                                   rounding=14, thickness=2 if selected else 1)
                tex = w._silhouette_texture()
                if tex:
                    pad = size * 0.14
                    alpha = 235 if tone == "green" else 150
                    dpg.draw_image(tex, (pad, pad), (size - pad, size - pad),
                                   color=(255, 255, 255, alpha))
        w.center_text(ident, inner, "green" if selected else "text", "ui_sm")
    dpg.bind_item_theme(tile, th.T["bare"])
    with dpg.tooltip(tile):
        w.text(person, "text", "ui_sm", wrap=-1)
    state.on_click(tile, _pick, i)


def _outputs():
    with dpg.child_window(width=-1, border=True) as pane:
        layout.on_resize(lambda: state.rebuild("fm_main", _fill_main))
        with dpg.group(tag="fm_main"):
            _fill_main()
    dpg.bind_item_theme(pane, th.T["pane"])


def _fill_main():
    current = _current()
    if current is None:
        w.text("Nothing to show until people have been detected.", "dim", "ui")
        return
    _index, (identity, _sub, _tone, person) = current
    art = layout.content_width(has_right=False) + layout.widths()[0] - _rail_width()

    _player(identity, person, art)
    w.spacer(14)
    _face_tiles(identity, person, art)
    w.spacer(10)
    _scores(person, art)

    w.spacer(18)
    w.section("Gait output", data.identity_for(person))
    _gait(person, art)
    w.spacer(16)


def _player(identity, person, art):
    case_number = data.CASES[state.SEL["case"]]["number"]
    path = video.sealed_path(case_number)
    start = _start_of(person)
    height = min(360, int(art * 9 / 16))

    with dpg.child_window(height=height + 74, border=True, no_scrollbar=True,
                          no_scroll_with_mouse=True) as box:
        dl = path and video.draw(art, height, path, at_fraction=start,
                                 play_badge=True, subtitle=identity)
        if dl:
            play = lambda s, a, u: video_preview.open_video_preview(path, identity, start)
            state.on_click(dl, play)
        else:
            dl = w.video_frame(art, height, "", "")
            dpg.push_container_stack(dl)
            w.draw_subtitle(identity, 0, height, art)
            dpg.pop_container_stack()
        w.spacer(8)
        with dpg.group(horizontal=True):
            button = dpg.add_button(label="Play", width=90, enabled=bool(path),
                                    callback=lambda *_: video_preview.open_video_preview(
                                        path, identity, start))
            dpg.bind_item_theme(button, th.T["btn_ghost"] if path else th.T["bare"])
            dpg.add_spacer(width=10)
            note = ("plays from where {} first appears".format(identity) if path
                    else "no sealed video for this case yet")
            w.mono(note, "faint", small=True)
    dpg.bind_item_theme(box, th.T["card"])


def _face_tiles(identity, person, art):
    tile = w.share(art, PER_ROW)
    items = data.FOLDER_ITEMS
    for start in range(0, len(items), PER_ROW):
        with dpg.group(horizontal=True):
            for frame, enhanced in items[start:start + PER_ROW]:
                item = w.face_tile("enhanced" if enhanced else "raw",
                                   "frame " + frame, width=tile, height=TILE_H,
                                   blurred=not enhanced, centered=True)
                state.on_double_click(item, _open_crop,
                                      (identity, person, frame, enhanced))
        w.spacer(8)


def _open_crop(sender, app_data, user_data):
    identity, person, frame, enhanced = user_data
    viewer.show(identity, "frame " + frame, data.look(person), enhanced,
                data.folder_meta(identity, "faces", frame, enhanced))


def _scores(person, art):
    summary = data.match_summary(person)
    width = w.share(art, len(summary) + 1)
    with dpg.group(horizontal=True):
        for label, value, sub, tone in summary:
            w.stat_box(label, value, tone, sub, width=width)
        matched = data.MATCHED_IDENTITY.get(person, "no match")
        w.stat_box("Matched", matched, "dim" if matched == "no match" else "green",
                   "compared to known people", width=width, big=False)


def _gait(person, art):
    stages = [st for st in data.WALK_STAGES if st[1] not in HIDDEN_STAGES]
    if stages:
        stage_w = w.share(art, len(stages))
        last = stages[-1][0]
        with dpg.group(horizontal=True):
            for letter, caption, sub in stages:
                w.face_tile(caption, sub, width=stage_w, height=STAGE_H,
                            blurred=(letter in "ab"), selected=(letter == last),
                            letter=letter, landmarks=(letter == "c"))
        w.spacer(14)

    detail = data.WALK_DETAILS.get(person) or {}
    if detail.get("warn"):
        w.spacer(10)
        w.text(detail["warn"][0], "amber", "ui", wrap=-1)
        w.text(detail["warn"][1], "dim", "ui_sm", wrap=art)
