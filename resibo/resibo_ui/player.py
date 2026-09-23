"""Scrub bars that actually play.

Each bar registers itself here; `tick()` runs once per frame, advances any
playing bar and redraws its track.
"""

import dearpygui.dearpygui as dpg
from . import theme as th, widgets as w

_players = {}
_next_id = [0]


def _seconds(stamp):
    """Turn 'HH:MM:SS' (or 'MM:SS') into seconds."""
    parts = [int(p) for p in stamp.split(":")]
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


def _stamp(seconds):
    """Turn seconds back into 'HH:MM:SS'."""
    seconds = max(0, int(seconds))
    return "{:02d}:{:02d}:{:02d}".format(seconds // 3600, seconds // 60 % 60, seconds % 60)


def _draw(player):
    """Redraw one track at its current position."""
    width = player["width"]
    pos = player["pos"]
    dpg.delete_item(player["track"], children_only=True)
    dpg.push_container_stack(player["track"])
    dpg.draw_line((0, 9), (width, 9), color=(40, 48, 56), thickness=3)
    dpg.draw_line((0, 9), (width * pos, 9), color=th.GREEN, thickness=3)
    dpg.draw_circle((width * pos, 9), 5, fill=th.GREEN, color=th.GREEN)
    for mark in player["marks"]:            # amber ticks mark flagged moments
        dpg.draw_line((width * mark, 2), (width * mark, 16), color=th.AMBER, thickness=2)
    dpg.pop_container_stack()
    dpg.set_value(player["elapsed"], _stamp(pos * player["duration"]))


def _toggle(sender, app_data, key):
    """Play/pause, restarting if the clip has run to the end."""
    player = _players[key]
    player["playing"] = not player["playing"]
    if player["playing"] and player["pos"] >= 0.999:
        player["pos"] = 0.0
    dpg.configure_item(player["button"], label="||" if player["playing"] else ">")


def _seek(sender, app_data, key):
    """Jump to wherever the track was clicked."""
    player = _players[key]
    x_mouse = dpg.get_mouse_pos(local=False)[0]
    x_track = dpg.get_item_rect_min(player["track"])[0]
    player["pos"] = min(1.0, max(0.0, (x_mouse - x_track) / player["width"]))
    _draw(player)


# Play button, elapsed and total time sit either side of the track.
CHROME = 250


def bar(current, total, progress=0.45, marks=(), width=620):
    """Play button, elapsed time, clickable scrub track and total length.

    `width` is the whole row; the track takes what the labels leave.
    """
    width = max(120, width - CHROME)
    _next_id[0] += 1
    key = "player_{}".format(_next_id[0])

    with dpg.group(horizontal=True):
        button = dpg.add_button(label=">", width=30,
                                callback=lambda s, a: _toggle(s, a, key))
        dpg.bind_item_theme(button, th.T["bare"])
        elapsed = w.text(current, "dim", "mono", wrap=-1)
        dpg.add_spacer(width=6)
        track = dpg.add_drawlist(width=width, height=18)
        dpg.add_spacer(width=6)
        w.text(total, "dim", "mono", wrap=-1)

    _players[key] = {
        "pos": progress, "playing": False, "width": width, "marks": tuple(marks),
        "duration": _seconds(total) or 1, "track": track,
        "button": button, "elapsed": elapsed,
    }
    _draw(_players[key])

    # Clicking anywhere on the track seeks to that point.
    with dpg.item_handler_registry() as reg:
        dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left,
                                     callback=lambda s, a: _seek(s, a, key))
    dpg.bind_item_handler_registry(track, reg)
    return key


def tick():
    """Advance every playing bar. Called once per frame."""
    delta = dpg.get_delta_time()
    for key in list(_players):
        player = _players[key]
        if not dpg.does_item_exist(player["track"]):
            del _players[key]                 # the screen was rebuilt
            continue
        if not player["playing"]:
            continue
        player["pos"] += delta / player["duration"]
        if player["pos"] >= 1.0:              # stop cleanly at the end
            player["pos"] = 1.0
            player["playing"] = False
            dpg.configure_item(player["button"], label=">")
        _draw(player)
