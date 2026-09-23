"""New case: one panel, filled top to bottom.

The evidence section stays empty until every detail is filled in, and the
case is only created once the evidence is sealed.
"""

import datetime
import dearpygui.dearpygui as dpg

from .. import actions, data, layout, theme as th, uploads, widgets as w

TITLE = "New case"
CRUMB = ("New case", "Details")
ACTION = None

FORM_W = 940
COL_W = 450

# Every field, in order, with its label and placeholder.
FIELDS = [
    ("nc_case_name", "Case name", "Alleged theft - Warehouse B"),
    ("nc_case_number", "Case number", "CASE-2026-11D"),
    ("nc_base_dir", "Base directory", "/var/evidence/cases/2026-11D"),
    ("nc_camera", "Camera", "HIKVISION 23MN"),
    ("nc_camera_loc", "Camera location", "Warehouse Bh CAM - 04"),
    ("nc_name", "Examiner name", "Maria Edona I. Inocencio"),
    ("nc_phone", "Phone", "+639 17 555 0143"),
    ("nc_email", "Email", "einocencio@students.nu-manila.edu.ph"),
]

_created = [None]          # app.run() supplies the "case is ready" callback
_cancelled = [None]        # and the way back out of a new case


def set_handler(on_created, on_cancel=None):
    _created[0] = on_created
    _cancelled[0] = on_cancel


def _cancel(sender=None, app_data=None, user_data=None):
    """Abandon this case and go back to the case list."""
    reset()
    if _cancelled[0]:
        _cancelled[0]()


def build():
    with dpg.child_window(width=-1, height=-1, border=True) as pane:
        # Centre the column so the panel does not read as left-weighted.
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=max(0, (layout.full_width() - FORM_W) // 2))
            with dpg.child_window(width=FORM_W, border=True) as form:
                dpg.add_spacer(height=6)
                _form()
                w.spacer(26)
                # Evidence only opens once the details above are complete.
                with dpg.group(tag="nc_evidence"):
                    _fill_evidence()
                w.spacer(30)
            dpg.bind_item_theme(form, th.T["pane"])
    dpg.bind_item_theme(pane, th.T["pane"])


def reset():
    """Clear the form and any files, ready for another new case."""
    uploads.clear()
    for tag, _label, _hint in FIELDS:
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, "")
    _refresh()


# --- Details --------------------------------------------------------------

def _field(tag, label, hint, width=COL_W, browse=False):
    with dpg.group():
        w.text(label, "dim", "ui_sm", wrap=-1)
        with dpg.group(horizontal=True):
            box = dpg.add_input_text(tag=tag, width=width, hint=hint,
                                     callback=lambda s, a: _refresh())
            w.font(box, "mono")
            if browse:
                b = dpg.add_button(label="Browse", width=90, callback=actions.browse)
                dpg.bind_item_theme(b, th.T["btn_ghost"])


def _pair(left, right):
    with dpg.group(horizontal=True):
        _field(*left)
        dpg.add_spacer(width=20)
        _field(*right)
    w.spacer(14)


def _form():
    """One continuous block: case, camera and examiner, no dividers."""
    _pair(FIELDS[0], FIELDS[1])
    _field(*FIELDS[2], width=FORM_W - 170, browse=True)
    w.spacer(14)
    _pair(FIELDS[3], FIELDS[4])
    _pair(FIELDS[5], FIELDS[6])
    _field(*FIELDS[7], width=FORM_W - 60)


def details_done():
    """True when every field has something in it."""
    return all(str(dpg.get_value(tag) or "").strip()
               for tag, _l, _h in FIELDS if dpg.does_item_exist(tag))


# --- Evidence -------------------------------------------------------------

def _refresh():
    from .. import state
    state.rebuild("nc_evidence", _fill_evidence)


def _pick_files(sender=None, app_data=None, user_data=None):
    dpg.show_item("dlg_evidence")


def _files_chosen(sender, app_data):
    """Queue everything the dialog returned."""
    chosen = app_data.get("selections") or {}
    for path in chosen.values():
        uploads.add(path)
    if not chosen and app_data.get("file_path_name"):
        uploads.add(app_data["file_path_name"])
    _refresh()


def _drop_file(sender, app_data, index):
    uploads.remove(index)
    _refresh()


def _seal(sender=None, app_data=None, user_data=None):
    """Create the case and hand it to the workspace."""
    if not uploads.all_done():
        actions.toast("Files are still being hashed", "amber")
        return
    count, total = uploads.totals()
    case = {
        "examiner": dpg.get_value("nc_name").strip(),
        "number": dpg.get_value("nc_case_number").strip(),
        "place": dpg.get_value("nc_camera_loc").strip(),
        "badge": "Active", "tone": "green",
        "name": dpg.get_value("nc_case_name").strip(),
        "opened": datetime.date.today().isoformat(),
        "exhibits": count, "flags": 0, "chain": "verified",
        "status": "Ready", "done": 0,
    }
    data.CASES.append(case)
    actions.toast("Sealed {} exhibit(s) - {}".format(count, uploads.size_text(total)))
    if _created[0]:
        _created[0](len(data.CASES) - 1)


