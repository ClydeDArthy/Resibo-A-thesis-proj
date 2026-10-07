"""Small reusable building blocks shared by every RESIBO screen."""

import os
import dearpygui.dearpygui as dpg
from . import theme as th

_SILHOUETTE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "images", "person_silhouette.png")
_SILHOUETTE_TAG = "tex_person_silhouette"


def font(tag, name):
    """Bind a named font to an item, if that font loaded."""
    if name in th.F:
        dpg.bind_item_font(tag, th.F[name])
    return tag


def text(value, color="text", fnt="ui", wrap=0):
    """Colored text in one call."""
    t = dpg.add_text(value, wrap=wrap)
    dpg.bind_item_theme(t, th.T["txt_" + color])
    return font(t, fnt)


def mono(value, color="dim", small=False):
    """Monospaced text, used for IDs, hashes, paths and numbers."""
    return text(value, color, "mono_sm" if small else "mono")


def title(value, size="h2"):
    """Section or screen heading."""
    return text(value, "text", size)


def spacer(h=8):
    dpg.add_spacer(height=h)


def divider(pad=6):
    spacer(pad)
    dpg.add_separator()
    spacer(pad)


def pill(label, tone="green"):
    """Read-only status chip, e.g. Done / Running / Queued."""
    b = dpg.add_button(label=label)
    dpg.bind_item_theme(b, th.T["pill_" + tone])
    return font(b, "mono_sm")


def cell_text(value, tone="text"):
    """Table cell text. wrap=-1 so a narrow column clips instead of wrapping."""
    return text(value, tone, "mono_sm", wrap=-1)


def dot(tone="green"):
    """Small status bullet drawn beside a table value."""
    col = {"green": th.GREEN, "amber": th.AMBER, "blue": th.BLUE,
           "red": th.RED}.get(tone, th.TEXT_FAINT)
    with dpg.drawlist(width=14, height=18):
        dpg.draw_circle((5, 10), 3.5, fill=col, color=col)


def pill_width(label):
    """Rough pixel width of a pill, used to size right-hand columns."""
    return len(label) * 8 + 24


def split_row(right_width, col_tag=None):
    """Build a two-column table so one trailing item hugs the right edge.

    Use as: with dpg.table_row(parent=split_row(90)): <left group>; <right group>
    """
    tbl = dpg.add_table(header_row=False, policy=dpg.mvTable_SizingFixedFit,
                        borders_innerH=False, borders_outerH=False,
                        borders_innerV=False, borders_outerV=False)
    dpg.bind_item_theme(tbl, th.T["tight"])
    dpg.push_container_stack(tbl)
    dpg.add_table_column(width_stretch=True, init_width_or_weight=1.0)
    # right_width=0 means "auto-fit to content", which pins the trailing block
    # to the right edge at any window size.
    extra = {"tag": col_tag} if col_tag else {}
    if right_width:
        extra["init_width_or_weight"] = right_width
    dpg.add_table_column(width_fixed=True, **extra)
    dpg.pop_container_stack()
    return tbl


def kv_row(key, value, tone="text", width=300, fnt="mono"):
    """Label on the left, value right-aligned - the detail-panel pattern."""
    with dpg.group():
        with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit,
                       borders_innerV=False, borders_outerV=False,
                       borders_innerH=False, borders_outerH=False) as tbl:
            dpg.add_table_column(width_stretch=True, init_width_or_weight=1.0)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=len(str(value)) * 9 + 8)
            with dpg.table_row():
                text(key, "dim", "ui_sm")
                text(str(value), tone, fnt)
        dpg.bind_item_theme(tbl, th.T["tight"])
    spacer(4)
    dpg.add_separator()
    spacer(4)


def section(label, hint=""):
    """Heading with an optional grey hint beside it, followed by a rule."""
    with dpg.group(horizontal=True):
        title(label)
        if hint:
            dpg.add_spacer(width=12)
            mono(hint, "faint", small=True)
    spacer(4)
    dpg.add_separator()
    spacer(8)


