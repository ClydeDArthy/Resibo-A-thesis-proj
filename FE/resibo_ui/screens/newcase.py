"""New case: one panel, filled top to bottom.

The evidence section stays empty until every detail is filled in, and the
case is only created once the evidence is sealed.
"""

import datetime
import os
import dearpygui.dearpygui as dpg

from .. import (actions, data, db, image_preview, layout, theme as th, uploads,
                video_preview, widgets as w)

TITLE = "New case"
CRUMB = ("New case", "Details")
ACTION = None

FORM_W = 940
COL_W = 450

# Every field, in order, with its label and format hint.
FIELDS = [
    ("nc_case_name", "Case name", ""),
    ("nc_case_number", "Case number", ""),
    ("nc_base_dir", "Base directory", ""),
    ("nc_camera", "Camera", ""),
    ("nc_camera_loc", "Camera location", ""),
    ("nc_name", "Examiner name", ""),
    ("nc_phone", "Phone", ""),
    ("nc_email", "Email", ""),
]

CASE_NAME_PREFIX = "CASE - "
PHONE_PREFIX = "+639 - "
CASE_SUFFIX_LEN = 3         # e.g. 09A
PHONE_SUFFIX_LEN = 9        # +639 already covers the leading 9 of "09XXXXXXXXX"


def _case_number_prefix():
    """System-set prefix: CASE-<this year>-, the user only fills in the rest."""
    return "CASE-{}-".format(datetime.date.today().year)


def _clean(sender, allowed=None, max_len=None, upper=False):
    """Filter what the user typed. The prefix itself is a separate, read-only
    label next to the field, so it never appears in the value and can't be
    edited or erased. Returns True if a keystroke had to be rejected."""
    value = dpg.get_value(sender) or ""
    working = value.upper() if upper else value
    rejected = False
    if allowed:
        kept = "".join(ch for ch in working if allowed(ch))
        rejected = len(kept) != len(working)
        working = kept
    if max_len is not None and len(working) > max_len:
        rejected = True
        working = working[:max_len]
    if working != value:
        dpg.set_value(sender, working)
    return rejected


def _on_case_name(sender, app_data=None):
    _clean(sender, upper=True)
    _refresh()


def _on_case_number(sender, app_data=None):
    if _clean(sender, allowed=str.isalnum, max_len=CASE_SUFFIX_LEN, upper=True):
        actions.toast("Case number: letters or numbers only, 3 characters max", "amber")
    _refresh()


def _on_phone(sender, app_data=None):
    if _clean(sender, allowed=str.isdigit, max_len=PHONE_SUFFIX_LEN):
        actions.toast("Phone: numbers only, 9 digits max", "amber")
    _refresh()


# Fields with a fixed, system-set prefix shown as a read-only chip beside the
# box, and the callback that filters what the user types into the rest.
_MASKS = {
    "nc_case_name": (lambda: CASE_NAME_PREFIX, _on_case_name),
    "nc_case_number": (_case_number_prefix, _on_case_number),
    "nc_phone": (lambda: PHONE_PREFIX, _on_phone),
}

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
            masked = _MASKS.get(tag)
            if masked:
                prefix_fn, callback = masked
                prefix_str = prefix_fn()
                chip = dpg.add_text(prefix_str)
                dpg.bind_item_theme(chip, th.T["txt_dim"])
                w.font(chip, "mono")
                chip_w = len(prefix_str) * 9 + 14
                box = dpg.add_input_text(tag=tag, width=max(60, width - chip_w),
                                         hint=hint, callback=callback)
            else:
                box = dpg.add_input_text(tag=tag, width=width, hint=hint,
                                         callback=lambda s, a: _refresh())
            w.font(box, "mono")
            if browse:
                b = dpg.add_button(label="Browse", width=90, callback=actions.browse)
                dpg.bind_item_theme(b, th.T["btn_ghost"])
        if tag == "nc_phone":
            w.text("You may receive notifications from us.", "faint", "ui_sm", wrap=-1)


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


def ingest_directory(path):
    """Queue every supported file found under `path`. Returns how many."""
    added = 0
    for root, _dirs, names in os.walk(path):
        for name in sorted(names):
            full = os.path.join(root, name)
            if uploads.is_allowed(full) and uploads.add(full):
                added += 1
    return added


def _pick_files(sender=None, app_data=None, user_data=None):
    """Native picker for evidence files; queue whatever comes back."""
    paths = actions.pick_evidence_files()
    rejected = 0
    for path in paths:
        if not uploads.is_allowed(path):
            rejected += 1
            continue
        uploads.add(path)
    if rejected:
        actions.toast("{} file(s) skipped - only JPEG, MP4, DAV or ASF are allowed"
                      .format(rejected), "amber")
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
        "number": _case_number_prefix() + dpg.get_value("nc_case_number").strip(),
        "place": dpg.get_value("nc_camera_loc").strip(),
        "badge": "Active", "tone": "green",
        "name": CASE_NAME_PREFIX + dpg.get_value("nc_case_name").strip(),
        "opened": datetime.date.today().isoformat(),
        "exhibits": count, "flags": 0, "chain": "verified",
        "status": "Ready", "done": 0,
        "base_dir": dpg.get_value("nc_base_dir").strip(),
    }
    db.insert_case(case)
    db.insert_evidence(case["number"], uploads.FILES)
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
    w.text("Double-click a file to preview it.", "faint", "ui_sm", wrap=-1)
    w.spacer(8)

    THUMBS_PER_ROW = 4
    thumb_w = w.share(FORM_W - 40, THUMBS_PER_ROW)
    w.tile_grid(len(uploads.FILES), THUMBS_PER_ROW,
               lambda i: _file_thumb(i, uploads.FILES[i], thumb_w))


def _file_thumb(index, entry, width):
    """One file as a real thumbnail: image or video frame, name and status."""
    reading = entry["state"] == "reading"
    if entry["state"] == "error":
        note = "could not be read"
    elif reading:
        note = "hashing {:.0f}%".format(uploads.progress(entry) * 100)
    else:
        note = uploads.size_text(entry["size"])

    tile = w.evidence_thumb(entry["path"], entry["name"], width=width,
                            note=note, on_remove=_drop_file, user_data=index)
    if not reading:
        from .. import state
        path = entry["path"]
        if uploads.is_video(path):
            state.on_double_click(tile, lambda s, a, u: video_preview.open_video_preview(path))
        elif os.path.splitext(path)[1].lower() in (".jpg", ".jpeg", ".png"):
            state.on_double_click(tile, lambda s, a, u: image_preview.show(path))


def tick():
    """Advance hashing and refresh the list while files are being read."""
    if uploads.tick():
        _refresh()
