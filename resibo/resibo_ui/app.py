"""Application shell.

Two stages: a full-window landing where a case is chosen, then the case
workspace with the nav rail and the stage screens.
"""

import dearpygui.dearpygui as dpg

from . import (actions, data, db, folders, icons, image_preview, layout, player,
               scrim, settings, splash, state, theme as th, viewer, widgets as w)
from .screens import (picker, newcase, progress, evidence, working_copy,
                      clips, people, faces, walking, history)

# Workspace screens, in nav-rail order. Progress is the case home.
SCREENS = [progress, evidence, working_copy, clips, people, faces, walking, history]

VIEWPORT_W, VIEWPORT_H = 1500, 940
_nav_icons = []
_current = 0


def _screen_index(name):
    """Find a screen by its TITLE, which is how progress steps refer to it."""
    for i, screen in enumerate(SCREENS):
        if screen.TITLE == name:
            return i
    return 0


def _select(index):
    """Show one workspace screen and refresh the top bar."""
    global _current
    if index == "next":
        index = min(_current + 1, len(SCREENS) - 1)
    elif isinstance(index, str):
        index = _screen_index(index)
    _current = index

    for i in range(len(SCREENS)):
        dpg.configure_item(f"screen_{i}", show=(i == index))
        icons.draw(_nav_icons[i], i, active=(i == index))

    active = SCREENS[index]
    dpg.set_value("crumb_case", data.CASES[state.SEL["case"]]["number"])
    dpg.set_value("crumb_page", active.CRUMB[1])

    primary, secondary = (active.ACTION or (None, None))
    dpg.configure_item("act_primary", show=bool(primary), label=primary or "",
                       callback=actions.PRIMARY.get(primary))
    if primary == "Export":
        # Greyed out until the workflow has actually finished.
        dpg.bind_item_theme("act_primary", th.T["btn_primary"]
                            if actions.case_complete() else th.T["btn_ghost"])
    dpg.configure_item("act_secondary", show=bool(secondary), label=secondary or "",
                       callback=actions.SECONDARY.get(secondary))


def open_case(index):
    """Leave the picker and open the workspace for one case."""
    state.SEL["case"] = index
    dpg.configure_item("picker", show=False)
    dpg.configure_item("newcase", show=False)
    dpg.configure_item("act_delete", show=False)
    dpg.configure_item("workspace", show=True)
    dpg.configure_item("nav_rail", show=True)
    dpg.configure_item("examiner_block", show=True)
    dpg.configure_item("vault_line", show=True)
    dpg.set_value("examiner_name", data.CASES[index].get("examiner", "-"))
    progress.refresh()
    evidence.refresh()
    clips.refresh()
    history.refresh()
    _select(0)
    actions.toast("Opened " + data.CASES[index]["number"])


def start_new_case():
    """Open the blank new-case panel."""
    dpg.configure_item("picker", show=False)
    dpg.configure_item("workspace", show=False)
    dpg.configure_item("nav_rail", show=False)
    dpg.configure_item("newcase", show=True)
    dpg.configure_item("act_delete", show=False)
    dpg.configure_item("vault_line", show=False)
    for tag in ("act_primary", "act_secondary", "examiner_block"):
        dpg.configure_item(tag, show=False)
    dpg.set_value("crumb_case", "New case")
    dpg.set_value("crumb_page", "Details")
    newcase.reset()


def back_to_cases(sender=None, app_data=None, user_data=None):
    """Return to the case picker."""
    viewer.hide()
    image_preview.hide()
    folders.hide()
    scrim.hide()
    dpg.configure_item("workspace", show=False)
    dpg.configure_item("newcase", show=False)
    dpg.configure_item("nav_rail", show=False)
    dpg.configure_item("picker", show=True)
    for tag in ("act_primary", "act_secondary", "examiner_block",
                "act_delete", "vault_line"):
        dpg.configure_item(tag, show=False)
    dpg.set_value("crumb_case", "Cases")
    dpg.set_value("crumb_page", "Select a case")
    picker.clear_selection()


def _on_pick(index):
    """Show the delete button only while a case is highlighted."""
    dpg.configure_item("act_delete", show=index is not None)


