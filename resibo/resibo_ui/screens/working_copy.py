"""Working copy: the original is sealed and all analysis runs on a verified copy."""

import dearpygui.dearpygui as dpg
from .. import data, layout, theme as th, widgets as w

TITLE = "Working copy"
CRUMB = ("CASE-2026-09A", "Copy")
ACTION = None


def build():
    with dpg.group(horizontal=True):
        _steps()
        _checks()
        _record()


def _steps():
    """Left rail: the six preservation steps, in the order they must happen."""
    with dpg.child_window(width=350, border=True) as panel:
        layout.register(panel, "left")
        w.title("Steps")
        w.spacer(4)
        dpg.add_separator()
        w.spacer(10)
        with dpg.child_window(tag="wc_list", border=False, width=-1, no_scrollbar=True, no_scroll_with_mouse=True):
            _fill_list()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_list():
    for name, badge, tone in data.COPY_STEPS:
        w.step_card(name, "", badge, tone)
        w.spacer(4)


def _checks():
    """Centre column: hash comparison and the technical read of the video."""
    with dpg.child_window(width=-430, border=True) as pane:
        layout.register(pane, "centre")
        with dpg.table_row(parent=w.header_row(70)):
            with dpg.group():
                w.title("Working copy", "h1")
                w.mono("The original stays untouched. Work happens on a copy.", "dim")
            with dpg.group():
                w.text("Hashes", "dim", "ui_sm")
                w.text("match", "green", "mono")

        w.spacer(10)
        dpg.add_separator()
        w.spacer(14)

        w.title("Hash check")
        w.spacer(8)
        rows = [(name, (h, "dim"), result) for name, h, result in data.COPY_HASHES]
        w.table(["File", "Hash", "Result"], rows, weights=[1, 1.6, 1])

        w.spacer(20)
        w.title("Video details")
        w.spacer(8)
        w.table(["Field", "Value"],
                [(field, (value, tone)) for field, value, tone in data.VIDEO_DETAILS],
                weights=[1, 2])

    dpg.bind_item_theme(pane, th.T["pane"])


def _record():
    """Right rail: the audit record written for this copy operation."""
    with dpg.child_window(width=-1, border=True) as panel:
        layout.register(panel, "right")
        w.title("Copy record")
        w.mono(data.COPY_RECORD["id"], "faint", small=True)
        w.spacer(6)
        dpg.add_separator()
        w.spacer(10)

        w.text("Copy", "text", "ui")
        w.spacer(6)
        w.kv_row("Converted", data.COPY_RECORD["converted"])
        w.kv_row("Reason", data.COPY_RECORD["reason"])
        w.kv_row("Frames", data.COPY_RECORD["frames"])
        w.kv_row("Result", data.COPY_RECORD["result"], "green")
    dpg.bind_item_theme(panel, th.T["panel"])
