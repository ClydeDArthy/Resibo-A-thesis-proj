"""Walking: gait analysis run on the person folders, separate from the face side."""

import dearpygui.dearpygui as dpg
from .. import data, layout, state, theme as th, widgets as w, widgets_plot as wp

TITLE = "Walking"
CRUMB = ("CASE-2026-09A", "Walking")
ACTION = None
HIDDEN_STAGES = {"Body points", "Walk cycles", "Walk pattern"}


def build():
    with dpg.group(horizontal=True):
        _results()
        _analysis()
        _detail()


def _pick(sender, app_data, index):
    """Select a person; the table and detail panel follow."""
    state.SEL["walk"] = index
    state.rebuild("wk_list", _fill_list)
    state.rebuild("wk_main", _fill_main)
    state.rebuild("wk_detail", _fill_detail)


def _results():
    """Left rail: usability verdict for each person checked."""
    with dpg.child_window(width=300, border=True) as panel:
        layout.register(panel, "left")
        w.title("Results")
        w.mono("{} people checked".format(len(data.WALK_RESULTS)), "faint", small=True)
        w.spacer(6)
        dpg.add_separator()
        w.spacer(10)
        with dpg.child_window(tag="wk_list", border=False, width=-1, no_scrollbar=True, no_scroll_with_mouse=True):
            _fill_list()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_list():
    for i, (name, reason, badge, tone) in enumerate(data.WALK_RESULTS):
        item = w.list_item(data.identity_for(name), reason, badge, tone,
                           selected=(i == state.SEL["walk"]))
        state.on_click(item, _pick, i)
        w.spacer(2)


def _analysis():
    """Centre column: folders, per-stage images, results table, chart and caveats."""
    with dpg.child_window(width=-390, border=True) as pane:
        layout.register(pane, "centre")
        layout.on_resize(lambda: state.rebuild("wk_main", _fill_main))
        with dpg.group(tag="wk_main"):
            _fill_main()
    dpg.bind_item_theme(pane, th.T["pane"])


def _fill_main():
    index = state.SEL["walk"]
    person = data.WALK_RESULTS[index][0]

    w.section("Person folders")
    def draw(i):
        name, sub, tone = data.PERSON_FOLDERS[i]
        tile = w.folder_tile(data.identity_for(name), sub, tone, height=100,
                             selected=(name == person))
        state.on_click(tile, _pick, i)

    w.tile_grid(len(data.PERSON_FOLDERS), 4, draw)

    w.spacer(16)
    w.section(data.identity_for(person) + " - step by step",
              "each stage keeps its own picture")
    stage_w = w.share(layout.content_width(has_right=True), len(data.WALK_STAGES))
    with dpg.group(horizontal=True):
        for letter, caption, sub in data.WALK_STAGES:
            if caption not in HIDDEN_STAGES:
                w.face_tile(caption, sub, width=stage_w, height=196,
                            blurred=True, letter=letter)

    w.spacer(16)
    w.section("Walking results", "one cycle = heel down to heel down again")
    rows = [(data.identity_for(r[0]),) + tuple(r[1:]) for r in data.WALK_TABLE]
    w.table(["Identity", "Cycles", "Cadence", "Left vs right", "Usable"],
            rows, weights=[1, 1, 1.1, 1.1, 1.2], highlight=index)

    w.spacer(16)
    w.section("Where the cycles were found",
              "ankle height per frame . amber lines are heel down")
    wp.gait_chart_frame()



def _detail():
    """Right rail: inputs, measurements and recording conditions for one person."""
    with dpg.child_window(width=-1, border=True) as panel:
        layout.register(panel, "right")
        with dpg.group(tag="wk_detail"):
            _fill_detail()
    dpg.bind_item_theme(panel, th.T["panel"])


def _fill_detail():
    person = data.WALK_RESULTS[state.SEL["walk"]][0]
    detail = data.WALK_DETAILS[person]

    w.title(data.identity_for(person))
    w.mono("{} . tracked as {}".format(detail["id"], person), "faint", small=True)
    w.spacer(8)

    # Conditions that weaken the result are stated up front.
    if detail["warn"]:
        w.text(detail["warn"][0], "amber", "ui", wrap=-1)
        w.text(detail["warn"][1], "dim", "ui_sm", wrap=layout.widths()[1] - 60)
        w.spacer(14)

    for group, label in (("input", "Input"), ("measured", "Measured"),
                         ("conditions", "Conditions")):
        w.text(label, "text", "ui")
        w.spacer(6)
        for key, value, tone in detail[group]:
            w.kv_row(key, value, tone)
        w.spacer(10)
