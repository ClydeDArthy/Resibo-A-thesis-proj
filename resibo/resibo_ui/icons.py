"""Nav rail icons, drawn with primitives so no icon font is needed.

Each screen has a glyph matching its stage of the RESIBO workflow.
"""

import dearpygui.dearpygui as dpg
from . import theme as th

W, H = 36, 32           # icon button size


def _grid(cx, cy, col):
    """Overview: four panes."""
    for dx, dy in ((-5, -5), (3, -5), (-5, 3), (3, 3)):
        dpg.draw_rectangle((cx + dx, cy + dy), (cx + dx + 4, cy + dy + 4),
                           fill=col, color=col)


def _document(cx, cy, col):
    """Case intake: a form with lines."""
    dpg.draw_rectangle((cx - 5, cy - 7), (cx + 5, cy + 7), color=col, thickness=1.2)
    for dy in (-3, 0, 3):
        dpg.draw_line((cx - 2, cy + dy), (cx + 3, cy + dy), color=col, thickness=1.2)


def _film(cx, cy, col):
    """Clips: a film strip."""
    dpg.draw_rectangle((cx - 7, cy - 5), (cx + 7, cy + 5), color=col, thickness=1.2)
    for dx in (-3, 1):
        dpg.draw_line((cx + dx, cy - 5), (cx + dx, cy + 5), color=col, thickness=1.2)


def _copy(cx, cy, col):
    """Working copy: one sheet duplicated."""
    dpg.draw_rectangle((cx - 7, cy - 7), (cx + 2, cy + 3), color=col, thickness=1.2)
    dpg.draw_rectangle((cx - 2, cy - 3), (cx + 7, cy + 7), color=col, thickness=1.2)


def _person(cx, cy, col):
    """People: head and shoulders."""
    dpg.draw_circle((cx, cy - 4), 3.2, color=col, thickness=1.2)
    dpg.draw_line((cx - 5, cy + 6), (cx - 4, cy + 1), color=col, thickness=1.2)
    dpg.draw_line((cx + 5, cy + 6), (cx + 4, cy + 1), color=col, thickness=1.2)
    dpg.draw_line((cx - 4, cy + 1), (cx + 4, cy + 1), color=col, thickness=1.2)


def _face(cx, cy, col):
    """Faces: a face with eyes."""
    dpg.draw_circle((cx, cy), 7, color=col, thickness=1.2)
    dpg.draw_circle((cx - 2.5, cy - 2), 1.1, fill=col, color=col)
    dpg.draw_circle((cx + 2.5, cy - 2), 1.1, fill=col, color=col)
    dpg.draw_line((cx - 3, cy + 3), (cx + 3, cy + 3), color=col, thickness=1.2)


def _face_video(cx, cy, col):
    """Face module: a face inside a video frame."""
    dpg.draw_rectangle((cx - 8, cy - 7), (cx + 8, cy + 7), color=col, thickness=1.2)
    dpg.draw_circle((cx, cy - 1), 3, color=col, thickness=1.2)
    dpg.draw_line((cx - 4, cy + 5), (cx + 4, cy + 5), color=col, thickness=1.2)


def _wave(cx, cy, col):
    """Gait: the ankle-height trace."""
    points = [(cx - 8, cy), (cx - 5, cy - 5), (cx - 2, cy + 4),
              (cx + 1, cy - 5), (cx + 4, cy + 4), (cx + 8, cy)]
    dpg.draw_polyline(points, color=col, thickness=1.4)


def _steps(cx, cy, col):
    """Walking: two footprints."""
    dpg.draw_circle((cx - 4, cy - 3), 2.6, color=col, thickness=1.2)
    dpg.draw_circle((cx + 4, cy + 3), 2.6, color=col, thickness=1.2)
    dpg.draw_line((cx - 4, cy), (cx - 4, cy + 2), color=col, thickness=1.2)
    dpg.draw_line((cx + 4, cy + 6), (cx + 4, cy + 8), color=col, thickness=1.2)


def _chain(cx, cy, col):
    """History: linked records."""
    for dy in (-5, 0, 5):
        dpg.draw_circle((cx - 5, cy + dy), 1.4, fill=col, color=col)
        dpg.draw_line((cx - 1, cy + dy), (cx + 6, cy + dy), color=col, thickness=1.2)


# One drawing function per screen, in nav order.
GLYPHS = [_grid, _document, _copy, _film, _person, _face, _face_video, _steps, _chain]


def draw(drawlist, index, active):
    """Redraw one rail icon in its active or resting colours."""
    dpg.delete_item(drawlist, children_only=True)
    dpg.push_container_stack(drawlist)
    bg = th.GREEN if active else th.BG_CARD
    fg = (10, 16, 13) if active else th.TEXT_DIM
    dpg.draw_rectangle((0, 0), (W, H), fill=bg, color=bg, rounding=5)
    GLYPHS[index](W / 2, H / 2, fg)
    dpg.pop_container_stack()