def _fill_evidence():
    """Empty until the details are done; then the intake and file list."""
    if not details_done():
        w.spacer(20)
        dpg.add_separator()
        w.spacer(24)
        w.text("Evidence intake opens once the details above are complete.",
               "faint", "ui_sm", wrap=-1)
        w.spacer(18)
        drop = dpg.add_button(label="Cancel", width=130, callback=_cancel)
        dpg.bind_item_theme(drop, th.T["btn_ghost"])
        return

    dpg.add_separator()
    w.spacer(18)
    w.title("Evidence intake", "h2")
    w.mono("Files are hashed on arrival. Nothing is modified.", "dim")
    w.spacer(14)

    count, total = uploads.totals()
    done = uploads.all_done()
    sealed = datetime.datetime.now().strftime("%H:%M:%S") if done else "-"
    summary = [("Exhibits", str(count), "text" if count else "dim"),
               ("Total size", uploads.size_text(total), "text" if count else "dim"),
               ("Hash", "SHA-256" if count else "-", "text" if count else "dim"),
               ("Hashed at", sealed, "green" if done else "dim")]
    box_w = w.share(FORM_W - 40, len(summary))
    with dpg.group(horizontal=True):
        for label, value, tone in summary:
            w.stat_box(label, value, tone, width=box_w)

    w.spacer(16)
    with dpg.group(horizontal=True):
        add = dpg.add_button(label="Add files", width=150, callback=_pick_files)
        dpg.bind_item_theme(add, th.T["btn_ghost"])
        dpg.add_spacer(width=10)
        seal = dpg.add_button(label="Seal and continue  >", width=230, callback=_seal)
        dpg.bind_item_theme(seal, th.T["btn_primary"] if done else th.T["btn_ghost"])
        dpg.add_spacer(width=10)
        drop = dpg.add_button(label="Cancel", width=130, callback=_cancel)
        dpg.bind_item_theme(drop, th.T["btn_ghost"])

    w.spacer(16)
    if not uploads.FILES:
        w.text("No files yet. Add the recordings for this case.", "faint", "ui_sm", wrap=-1)
        return

    for i, entry in enumerate(uploads.FILES):
        _file_row(i, entry)
        w.spacer(6)


def _file_row(index, entry):
    """One file: name, size, progress or hash, and a remove or cancel button."""
    reading = entry["state"] == "reading"
    with dpg.child_window(auto_resize_y=True, border=True, no_scrollbar=True,
                          no_scroll_with_mouse=True) as row:
        with dpg.table_row(parent=w.split_row(0)):
            with dpg.group():
                w.text(entry["name"], "text", "ui", wrap=-1)
                if entry["state"] == "error":
                    w.text("could not be read", "amber", "mono_sm", wrap=-1)
                elif reading:
                    w.text("{}  .  hashing {:.0f}%".format(
                        uploads.size_text(entry["size"]),
                        uploads.progress(entry) * 100), "dim", "mono_sm", wrap=-1)
                else:
                    w.text("{}  .  {}...".format(uploads.size_text(entry["size"]),
                                                 entry["digest"][:16]),
                           "dim", "mono_sm", wrap=-1)
            with dpg.group():
                w.spacer(4)
                btn = dpg.add_button(label="Cancel" if reading else "Remove",
                                     width=100, callback=_drop_file, user_data=index)
                dpg.bind_item_theme(btn, th.T["btn_ghost"])
        if reading:
            bar = dpg.add_progress_bar(default_value=uploads.progress(entry),
                                       width=-1, height=4, overlay="")
            dpg.bind_item_theme(bar, th.T["bar_blue"])
    dpg.bind_item_theme(row, th.T["card"])


def build_dialog():
    """Multi-select file dialog for the evidence files."""
    with dpg.file_dialog(tag="dlg_evidence", label="Add evidence files",
                         directory_selector=False, show=False, modal=True,
                         width=760, height=480, callback=_files_chosen):
        dpg.add_file_extension(".*")
        dpg.add_file_extension(".mp4", color=(74, 222, 128))
        dpg.add_file_extension(".avi", color=(74, 222, 128))
        dpg.add_file_extension(".mkv", color=(74, 222, 128))


def tick():
    """Advance hashing and refresh the list while files are being read."""
    if uploads.tick():
        _refresh()
