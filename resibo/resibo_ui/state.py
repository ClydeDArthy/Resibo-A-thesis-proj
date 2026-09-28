"""Selection state and the helpers that redraw a view after a click.

Each screen keeps its current selection here, so a click can rebuild only the
parts of the view that depend on it.
"""

import dearpygui.dearpygui as dpg

# Current selection per screen, by key.
SEL = {
    "case": 0,         # Overview - which case
    "intake": 2,       # Case intake - which form section
    "exhibit": 0,      # Evidence intake - which exhibit row
    "clip": 2,         # Clips - which segment
    "copy_step": 5,    # Working copy - which preservation step
    "people": 1,       # Person detection - which tracked person
    "people_step": 2,  # Person detection - which pipeline step
    "folder": None,    # Person detection - open identity folder
    "face_step": 2,    # Faces - which face stage
    "face_person": 1,  # Faces - which saved person
    "gait": 1,         # Gait - which person
    "walk": 1,         # Walking - which person
    "stage": -1,       # History - stage filter (-1 = show the whole chain)
    "record": 4,       # History - which audit record
}

# Clickable cards, registered as {item: (callback, user_data)}.
# DearPyGui has no click handler for child windows, so one global mouse
# handler checks which registered card is under the cursor.
_clickable = {}
_double = {}


def rebuild(tag, fill):
    """Clear a container and run `fill` to draw its new contents."""
    if not dpg.does_item_exist(tag):
        return
    dpg.delete_item(tag, children_only=True)
    dpg.push_container_stack(tag)
    try:
        fill()
    finally:
        dpg.pop_container_stack()
    _prune()


def on_click(item, callback, user_data=None):
    """Make a card or tile respond to a left click."""
    _clickable[item] = (callback, user_data)
    return item


def on_double_click(item, callback, user_data=None):
    """Make a card or tile respond to a left double click."""
    _double[item] = (callback, user_data)
    return item


def _prune():
    """Drop registrations whose items were deleted by a rebuild."""
    for item in [i for i in _clickable if not dpg.does_item_exist(i)]:
        del _clickable[item]
    for item in [i for i in _double if not dpg.does_item_exist(i)]:
        del _double[item]


def _hit(registry):
    """The smallest registered item under the cursor, if any."""
    hit, area = None, None
    for item, entry in list(registry.items()):
        if not dpg.does_item_exist(item):
            continue
        if not dpg.is_item_hovered(item):
            continue
        width, height = dpg.get_item_rect_size(item)
        size = width * height
        if area is None or size < area:
            hit, area = (item, entry), size
    return hit


def _dispatch_double(sender, app_data):
    """Fire the double-click callback under the cursor."""
    from . import image_preview, video_preview, viewer
    if viewer.is_open() or image_preview.is_open() or video_preview.is_open():
        return
    hit = _hit(_double)
    if hit:
        item, (callback, user_data) = hit
        callback(item, app_data, user_data)


def _dispatch(sender, app_data):
    """Fire the callback of the smallest registered card under the cursor."""
    from . import folders, image_preview, video_preview, viewer
    x, y = dpg.get_mouse_pos(local=False)
    if viewer.is_open():
        # The preview is on top; a click outside it closes it and stops there.
        if viewer.click_outside(x, y):
            viewer.hide()
        return
    if image_preview.is_open():
        if image_preview.click_outside(x, y):
            image_preview.hide()
        return
    if video_preview.is_open():
        if video_preview.click_outside(x, y):
            video_preview.hide()
        return
    if folders.is_open() and folders.click_outside(x, y):
        folders.hide()
        return

    hit, area = None, None
    for item, entry in list(_clickable.items()):
        if not dpg.does_item_exist(item):
            continue
        if not dpg.is_item_hovered(item):
            continue
        width, height = dpg.get_item_rect_size(item)
        size = width * height
        if area is None or size < area:
            hit, area = (item, entry), size
    if hit:
        item, (callback, user_data) = hit
        callback(item, app_data, user_data)


def refresh_crumb(number):
    """Point the top-bar breadcrumb at the currently selected case."""
    if dpg.does_item_exist("crumb_case"):
        dpg.set_value("crumb_case", number)


def install_handlers():
    """Register the one global mouse handler. Call once, after the context exists."""
    with dpg.handler_registry():
        dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left, callback=_dispatch)
        dpg.add_mouse_double_click_handler(button=dpg.mvMouseButton_Left,
                                           callback=_dispatch_double)