def _ask_delete(sender=None, app_data=None, user_data=None):
    """Confirm before removing a case from the vault list."""
    index = picker.selected()
    if index is None:
        return
    dpg.set_value("confirm_text", "Remove {} from the case list?".format(
        data.CASES[index]["number"]))
    try:
        width = dpg.get_viewport_client_width()
        height = dpg.get_viewport_client_height()
    except Exception:
        width, height = 1500, 940
    scrim.show()
    dpg.configure_item("confirm_delete", show=True,
                       pos=((width - CONFIRM_W) // 2, (height - CONFIRM_H) // 2))
    dpg.focus_item("confirm_delete")


def _do_delete(sender=None, app_data=None, user_data=None):
    index = picker.selected()
    scrim.hide()
    if index is None:                     # the selection went away meanwhile
        dpg.configure_item("confirm_delete", show=False)
        return
    number = data.CASES[index]["number"]
    db.delete_case(number)
    del data.CASES[index]
    state.SEL["case"] = min(state.SEL["case"], max(0, len(data.CASES) - 1))
    dpg.configure_item("confirm_delete", show=False)
    picker.clear_selection()
    actions.toast("Deleted " + number, "amber")


def _cancel_delete(sender=None, app_data=None, user_data=None):
    scrim.hide()
    dpg.configure_item("confirm_delete", show=False)


CONFIRM_W, CONFIRM_H = 460, 230


def _confirm_dialog():
    """Fixed, centred confirmation shown before a case is removed."""
    with dpg.window(tag="confirm_delete", modal=True, show=False, no_resize=True,
                    no_move=True, no_title_bar=True, no_collapse=True,
                    no_scrollbar=True, no_scroll_with_mouse=True,
                    width=CONFIRM_W, height=CONFIRM_H) as win:
        dpg.add_spacer(height=4)
        w.text("Delete case", "red", "h2", wrap=-1)
        w.spacer(10)
        w.font(dpg.add_text("", tag="confirm_text"), "ui")
        w.spacer(6)
        w.text("The case and its progress are removed from this list.",
               "dim", "ui_sm", wrap=CONFIRM_W - 60)
        w.spacer(24)
        with dpg.table_row(parent=w.split_row(0)):
            dpg.add_spacer(width=1)
            with dpg.group(horizontal=True):
                cancel = dpg.add_button(label="Cancel", width=130, callback=_cancel_delete)
                dpg.bind_item_theme(cancel, th.T["btn_ghost"])
                dpg.add_spacer(width=10)
                confirm = dpg.add_button(label="Delete", width=130, callback=_do_delete)
                dpg.bind_item_theme(confirm, th.T["btn_danger"])
    dpg.bind_item_theme(win, th.T["panel"])


def _nav_rail():
    """Thin left rail: logo plus one icon per workspace screen."""
    with dpg.child_window(tag="nav_rail", width=layout.RAIL, border=False,
                          show=False) as rail:
        dpg.add_spacer(height=14)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=11)
            # The logo doubles as the home button.
            logo = dpg.add_button(label="R", width=36, height=36,
                                  callback=back_to_cases)
            dpg.bind_item_theme(logo, th.T["pill_green"])
            with dpg.tooltip(logo):
                w.text("Back to cases", "text", "ui_sm", wrap=-1)
        dpg.add_spacer(height=16)
        for i in range(len(SCREENS)):
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=11)
                # A borderless cell hosts the icon: a drawlist cannot carry a
                # tooltip or report hover on its own.
                with dpg.child_window(width=icons.W, height=icons.H, border=False,
                                      no_scrollbar=True, no_scroll_with_mouse=True) as cell:
                    _nav_icons.append(dpg.add_drawlist(width=icons.W, height=icons.H))
                dpg.bind_item_theme(cell, th.T["bare"])
                state.on_click(cell, lambda s, a, u: _select(u), i)
            dpg.add_spacer(height=7)
    dpg.bind_item_theme(rail, th.T["panel"])


