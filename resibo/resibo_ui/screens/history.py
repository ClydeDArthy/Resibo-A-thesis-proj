"""History: the audit trail of the open case, as it stands right now.

All / Flagged filters the records shown, and clicking a stage narrows the
trail to that stage.
"""

import datetime
import dearpygui.dearpygui as dpg
from .. import data, layout, state, theme as th, widgets as w

TITLE = "History"
CRUMB = ("CASE-2026-09A", "History")
ACTION = ("Export", None)

_flagged_only = {"on": False}
_clock = {"frames": 0}


def build():
    with dpg.group(horizontal=True):
        _stages()
        _records()
        _detail()


# --- Filtering -------------------------------------------------------------

def _case():
    return data.CASES[state.SEL["case"]]


def _visible():
    """Records after the stage filter, the flag filter and any dropped stages."""
    rows = data.records_for(_case())
    if state.SEL["stage"] >= 0:
        stage = data.HISTORY_STAGES[state.SEL["stage"]][0]
        rows = [(i, r) for i, r in rows if r[2] == stage]
    if _flagged_only["on"]:
        rows = [(i, r) for i, r in rows if r[5]]
    return rows


def _set_filter(sender, app_data, flagged):
    """The All / Flagged switch, which drives the records table."""
    _flagged_only["on"] = flagged
    _redraw()


def _pick_stage(sender, app_data, index):
    state.SEL["stage"] = -1 if state.SEL["stage"] == index else index
    _redraw()


def _pick_record(sender, app_data, index):
    state.SEL["record"] = index
    _redraw()


def _redraw():
    state.rebuild("hs_list", _fill_stages)
    state.rebuild("hs_records", _fill_records)
    state.rebuild("hs_detail", _fill_detail)


def refresh():
    """Called when the open case changes."""
    state.SEL["stage"] = -1
    _redraw()


# --- Stage rail ------------------------------------------------------------

def _stages():
    """Left rail: one row per stage, with its live record count."""
    with dpg.child_window(width=320, border=True) as panel:
        layout.register(panel, "left")
        with dpg.table_row(parent=w.header_row(150)):
            with dpg.group():
                w.title("Filter")
                w.mono("by stage", "faint", small=True)
            with dpg.group(horizontal=True):
                w.spacer(6)
                all_btn = dpg.add_button(label="All", tag="hs_all")
                flag_btn = dpg.add_button(label="Flagged", tag="hs_flagged")
                w.font(all_btn, "mono_sm")
                w.font(flag_btn, "mono_sm")
                dpg.configure_item(all_btn, callback=lambda s, a: _set_filter(s, a, False))
                dpg.configure_item(flag_btn, callback=lambda s, a: _set_filter(s, a, True))
        w.spacer(6)
        dpg.add_separator()
        w.spacer(10)
        # Ten stages will not fit on a short window, so this list scrolls.
        with dpg.child_window(tag="hs_list", border=False, width=-1):
            _fill_stages()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_stages():
    # The switch shows which way it is set.
    dpg.bind_item_theme("hs_all", th.T["pill_green"] if not _flagged_only["on"]
                        else th.T["pill_gray"])
    dpg.bind_item_theme("hs_flagged", th.T["pill_amber"] if _flagged_only["on"]
                        else th.T["pill_gray"])

    for i, (name, count, badge, tone) in enumerate(data.stages_for(_case())):
        item = w.list_item(name, count, badge, tone,
                           selected=(i == state.SEL["stage"]))
        state.on_click(item, _pick_stage, i)
        w.spacer(2)


# --- Records ---------------------------------------------------------------

def _records():
    """Centre column: live chain counters and the record log."""
    with dpg.child_window(width=-420, border=True) as pane:
        layout.register(pane, "centre")
        w.title("History", "h1")
        w.mono("Every step is logged and locked to the step before it.", "dim")
        w.spacer(10)
        dpg.add_separator()
        w.spacer(14)
        with dpg.group(tag="hs_records"):
            _fill_records()
    dpg.bind_item_theme(pane, th.T["pane"])


def _fill_records():
    case = _case()
    written = data.records_for(case)
    visible = _visible()
    flags = sum(1 for _i, r in written if r[5])

    hint = "newest first . click a row to open it"
    if state.SEL["stage"] >= 0:
        hint = "filtered to " + data.HISTORY_STAGES[state.SEL["stage"]][0]
    if _flagged_only["on"]:
        hint += " . flagged only"
    w.section("Records", hint)

    stats = [("Chain length", "{:,}".format(len(written)), "text"),
             ("Last checked", dpg.get_value("hs_clock") or "-", "green"),
             ("Flags", "{:02d}".format(flags), "amber" if flags else "green"),
             ("Broken", "0", "text")]
    box_w = w.share(layout.content_width(has_right=True), len(stats))
    with dpg.group(horizontal=True):
        for label, value, tone in stats:
            w.stat_box(label, value, tone, width=box_w)

    w.spacer(14)
    if not visible:
        w.text("No records match this filter.", "faint", "ui_sm", wrap=-1)
        return

    rows = [(rec, time, stage, (what, "amber" if flagged else "green"),
             ("Yes" if linked == "Yes" else "First", "amber" if flagged else "green", True))
            for _i, (rec, time, stage, what, linked, flagged) in visible]
    highlight = next((n for n, (i, _r) in enumerate(visible)
                      if i == state.SEL["record"]), -1)
    w.table(["Record", "Time", "Stage", "What happened", "Linked"], rows,
            weights=[1.1, 0.9, 1.1, 1.8, 0.7], highlight=highlight,
            on_select=lambda s, a, u: _pick_record(s, a, visible[u][0]))


# --- Record detail ---------------------------------------------------------

def _detail():
    """Right rail: the selected record and its place in the hash chain."""
    with dpg.child_window(width=-1, border=True) as panel:
        layout.register(panel, "right")
        with dpg.group(tag="hs_detail"):
            _fill_detail()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_detail():
    visible = _visible()
    if not visible:
        w.title("No record")
        w.mono("nothing matches the filter", "faint", small=True)
        return
    if state.SEL["record"] not in [i for i, _r in visible]:
        state.SEL["record"] = visible[0][0]

    detail = data.history_detail(state.SEL["record"])
    w.title(detail["id"])
    w.mono(detail["sub"], "faint", small=True)
    w.spacer(12)
    dpg.add_separator()
    w.spacer(12)
    w.text("Record", "text", "ui")
    w.spacer(6)
    for key, value, tone in detail["record"]:
        w.kv_row(key, value, tone)
    w.spacer(12)
    w.text("Chain", "text", "ui")
    w.spacer(6)
    for key, value, tone in detail["chain"]:
        w.kv_row(key, value, tone)


# --- Live clock ------------------------------------------------------------

def tick():
    """Keep the 'last checked' time current while this screen is open."""
    _clock["frames"] += 1
    if _clock["frames"] % 60:
        return
    now = datetime.datetime.now().strftime("%H:%M:%S")
    if dpg.does_item_exist("hs_clock"):
        dpg.set_value("hs_clock", now)
        state.rebuild("hs_records", _fill_records)


def install_clock():
    """A hidden value item so the clock survives rebuilds of the panel."""
    if not dpg.does_item_exist("hs_clock"):
        with dpg.value_registry():
            dpg.add_string_value(tag="hs_clock",
                                 default_value=datetime.datetime.now().strftime("%H:%M:%S"))
