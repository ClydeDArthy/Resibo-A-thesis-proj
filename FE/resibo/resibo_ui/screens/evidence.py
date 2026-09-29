"""Evidence intake: the exhibit files, hashed and sealed before any analysis."""

import hashlib
import os
import dearpygui.dearpygui as dpg
from .. import actions, data, db, layout, scrim, state, theme as th, uploads, widgets as w

TITLE = "Evidence"
CRUMB = ("CASE-2026-09A", "Evidence intake")
ACTION = None

CONFIRM_W, CONFIRM_H = 460, 230
_pending = {"prefix": None, "row_id": None}


def build(prefix="wsp"):
    """`prefix` keeps tags unique; this panel appears on the landing too."""
    with dpg.child_window(width=-1, border=True) as pane:
        with dpg.group(tag=prefix + "_evidence"):
            _fill(prefix)
    dpg.bind_item_theme(pane, th.T["pane"])


def _case():
    return data.CASES[state.SEL["case"]]


def refresh():
    """Redraw after the open case changes."""
    state.SEL["exhibit"] = 0
    if dpg.does_item_exist("wsp_evidence"):
        state.rebuild("wsp_evidence", lambda: _fill("wsp"))


def _rows_for_case(case_number):
    """(rows, summary) for this case: the real sealed exhibits and their live
    totals, or the illustrative mock data if it has none yet."""
    real = db.evidence_for(case_number)
    if not real:
        rows = [(None, ex, name, size, h, status) for ex, name, size, h, status in data.EVIDENCE]
        return rows, data.EVIDENCE_SUMMARY

    # Named after the order the user actually attached them in, not the
    # underlying database row id (which is shared across every case).
    rows = [(r["id"], "Attachment {}".format(i + 1), r["name"],
             uploads.size_text(r["size"] or 0), r["digest"] or "", "Sealed")
            for i, r in enumerate(real)]

    total = sum(r["size"] or 0 for r in real)
    sealed_at = max((r["sealed_at"] or "" for r in real), default="")
    sealed_time = sealed_at.split(" ")[1] if " " in sealed_at else (sealed_at or "-")
    summary = [("Exhibits", str(len(real)), "text"),
              ("Total size", uploads.size_text(total), "text"),
              ("Hash", "SHA-256", "text"),
              ("Sealed at", sealed_time, "green")]
    return rows, summary


def _pick(sender, app_data, user_data):
    prefix, index = user_data
    state.SEL["exhibit"] = index
    state.rebuild(prefix + "_evidence", lambda: _fill(prefix))


def _fill(prefix):
    case = _case()
    rows_data, summary = _rows_for_case(case["number"])

    w.title("Evidence intake", "h1")
    w.mono("The original files are hashed and sealed. Nothing here is modified.", "dim")
    w.spacer(10)
    dpg.add_separator()
    w.spacer(14)

    box_w = w.share(layout.content_width(has_right=False), len(summary))
    with dpg.group(horizontal=True):
        for label, value, tone in summary:
            w.stat_box(label, value, tone, width=box_w)

    w.spacer(18)
    w.section("Exhibits", "hashed on arrival, then written to the vault")
    rows = [(label, name, size, (h, "dim"), (status, "green", True))
            for _rid, label, name, size, h, status in rows_data]
    w.table(["Exhibit", "File", "Size", "Hash (SHA-256)", "Status"], rows,
            weights=[0.8, 2.0, 0.7, 1.8, 0.9],
            highlight=state.SEL["exhibit"],
            on_select=lambda s, a, u: _pick(s, a, (prefix, u)))

    w.spacer(18)
    finished = actions.case_complete()
    with dpg.group(horizontal=True):
        add = dpg.add_button(label="Add exhibit", width=140,
                             callback=lambda s, a, u: _add_exhibit(prefix))
        dpg.bind_item_theme(add, th.T["btn_ghost"])
        if not finished and rows_data:
            dpg.add_spacer(width=10)
            remove = dpg.add_button(label="Remove attachment", width=170,
                                    callback=lambda s, a, u: _ask_remove(prefix, rows_data))
            dpg.bind_item_theme(remove, th.T["btn_danger"])


