"""What the header buttons, Browse and Export actually do."""

import json
import os
import dearpygui.dearpygui as dpg

from . import data, state, theme as th

# app.run() fills this in; it avoids importing app here and creating a cycle.
_navigate = [None]
_toast_frames = [0]


def set_navigator(fn):
    """Give the actions a way to switch screens."""
    _navigate[0] = fn


def toast(message, tone="green"):
    """Show a short confirmation in the top bar for a couple of seconds."""
    if not dpg.does_item_exist("toast"):
        return
    dpg.set_value("toast", message)
    dpg.bind_item_theme("toast", th.T["txt_" + tone])
    _toast_frames[0] = 140                  # roughly two seconds at 60 fps


def tick():
    """Fade the toast out. Called once per frame."""
    if _toast_frames[0] > 0:
        _toast_frames[0] -= 1
        if _toast_frames[0] == 0 and dpg.does_item_exist("toast"):
            dpg.set_value("toast", "")


# --- Navigation -----------------------------------------------------------

def next_screen(sender=None, app_data=None, user_data=None):
    """Advance the workflow one step down the nav rail."""
    if _navigate[0]:
        _navigate[0]("next")


# --- File dialogs ---------------------------------------------------------

def _picked_dir(sender, app_data):
    """Write the chosen folder back into the new-case base directory field."""
    path = app_data.get("file_path_name") or app_data.get("current_path", "")
    if path and dpg.does_item_exist("nc_base_dir"):
        dpg.set_value("nc_base_dir", path.replace("\\", "/"))
        toast("Base directory set")
        from .screens import newcase
        newcase._refresh()


def browse(sender=None, app_data=None, user_data=None):
    """Open a folder picker for the evidence base directory."""
    dpg.show_item("dlg_browse")


def _picked_export(sender, app_data):
    """Write the audit chain to the chosen file."""
    path = app_data.get("file_path_name")
    if not path:
        return
    if not path.lower().endswith(".json"):
        path += ".json"
    case = data.CASES[state.SEL["case"]]
    report = {
        "case": case["number"],
        "name": case["name"],
        "examiner": data.EXAMINER["full_name"],
        "vault": data.VAULT,
        "segment": data.SEGMENT,
        "chain_length": data.HISTORY_STATS[0][1],
        "records": [
            {"record": r, "time": t, "stage": s, "action": a, "linked": ln == "Yes"}
            for r, t, s, a, ln in data.HISTORY_RECORDS
        ],
    }
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        toast("Exported to " + os.path.basename(path))
    except OSError as err:
        toast("Export failed: {}".format(err), "amber")


def case_complete():
    """True when every workflow step of the open case has finished."""
    case = data.CASES[state.SEL["case"]]
    return case["done"] >= len(data.STEPS)


def export(sender=None, app_data=None, user_data=None):
    """Open a save dialog for the audit trail, once the case is finished."""
    if not case_complete():
        case = data.CASES[state.SEL["case"]]
        toast("Cannot export yet - {} of {} steps done".format(
            case["done"], len(data.STEPS)), "amber")
        return
    dpg.show_item("dlg_export")


def build_dialogs():
    """Create the file dialogs once, hidden, at startup."""
    dpg.add_file_dialog(tag="dlg_browse", label="Select evidence base directory",
                        directory_selector=True, show=False, modal=True,
                        width=720, height=460, callback=_picked_dir)

    with dpg.file_dialog(tag="dlg_export", label="Export audit trail",
                         directory_selector=False, show=False, modal=True,
                         default_filename="audit_trail", width=720, height=460,
                         callback=_picked_export):
        dpg.add_file_extension(".json", color=(74, 222, 128))


# Header buttons, looked up by the label the screen declares.
PRIMARY = {
    "Continue": next_screen,
    "Export": export,
}
SECONDARY = {}