def list_item(name, sub, badge=None, tone="green", selected=False, height=None):
    """Left-rail list entry: name, grey subtitle and a right-aligned status pill.

    Height comes from the content, so the card is always an exact fit.
    """
    box = {"height": height} if height else {"auto_resize_y": True}
    with dpg.child_window(border=True, no_scrollbar=True, no_scroll_with_mouse=True, **box) as item:
        with dpg.table_row(parent=split_row(pill_width(badge) if badge else 1)):
            with dpg.group():
                # wrap=-1 so a long label clips at the column edge rather than
                # wrapping and pushing out of the fixed-height card.
                text(name, "text", "ui", wrap=-1)
                text(sub, "faint", "mono_sm", wrap=-1)
            with dpg.group():
                spacer(4)
                if badge:
                    pill(badge, tone)
    dpg.bind_item_theme(item, th.T["card_sel"] if selected else th.T["card"])
    return item


def step_card(name, sub, badge, tone="green", progress=None, selected=False):
    """Pipeline stage card, optionally with a progress bar underneath."""
    with dpg.child_window(auto_resize_y=True, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as item:
        with dpg.table_row(parent=split_row(pill_width(badge))):
            with dpg.group():
                text(name, "text", "ui", wrap=-1)
                if sub:
                    text(sub, "faint", "mono_sm", wrap=-1)
            with dpg.group():
                spacer(4)
                pill(badge, tone)
        if progress is not None:
            spacer(4)
            bar_tone = {"green": "green", "blue": "blue"}.get(tone, "amber")
            bar = dpg.add_progress_bar(default_value=progress, width=-1, height=4, overlay="")
            dpg.bind_item_theme(bar, th.T["bar_" + bar_tone])
    dpg.bind_item_theme(item, th.T["card_sel"] if selected else th.T["card"])
    return item


def numbered_step(index, name, sub, badge, tone):
    """Overview progress row: circled number, label and status pill."""
    with dpg.child_window(auto_resize_y=True, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as item:
        with dpg.table_row(parent=split_row(pill_width(badge))):
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=36, height=38):
                    col = th.GREEN if tone == "green" else th.BLUE if tone == "blue" else th.TEXT_FAINT
                    dpg.draw_circle((17, 19), 13, color=col, thickness=1.2)
                    dpg.draw_text((13, 11), str(index), size=14, color=col)
                with dpg.group():
                    text(name, "text", "ui", wrap=-1)
                    text(sub, "faint", "mono_sm", wrap=-1)
            with dpg.group():
                spacer(4)
                pill(badge, tone)
    dpg.bind_item_theme(item, th.T["card"])
    return item


def header_row(right_width=1, col_tag=None):
    """Open a screen-header row whose trailing block sits at the right edge."""
    return split_row(right_width, col_tag)


def stat_box(label, value, tone="text", sub="", width=-1, big=True):
    """Metric tile: small grey label, large value, optional caption."""
    height = 96 + (22 if sub else 0)
    with dpg.child_window(width=width, height=height, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as box:
        text(label, "dim", "ui_sm")
        spacer(2)
        text(str(value), tone, "mono_big" if big else "h2")
        if sub:
            mono(sub, "faint", small=True)
    dpg.bind_item_theme(box, th.T["card"])
    return box


def note(heading, body, tone="blue", wrap=880):
    """Callout box for caveats the examiner needs to read.

    Height is derived from the wrapped line count, since an auto-sized child
    window clips wrapped text.
    """
    chars_per_line = max(10, int(wrap / 7.0))       # ~7 px per character at 14 px
    lines = 0
    for paragraph in body.splitlines() or [""]:
        lines += max(1, -(-len(paragraph) // chars_per_line))
    with dpg.child_window(height=46 + lines * 20, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as n:
        text(heading, "blue" if tone == "blue" else "amber", "ui")
        spacer(2)
        text(body, "dim", "ui_sm", wrap=wrap)
    dpg.bind_item_theme(n, th.T["note_" + tone])
    return n


def table(headers, rows, weights=None, highlight=-1, height=0, on_select=None):
    """Read-only table. Cells may be plain values or (value, tone) pairs."""
    with dpg.table(header_row=True, borders_innerH=True, borders_outerH=False,
                   borders_innerV=False, borders_outerV=False,
                   policy=dpg.mvTable_SizingStretchProp, height=height,
                   scrollY=height > 0) as tbl:
        for i, head in enumerate(headers):
            dpg.add_table_column(label=head, init_width_or_weight=(weights[i] if weights else 1))
        for r, row in enumerate(rows):
            with dpg.table_row():
                cells = list(row)
                if on_select is not None:
                    # A selectable spanning every column makes the whole row clickable.
                    first = cells.pop(0)
                    label = first[0] if isinstance(first, tuple) else first
                    sel = dpg.add_selectable(label=str(label), span_columns=True,
                                             default_value=(r == highlight),
                                             callback=on_select, user_data=r)
                    font(sel, "mono")
                for cell in cells:
                    tone, bullet = "text", False
                    if isinstance(cell, tuple):
                        cell, tone, *rest = cell
                        bullet = bool(rest and rest[0])
                    if bullet:
                        with dpg.group(horizontal=True):
                            dot(tone)
                            if cell:
                                cell_text(str(cell), tone)
                    else:
                        cell_text(str(cell), tone)
    if highlight >= 0 and on_select is None:
        dpg.highlight_table_row(tbl, highlight, th.BG_ROW_SEL + (255,))
    return tbl


def _silhouette_texture():
    """The generic person silhouette, loaded once and cached as a texture."""
    if dpg.does_item_exist(_SILHOUETTE_TAG):
        return _SILHOUETTE_TAG
    if not os.path.isfile(_SILHOUETTE_PATH):
        return None
    width, height, _channels, data = dpg.load_image(_SILHOUETTE_PATH)
    with dpg.texture_registry():
        dpg.add_static_texture(width, height, data, tag=_SILHOUETTE_TAG)
    return _SILHOUETTE_TAG


def _figure(cx, ground, box_w, box_h, dim=False):
    """Draw the generic person silhouette, filling its detection box."""
    tex = _silhouette_texture()
    if not tex:
        return
    alpha = 130 if dim else 220
    dpg.draw_image(tex, (cx - box_w / 2, ground - box_h), (cx + box_w / 2, ground),
                   color=(255, 255, 255, alpha))


def video_frame(width, height, cam_label, time_label, boxes=(), corner="", looks=None):
    """Mock CCTV frame.

    `boxes` use fractions of the frame: (fx, fy, fw, fh, label, tone), so the
    drawing always fits whatever size the frame is given.
    """
    with dpg.drawlist(width=width, height=height) as dl:
        dpg.draw_rectangle((0, 0), (width, height), fill=(19, 23, 27), color=th.BORDER)
        if cam_label:
            dpg.draw_text((14, 10), cam_label, size=14, color=th.TEXT_DIM)
        if time_label:
            dpg.draw_text((width - len(time_label) * 8 - 16, 10), time_label,
                          size=14, color=th.TEXT_DIM)
        dpg.draw_line((0, height * 0.66), (width, height * 0.66), color=(28, 34, 40))

        for i, (fx, fy, fw, fh, label, tone) in enumerate(boxes):
            x, y = fx * width, fy * height
            bw, bh = fw * width, fh * height
            col = th.GREEN if tone == "green" else th.AMBER

            _figure(x + bw / 2, y + bh, bw, bh, dim=(tone != "green"))
            dpg.draw_rectangle((x, y), (x + bw, y + bh), color=col, thickness=1.5)

            # Label sits above the box, or inside it when there is no room.
            tw = len(label) * 7 + 12
            ly = y - 17 if y > 20 else y + 2
            dpg.draw_rectangle((x, ly), (x + tw, ly + 15), fill=col, color=col)
            dpg.draw_text((x + 5, ly - 1), label, size=13, color=(10, 14, 12))

            # Face box, proportional to the person box.
            fxw, fxh = bw * 0.40, bh * 0.15
            dpg.draw_rectangle((x + bw / 2 - fxw / 2, y + bh * 0.06),
                               (x + bw / 2 + fxw / 2, y + bh * 0.06 + fxh),
                               color=th.AMBER, thickness=1.3)

        if corner:
            dpg.draw_text((width - len(corner) * 8 - 16, height - 24), corner,
                          size=14, color=th.TEXT_DIM)
    return dl


def center_text(value, width, color="text", fnt="ui_sm", char=7.0):
    """Draw text centred in a column of `width` pixels."""
    if len(value) * char > width:
        text(value, color, fnt, wrap=width)
        return
    with dpg.group(horizontal=True):
        pad = int((width - len(value) * char) / 2)
        if pad > 2:
            dpg.add_spacer(width=pad)
        text(value, color, fnt, wrap=-1)


def face_tile(caption, sub, width=195, height=200, blurred=False, selected=False,
              letter="", landmarks=False, bbox=False, centered=False):
    """Face-analysis thumbnail: the example portrait plus its caption."""
    # Reserve room for the caption (and sub) so neither is clipped. A centred
    # line sits in its own group, which costs about 28 px including spacing.
    sub_lines = -(-int(len(sub) * 7.2) // max(1, width - 20)) if sub else 0
    art_h = max(60, height - 56 - sub_lines * 26)
    with dpg.child_window(width=width, height=height, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as tile:
        w = width - 20
        with dpg.drawlist(width=w, height=art_h):
            dpg.draw_rectangle((0, 0), (w, art_h), fill=(24, 29, 34), color=(0, 0, 0, 0))

            tex = _silhouette_texture()
            if tex:
                img_h = min(art_h * 0.95, w)
                img_w = img_h
                left, top = (w - img_w) / 2, (art_h - img_h) / 2
                alpha = 165 if blurred else 235      # unsharpened crops read flatter
                dpg.draw_image(tex, (left, top), (left + img_w, top + img_h),
                               color=(255, 255, 255, alpha))

                # Measured against the actual silhouette: the head runs from
                # about 6% to 60% of the image height, and about 26% either
                # side of centre.
                cx = left + img_w / 2
                head_top, head_bottom = top + img_h * 0.06, top + img_h * 0.60
                head_cy = (head_top + head_bottom) / 2
                half_h = (head_bottom - head_top) / 2
                half_w = img_w * 0.26

                if landmarks:                         # RetinaFace 5-point marks
                    for px, py in ((-0.55, -0.35), (0.55, -0.35), (0.0, 0.10),
                                   (-0.40, 0.55), (0.40, 0.55)):
                        dpg.draw_circle((cx + half_w * px, head_cy + half_h * py), 2.5,
                                        fill=th.GREEN, color=th.GREEN)
                if bbox:                              # the detected face box
                    dpg.draw_rectangle((cx - half_w, head_top), (cx + half_w, head_bottom),
                                       color=th.AMBER, thickness=2)
            if letter:
                dpg.draw_rectangle((6, 6), (24, 24), color=th.BORDER, fill=(28, 34, 40))
                dpg.draw_text((11, 6), letter, size=13, color=th.TEXT_DIM)
        spacer(2)
        if centered:
            center_text(caption, w)
            if sub:
                center_text(sub, w, "faint", "mono_sm", char=7.2)
        else:
            text(caption, "text", "ui_sm", wrap=-1)
            if sub:
                text(sub, "faint", "mono_sm", wrap=w)
    dpg.bind_item_theme(tile, th.T["card_sel"] if selected else th.T["card"])
    return tile


_IMG_CACHE = {}


def image_texture(path):
    """A cached (tag, width, height) DPG texture for a still image file."""
    cached = _IMG_CACHE.get(path)
    if cached and dpg.does_item_exist(cached[0]):
        return cached
    if not os.path.isfile(path):
        return None
    try:
        width, height, _channels, data = dpg.load_image(path)
    except Exception:
        return None
    tag = "evtex_{}".format(abs(hash(path)))
    with dpg.texture_registry():
        dpg.add_static_texture(width, height, data, tag=tag)
    _IMG_CACHE[path] = (tag, width, height)
    return _IMG_CACHE[path]


def _thumb_texture(path):
    """A real preview (tag, width, height) for an image or video file, else None."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg", ".png"):
        return image_texture(path)
    if ext in (".mp4", ".dav", ".asf"):
        from . import video
        return video.frame_texture(path, 0.0)
    return None


def _is_video_path(path):
    return os.path.splitext(path)[1].lower() in (".mp4", ".dav", ".asf")


def _draw_file_icon(cx, cy, label=""):
    """A generic file icon - a page with a folded corner - labelled by type."""
    w_, h_, fold = 46, 58, 16
    left, top = cx - w_ / 2, cy - h_ / 2
    right, bottom = cx + w_ / 2, cy + h_ / 2
    page = (58, 66, 76)

    dpg.draw_polygon([(left, top), (right - fold, top), (right, top + fold),
                      (right, bottom), (left, bottom)],
                     fill=page, color=th.TEXT_FAINT, thickness=1.3)
    dpg.draw_triangle((right - fold, top), (right, top + fold), (right - fold, top + fold),
                      fill=(40, 46, 52), color=th.TEXT_FAINT, thickness=1.0)

    if label:
        band_h = 18
        dpg.draw_rectangle((left, bottom - band_h), (right, bottom),
                           fill=th.BLUE, color=th.BLUE)
        dpg.draw_text((cx - len(label) * 3.6, bottom - band_h + 3), label,
                      size=13, color=(255, 255, 255, 255))


def _draw_play_badge(cx, cy, r=18):
    """A play-button badge over a video thumbnail, like a media player's."""
    dpg.draw_circle((cx, cy), r, fill=(0, 0, 0, 150), color=(255, 255, 255, 70))
    tw, tall = r * 0.7, r * 0.8
    dpg.draw_triangle((cx - tw * 0.30, cy - tall / 2), (cx - tw * 0.30, cy + tall / 2),
                      (cx + tw * 0.65, cy), fill=(255, 255, 255, 235), color=(255, 255, 255, 235))


def draw_subtitle(value, left, bottom, width, size=16):
    """A centred caption on a dark band along the bottom edge of a frame."""
    band = size + 14
    dpg.draw_rectangle((left, bottom - band), (left + width, bottom),
                       fill=(0, 0, 0, 170), color=(0, 0, 0, 0))
    dpg.draw_text((left + (width - len(value) * size * 0.55) / 2, bottom - band + 6),
                  value, size=size, color=(255, 255, 255, 240))


def evidence_thumb(path, name, width=160, note="", selected=False,
                   on_remove=None, user_data=None):
    """A file-manager-style thumbnail: a perfectly square, unstretched preview,
    with the filename and size/status always fully visible beneath it."""
    art_w = width - 20                  # the image area is a true square
    img_h = art_w
    caption_h = 64                      # room for a name that wraps to two lines, plus note
    height = img_h + caption_h + 16

    with dpg.child_window(width=width, height=height, border=True,
                          no_scrollbar=True, no_scroll_with_mouse=True) as tile:
        if on_remove:
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=width - 42)
                close = dpg.add_button(label="x", width=20, height=20,
                                       callback=on_remove, user_data=user_data)
                dpg.bind_item_theme(close, th.T["btn_ghost"])
        with dpg.drawlist(width=art_w, height=img_h):
            dpg.draw_rectangle((0, 0), (art_w, img_h), fill=(20, 24, 28), color=(0, 0, 0, 0))
            found = _thumb_texture(path)
            if found:
                tag, src_w, src_h = found
                # Fit the real frame inside the square without stretching it.
                scale = min((art_w - 6) / src_w, (img_h - 6) / src_h)
                draw_w, draw_h = src_w * scale, src_h * scale
                left, top = (art_w - draw_w) / 2, (img_h - draw_h) / 2
                dpg.draw_image(tag, (left, top), (left + draw_w, top + draw_h))
                if _is_video_path(path):
                    _draw_play_badge(art_w / 2, img_h / 2)
            else:                                  # generic file icon fallback
                ext = os.path.splitext(path)[1].lstrip(".").upper()
                _draw_file_icon(art_w / 2, img_h / 2, ext)
        spacer(4)
        center_text(name, art_w, "text", "ui_sm", char=6.4)
        if note:
            center_text(note, art_w, "faint", "mono_sm", char=6.0)
    dpg.bind_item_theme(tile, th.T["card_sel"] if selected else th.T["card"])
    return tile


def share(total, count, gap=8):
    """Width of one item when `count` of them share `total` across a row."""
    return max(90, int((total - gap * (count - 1)) / count))


def tile_grid(count, columns, render):
    """Lay out `count` tiles across `columns`, each stretching to fit."""
    with dpg.table(header_row=False, policy=dpg.mvTable_SizingStretchProp,
                   borders_innerH=False, borders_outerH=False,
                   borders_innerV=False, borders_outerV=False) as tbl:
        for _ in range(columns):
            dpg.add_table_column(init_width_or_weight=1.0)
        for start in range(0, count, columns):
            with dpg.table_row():
                for i in range(start, min(start + columns, count)):
                    render(i)
    dpg.bind_item_theme(tbl, th.T["tight"])
    return tbl


def folder_tile(name, sub, tone="green", width=-1, height=None, selected=False):
    """Saved-person folder card used by People, Faces and Walking."""
    box = {"height": height} if height else {"auto_resize_y": True}
    with dpg.child_window(width=width, border=True, no_scrollbar=True, no_scroll_with_mouse=True, **box) as tile:
        col = th.GREEN_DEEP if tone == "green" else th.AMBER
        with dpg.drawlist(width=40, height=26):
            dpg.draw_rectangle((0, 2), (16, 8), fill=col, color=col)
            dpg.draw_rectangle((0, 7), (30, 24), fill=col, color=col)
        text(name, "text", "ui_sm")
        mono(sub, "faint", small=True)
    dpg.bind_item_theme(tile, th.T["card_sel"] if selected else th.T["card"])
    return tile


LANE_LABEL = 100        # label column in front of a presence lane


def track_lane(label, segments, width=620):
    """One person's presence timeline: green where seen, amber where uncertain.

    `width` is the total row width; the bar takes what the label leaves.
    """
    width = max(80, width - LANE_LABEL)
    with dpg.group(horizontal=True):
        text(label, "dim", "mono_sm", wrap=-1)
        dpg.add_spacer(width=max(6, LANE_LABEL - len(label) * 7 - 8))
        with dpg.drawlist(width=width, height=14):
            dpg.draw_rectangle((0, 3), (width, 13), fill=th.BG_CARD_HOVER,
                               color=(0, 0, 0, 0))
            for (start, end, tone) in segments:
                col = th.GREEN_DEEP if tone == "green" else (150, 110, 34)
                dpg.draw_rectangle((width * start, 3), (width * end, 13), fill=col, color=col)


def status_bar(items):
    """Bottom strip of label/value pairs, e.g. Vault and Segment."""
    dpg.add_separator()
    spacer(3)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=14)
        for label, value, tone in items:
            text(label, "faint", "ui_sm")
            dpg.add_spacer(width=4)
            mono(value, tone, small=True)
            dpg.add_spacer(width=22)
