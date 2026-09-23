"""Evidence intake: the exhibit files, hashed and sealed before any analysis."""

import dearpygui.dearpygui as dpg
from .. import actions, data, layout, state, theme as th, widgets as w

TITLE = "Evidence"
CRUMB = ("CASE-2026-09A", "Evidence intake")
ACTION = None


def build(prefix="wsp"):
    """`prefix` keeps tags unique; this panel appears on the landing too."""
    with dpg.child_window(width=-1, border=True) as pane:
        with dpg.group(tag=prefix + "_evidence"):
            _fill(prefix)
    dpg.bind_item_theme(pane, th.T["pane"])


def _pick(sender, app_data, user_data):
    prefix, index = user_data
    state.SEL["exhibit"] = index
    state.rebuild(prefix + "_evidence", lambda: _fill(prefix))


def _fill(prefix):
    w.title("Evidence intake", "h1")
    w.mono("The original files are hashed and sealed. Nothing here is modified.", "dim")
    w.spacer(10)
    dpg.add_separator()
    w.spacer(14)

    box_w = w.share(layout.content_width(has_right=False), len(data.EVIDENCE_SUMMARY))
    with dpg.group(horizontal=True):
        for label, value, tone in data.EVIDENCE_SUMMARY:
            w.stat_box(label, value, tone, width=box_w)

    w.spacer(18)
    w.section("Exhibits", "hashed on arrival, then written to the vault")
    rows = [(ex, name, size, (h, "dim"), (status, "green", True))
            for ex, name, size, h, status in data.EVIDENCE]
    w.table(["Exhibit", "File", "Size", "Hash (SHA-256)", "Status"], rows,
            weights=[0.8, 2.0, 0.7, 1.8, 0.9],
            highlight=state.SEL["exhibit"],
            on_select=lambda s, a, u: _pick(s, a, (prefix, u)))

    w.spacer(18)
    with dpg.group(horizontal=True):
        add = dpg.add_button(label="Add exhibit", width=140, callback=actions.browse)
        dpg.bind_item_theme(add, th.T["btn_ghost"])
        dpg.add_spacer(width=10)
        seal = dpg.add_button(label="Verify seals", width=140,
                              callback=lambda: actions.toast("All 3 seals verified"))
        dpg.bind_item_theme(seal, th.T["btn_ghost"])

