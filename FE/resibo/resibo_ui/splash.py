"""Startup splash: a bouncing R that expands into the case list.

Three phases, driven from the render loop:
  bounce  - the logo bounces while the app settles
  expand  - the logo grows until it fills the window
  reveal  - the green cover fades out, showing the page underneath
"""

import math
import dearpygui.dearpygui as dpg
from . import theme as th

BOUNCE_S = 1.9          # how long the logo bounces
EXPAND_S = 0.45         # logo grows to fill the window
REVEAL_S = 0.50         # green cover fades away
TOTAL_S = BOUNCE_S + EXPAND_S + REVEAL_S

LOGO = 86               # logo square side
PERIOD = 0.62           # one bounce
HOP = 58                # bounce height

_s = {"t": 0.0, "active": False}


def _ease_out(x):
    """Cubic ease-out: fast at first, gentle at the end."""
    return 1 - (1 - x) ** 3


def _size():
    try:
        return dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
    except Exception:
        return 1500, 940


def build():
    """Create the overlay window that floats above the app."""
    with dpg.window(tag="splash", no_title_bar=True, no_resize=True, no_move=True,
                    no_scrollbar=True, no_scroll_with_mouse=True, no_collapse=True, no_close=True,
                    no_bring_to_front_on_focus=False) as win:
        dpg.add_drawlist(tag="splash_draw", width=10, height=10)
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 0))
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
    dpg.bind_item_theme(win, t)
    _s["active"] = True
    _s["t"] = 0.0
    return win


def _ink():
    """Dark or light lettering, whichever reads on the accent."""
    r, g, b = th.ACCENT[:3]
    return (8, 20, 14) if (r * 299 + g * 587 + b * 114) / 1000 > 140 else (250, 252, 250)


def _logo_rect(width, height):
    """Where the logo sits when it is resting on the ground."""
    cx, cy = width / 2, height / 2 - 30
    return cx - LOGO / 2, cy - LOGO / 2


def _draw_bounce(width, height, t):
    """Dark screen, bouncing logo, wordmark and a filling progress line."""
    x0, y0 = _logo_rect(width, height)
    u = (t % PERIOD) / PERIOD
    lift = math.sin(math.pi * u)                   # 0 on the ground, 1 at the top

    # Squash on contact, stretch in the air.
    squash = max(0.0, 1.0 - lift * 5.0)
    sx, sy = 1 + 0.20 * squash, 1 - 0.20 * squash
    w, h = LOGO * sx, LOGO * sy
    cx = x0 + LOGO / 2
    bottom = y0 + LOGO
    top = bottom - h - lift * HOP

    dpg.draw_rectangle((0, 0), (width, height), fill=th.BG_APP, color=th.BG_APP)

    # Shadow shrinks and fades as the logo rises.
    shadow = 1 - lift * 0.55
    tint = tuple(int(c * 0.35) for c in th.ACCENT) + (int(150 * shadow),)
    dpg.draw_ellipse((cx - (LOGO / 2) * shadow, bottom + 12),
                     (cx + (LOGO / 2) * shadow, bottom + 12 + 11 * shadow),
                     fill=tint, color=(0, 0, 0, 0))

    dpg.draw_rectangle((cx - w / 2, top), (cx + w / 2, top + h),
                       fill=th.ACCENT, color=th.ACCENT, rounding=16)
    dpg.draw_text((cx - 16, top + h / 2 - 27), "R", size=54, color=_ink())

    dpg.draw_text((width / 2 - 45, y0 + LOGO + 54), "RESIBO", size=30, color=th.TEXT)
    dpg.draw_text((width / 2 - 85, y0 + LOGO + 94),
                  "Forensic Surveillance Toolkit", size=18, color=th.TEXT_DIM)

    # Progress line under the wordmark.
    bar_w, bar_x = 300, width / 2 - 150
    bar_y = y0 + LOGO + 136
    dpg.draw_line((bar_x, bar_y), (bar_x + bar_w, bar_y), color=(34, 42, 50), thickness=3)
    dpg.draw_line((bar_x, bar_y), (bar_x + bar_w * min(1.0, t / BOUNCE_S), bar_y),
                  color=th.ACCENT, thickness=3)


def _draw_expand(width, height, k):
    """The logo grows from its resting square to the whole window."""
    x0, y0 = _logo_rect(width, height)
    e = _ease_out(k)
    left = x0 * (1 - e)
    top = y0 * (1 - e)
    right = x0 + LOGO + (width - x0 - LOGO) * e
    bottom = y0 + LOGO + (height - y0 - LOGO) * e

    dpg.draw_rectangle((0, 0), (width, height), fill=th.BG_APP, color=th.BG_APP)
    dpg.draw_rectangle((left, top), (right, bottom),
                       fill=th.ACCENT, color=th.ACCENT, rounding=int(16 * (1 - e)))
    if k < 0.45:                                   # the R fades as the square grows
        alpha = int(255 * (1 - k / 0.45))
        cx = (left + right) / 2
        cy = (top + bottom) / 2
        dpg.draw_text((cx - 16, cy - 27), "R", size=54, color=_ink() + (alpha,))


def _draw_reveal(width, height, k):
    """The green cover fades out over the page that is already drawn."""
    alpha = int(255 * (1 - _ease_out(k)))
    if alpha > 0:
        dpg.draw_rectangle((0, 0), (width, height),
                           fill=th.ACCENT + (alpha,), color=(0, 0, 0, 0))


def tick():
    """Advance the animation one frame. Returns True while the splash is up."""
    if not _s["active"]:
        return False

    _s["t"] += dpg.get_delta_time()
    t = _s["t"]
    width, height = _size()

    dpg.configure_item("splash", width=width, height=height, pos=(0, 0))
    dpg.configure_item("splash_draw", width=width, height=height)
    dpg.delete_item("splash_draw", children_only=True)
    dpg.push_container_stack("splash_draw")
    try:
        if t < BOUNCE_S:
            _draw_bounce(width, height, t)
        elif t < BOUNCE_S + EXPAND_S:
            _draw_expand(width, height, (t - BOUNCE_S) / EXPAND_S)
        else:
            _draw_reveal(width, height, min(1.0, (t - BOUNCE_S - EXPAND_S) / REVEAL_S))
    finally:
        dpg.pop_container_stack()

    if t >= TOTAL_S:
        _s["active"] = False
        dpg.delete_item("splash")
    return _s["active"]