def _top_bar():
    """Product name, breadcrumb and the per-screen action buttons."""
    with dpg.child_window(height=84, border=True, no_scrollbar=True,
                          no_scroll_with_mouse=True) as bar:
        with dpg.table_row(parent=w.split_row(0, "topbar_col")):
            with dpg.group(horizontal=True):
                w.font(dpg.add_text("RESIBO"), "h2")
                dpg.add_spacer(width=18)
                with dpg.group():
                    with dpg.group(horizontal=True):
                        w.font(dpg.add_text("Cases", tag="crumb_case"), "ui")
                        w.text("/", "faint", "ui")
                        crumb = dpg.add_text("Select a case", tag="crumb_page")
                        dpg.bind_item_theme(crumb, th.T["txt_dim"])
                        w.font(crumb, "ui")
                        dpg.add_spacer(width=24)
                        # Confirmation messages appear here and clear themselves.
                        w.font(dpg.add_text("", tag="toast"), "ui_sm")
                    # Where the evidence lives, kept with the case it belongs to.
                    with dpg.group(horizontal=True, tag="vault_line", show=False):
                        w.text("Vault", "faint", "ui_sm", wrap=-1)
                        w.text(data.VAULT, "dim", "mono_sm", wrap=-1)
                        dpg.add_spacer(width=16)
                        w.text("Segment", "faint", "ui_sm", wrap=-1)
                        w.text(data.SEGMENT, "dim", "mono_sm", wrap=-1)
            with dpg.group(horizontal=True):
                with dpg.group(tag="examiner_block", show=False):
                    w.text("Examiner", "dim", "ui_sm")
                    w.font(dpg.add_text("", tag="examiner_name"), "mono_sm")
                dpg.add_spacer(width=14)
                delete = dpg.add_button(label="Delete case", tag="act_delete",
                                        show=False, callback=_ask_delete)
                dpg.bind_item_theme(delete, th.T["btn_danger"])
                dpg.add_spacer(width=8)
                sec = dpg.add_button(label="", tag="act_secondary", show=False)
                dpg.bind_item_theme(sec, th.T["btn_ghost"])
                dpg.add_spacer(width=8)
                pri = dpg.add_button(label="", tag="act_primary", show=False)
                dpg.bind_item_theme(pri, th.T["btn_primary"])
    dpg.bind_item_theme(bar, th.T["panel"])


def _build_stages():
    """Build the rail, the header and the three stages into the primary window."""
    _nav_icons.clear()
    layout.reset()
    with dpg.group(horizontal=True):
        _nav_rail()
        with dpg.group():
            _top_bar()
            # Stage one: the case picker, full window, no rail.
            with dpg.child_window(tag="picker", width=-1, height=-1, border=False):
                picker.build()
            # Stage two: manual intake for a brand new case.
            with dpg.child_window(tag="newcase", width=-1, height=-1,
                                  border=False, show=False):
                newcase.build()
            # Stage three: the case workspace.
            with dpg.child_window(tag="workspace", width=-1, height=-1,
                                  border=False, show=False):
                for i, screen in enumerate(SCREENS):
                    with dpg.child_window(tag=f"screen_{i}", width=-1, height=-1,
                                          border=False, show=False):
                        screen.build()


def set_theme(name):
    """Switch palette and rebuild the interface with the new colours."""
    if name == th.CURRENT[0]:
        return
    th.set_palette(name)
    th.build_themes()
    settings.save(theme=name)

    # Themes are baked into every item, so the interface is rebuilt.
    viewer.hide()
    image_preview.hide()
    folders.hide()
    scrim.hide()
    for tag in ("viewer", "image_preview", "folder_win",
                "confirm_delete", "dlg_export", "ev_remove_confirm", "scrim"):
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
    dpg.delete_item("primary", children_only=True)

    actions.build_dialogs()
    scrim.build()
    _confirm_dialog()
    evidence.build_dialog()
    viewer.build()
    image_preview.build()
    folders.build()

    dpg.push_container_stack("primary")
    _build_stages()
    dpg.pop_container_stack()

    dpg.set_viewport_clear_color(th.BG_APP + (255,))
    layout.apply()
    back_to_cases()
    actions.toast(name + " theme")


def run():
    """Create the window, build both stages, then start the render loop."""
    dpg.create_context()
    th.set_palette(settings.load()["theme"])
    th.build_themes()
    state.install_handlers()
    actions.set_navigator(_select)
    actions.build_dialogs()
    picker.set_handlers(open_case, start_new_case, _on_pick, set_theme)
    newcase.set_handler(open_case, back_to_cases)
    scrim.build()
    _confirm_dialog()
    evidence.build_dialog()
    viewer.build()
    image_preview.build()
    folders.build()
    history.install_clock()
    progress.set_opener(_select)

    with dpg.window(tag="primary"):
        _build_stages()

    dpg.create_viewport(title="RESIBO - Forensic Surveillance Toolkit",
                        width=VIEWPORT_W, height=VIEWPORT_H,
                        min_width=1280, min_height=760,
                        clear_color=th.BG_APP + (255,))
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("primary", True)
    dpg.maximize_viewport()
    dpg.set_viewport_resize_callback(layout.apply)
    layout.apply()
    splash.build()          # covers the window until the intro finishes

    # Manual loop so the scrub bars and toasts can update each frame.
    while dpg.is_dearpygui_running():
        splash.tick()
        if dpg.get_item_configuration("picker")["show"]:
            picker.tick()
        elif dpg.get_item_configuration("newcase")["show"]:
            newcase.tick()
        if SCREENS[_current] is history and dpg.get_item_configuration("workspace")["show"]:
            history.tick()
        player.tick()
        actions.tick()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()
