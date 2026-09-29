"""Responsive column widths.

Panels register themselves by role; `apply()` recomputes their widths from the
current viewport size, so the centre column always keeps the most space.
"""

import dearpygui.dearpygui as dpg

DEFAULT_W = 1500       # assumed width before the viewport exists
RAIL = 58              # width of the icon rail
GUTTER = 10

# Side panels take a share of the window, within these bounds.
LEFT_SHARE, LEFT_MIN, LEFT_MAX = 0.19, 230, 330
RIGHT_SHARE, RIGHT_MIN, RIGHT_MAX = 0.21, 260, 380

PANE_PAD = 22          # padding inside a centre pane
CARD_PAD = 26          # padding inside a card, plus its scrollbar gutter

_panels = []           # (item, role, scale)
_refills = []          # callbacks that redraw fixed-size art after a resize
_last_width = [0]


def reset():
    """Forget the panels from a previous build of the interface."""
    _panels.clear()
    _refills.clear()
    _last_width[0] = 0


def register(item, role, scale=1.0):
    """Roles: 'left', 'right', or 'centre' (a centre column with a right panel)."""
    _panels.append((item, role, scale))
    return item


def widths():
    """Current left and right panel widths for this window size."""
    try:
        total = dpg.get_viewport_client_width() or DEFAULT_W
    except Exception:            # screens are built before the viewport exists
        total = DEFAULT_W
    left = int(min(LEFT_MAX, max(LEFT_MIN, total * LEFT_SHARE)))
    right = int(min(RIGHT_MAX, max(RIGHT_MIN, total * RIGHT_SHARE)))
    return left, right


def content_width(has_right=True, inset=CARD_PAD):
    """Pixels available for artwork inside a centre pane."""
    try:
        total = dpg.get_viewport_client_width() or DEFAULT_W
    except Exception:
        total = DEFAULT_W
    left, right = widths()
    space = total - RAIL - left - PANE_PAD * 2 - inset
    if has_right:
        space -= right + GUTTER
    return max(360, int(space))


def full_width():
    """Pixels available to a panel that has no rail and no side columns."""
    try:
        total = dpg.get_viewport_client_width() or DEFAULT_W
    except Exception:
        total = DEFAULT_W
    return max(480, int(total - PANE_PAD * 2))


def on_resize(fill):
    """Register a redraw for art that cannot size itself."""
    _refills.append(fill)


def apply(sender=None, app_data=None):
    """Resize every registered panel. Runs at startup and on window resize."""
    left, right = widths()
    for item, role, scale in list(_panels):
        if not dpg.does_item_exist(item):
            continue
        if role == "left":
            dpg.configure_item(item, width=int(left * scale))
        elif role == "right":
            dpg.configure_item(item, width=int(right * scale))
        elif role == "centre":
            # Negative width means "fill, minus this much" - leave room for the
            # right panel so the centre column absorbs the rest.
            dpg.configure_item(item, width=-(int(right * scale) + GUTTER))

    # Drawlists take pixel sizes, so redraw them when the width really changes.
    try:
        total = dpg.get_viewport_client_width() or DEFAULT_W
    except Exception:
        return
    if abs(total - _last_width[0]) > 8:
        _last_width[0] = total
        for fill in _refills:
            fill()