def _hash_file(path):
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(2 * 1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def _add_exhibit(prefix):
    """Pick real files and seal them onto the case that's actually open."""
    paths = actions.pick_evidence_files()
    if not paths:
        return

    case = _case()
    accepted, rejected = [], 0
    for path in paths:
        if not uploads.is_allowed(path):
            rejected += 1
            continue
        try:
            size = os.path.getsize(path)
            digest = _hash_file(path)
        except OSError:
            rejected += 1
            continue
        accepted.append({"name": os.path.basename(path), "path": path,
                         "size": size, "digest": digest})

    if accepted:
        db.insert_evidence(case["number"], accepted)
        case["exhibits"] = case.get("exhibits", 0) + len(accepted)
        db.insert_case(case)
        actions.toast("Added {} exhibit(s)".format(len(accepted)))
    if rejected:
        actions.toast("{} file(s) skipped - only JPEG, MP4, DAV or ASF are allowed"
                      .format(rejected), "amber")
    if accepted and dpg.does_item_exist(prefix + "_evidence"):
        state.rebuild(prefix + "_evidence", lambda: _fill(prefix))


def _ask_remove(prefix, rows_data):
    index = state.SEL["exhibit"]
    if not (0 <= index < len(rows_data)):
        return
    row_id = rows_data[index][0]
    case = _case()
    message = "Are you sure?" if case["done"] == 0 else "The progress will reset!"
    _pending.update(prefix=prefix, row_id=row_id)
    dpg.set_value("ev_confirm_text", message)
    try:
        width = dpg.get_viewport_client_width()
        height = dpg.get_viewport_client_height()
    except Exception:
        width, height = 1500, 940
    scrim.show()
    dpg.configure_item("ev_remove_confirm", show=True,
                       pos=((width - CONFIRM_W) // 2, (height - CONFIRM_H) // 2))
    dpg.focus_item("ev_remove_confirm")


def _cancel_remove(sender=None, app_data=None, user_data=None):
    scrim.hide()
    dpg.configure_item("ev_remove_confirm", show=False)


def _do_remove(sender=None, app_data=None, user_data=None):
    row_id = _pending["row_id"]
    prefix = _pending["prefix"]
    scrim.hide()
    dpg.configure_item("ev_remove_confirm", show=False)
    if row_id is None:
        return

    case = _case()
    db.delete_evidence(row_id)
    if case["done"] > 0:
        case["done"] = 0
        case["status"] = "Intake only"
    case["exhibits"] = max(0, case.get("exhibits", 1) - 1)
    db.insert_case(case)
    state.SEL["exhibit"] = 0
    actions.toast("Exhibit removed", "amber")
    if prefix and dpg.does_item_exist(prefix + "_evidence"):
        state.rebuild(prefix + "_evidence", lambda: _fill(prefix))

    from . import progress
    if dpg.does_item_exist("pg_steps"):
        progress.refresh()


def build_dialog():
    """Confirmation modal for removing a sealed exhibit; built once, hidden."""
    with dpg.window(tag="ev_remove_confirm", modal=True, show=False, no_resize=True,
                    no_move=True, no_title_bar=True, no_collapse=True,
                    no_scrollbar=True, no_scroll_with_mouse=True,
                    width=CONFIRM_W, height=CONFIRM_H) as win:
        dpg.add_spacer(height=4)
        w.text("Remove attachment", "red", "h2", wrap=-1)
        w.spacer(10)
        w.font(dpg.add_text("", tag="ev_confirm_text"), "ui")
        w.spacer(6)
        w.text("The exhibit is deleted from the vault and cannot be recovered.",
               "dim", "ui_sm", wrap=CONFIRM_W - 60)
        w.spacer(24)
        with dpg.table_row(parent=w.split_row(0)):
            dpg.add_spacer(width=1)
            with dpg.group(horizontal=True):
                cancel = dpg.add_button(label="Cancel", width=130, callback=_cancel_remove)
                dpg.bind_item_theme(cancel, th.T["btn_ghost"])
                dpg.add_spacer(width=10)
                confirm = dpg.add_button(label="Remove", width=130, callback=_do_remove)
                dpg.bind_item_theme(confirm, th.T["btn_danger"])
    dpg.bind_item_theme(win, th.T["panel"])
