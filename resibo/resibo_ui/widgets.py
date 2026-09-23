"""Small reusable building blocks shared by every RESIBO screen."""

import dearpygui.dearpygui as dpg
from . import theme as th


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
    with dpg.child_window(width=width, height=96, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as box:
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


def _figure(cx, ground, box_h, look, dim=False):
    """Draw one person: head, hair and torso, tinted by their look."""
    shade = 0.55 if dim else 1.0
    skin = tuple(int(c * shade) for c in look["skin"])
    hair = tuple(int(c * shade) for c in look["hair"])
    shirt = tuple(int(c * shade) for c in look["shirt"])

    head_r = box_h * 0.105 * look["build"]
    head_cy = ground - box_h * 0.80
    body_top = head_cy + head_r * 0.7
    half = box_h * 0.20 * look["build"]

    dpg.draw_ellipse((cx - half, body_top), (cx + half, ground), fill=shirt, color=shirt)
    dpg.draw_circle((cx, head_cy), head_r, fill=skin, color=skin)
    # Hair sits on the upper part of the head.
    if look["hair_style"] == "long":
        dpg.draw_ellipse((cx - head_r, head_cy - head_r),
                         (cx + head_r, head_cy + head_r * 1.5), fill=hair, color=hair)
        dpg.draw_circle((cx, head_cy + head_r * 0.15), head_r * 0.78, fill=skin, color=skin)
    elif look["hair_style"] == "cap":
        dpg.draw_ellipse((cx - head_r * 1.1, head_cy - head_r * 1.1),
                         (cx + head_r * 1.1, head_cy + head_r * 0.1), fill=hair, color=hair)
    else:
        dpg.draw_circle((cx, head_cy - head_r * 0.25), head_r * 0.92, fill=hair, color=hair)


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
            look = (looks or {}).get(label) or _neutral_look(i)

            _figure(x + bw / 2, y + bh, bh, look, dim=(tone != "green"))
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


def _neutral_look(seed=0):
    """Fallback appearance when a person has no entry of their own."""
    palettes = [((168, 124, 96), (44, 32, 26), (78, 92, 104), "short"),
                ((140, 100, 78), (28, 22, 20), (92, 76, 68), "cap"),
                ((198, 160, 130), (96, 72, 40), (66, 84, 78), "long")]
    skin, hair, shirt, style = palettes[seed % len(palettes)]
    return {"skin": skin, "hair": hair, "shirt": shirt,
            "build": 1.0, "height": 1.0, "hair_style": style}


def center_text(value, width, color="text", fnt="ui_sm", char=7.0):
    """Draw text centred in a column of `width` pixels."""
    with dpg.group(horizontal=True):
        pad = int((width - len(value) * char) / 2)
        if pad > 2:
            dpg.add_spacer(width=pad)
        text(value, color, fnt, wrap=-1)


def face_tile(caption, sub, width=195, height=200, blurred=False, selected=False,
              letter="", landmarks=False, bbox=False, look=None, centered=False):
    """Face-analysis thumbnail: a drawn portrait plus its caption."""
    look = look or _neutral_look()
    # Reserve room for the caption (and sub) so neither is clipped. A centred
    # line sits in its own group, which costs about 28 px including spacing.
    sub_lines = 1 if sub else 0
    art_h = max(60, height - 56 - sub_lines * 26)
    with dpg.child_window(width=width, height=height, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as tile:
        w = width - 20
        with dpg.drawlist(width=w, height=art_h):
            fade = 0.72 if blurred else 1.0      # unsharpened crops read flatter
            skin = tuple(int(c * fade) for c in look["skin"])
            hair = tuple(int(c * fade) for c in look["hair"])
            shirt = tuple(int(c * fade) for c in look["shirt"])

            dpg.draw_rectangle((0, 0), (w, art_h), fill=(24, 29, 34), color=(0, 0, 0, 0))
            dpg.draw_ellipse((w * 0.24, art_h * 0.60), (w * 0.76, art_h * 1.32),
                             fill=shirt, color=shirt)                     # shoulders
            head_r = art_h * 0.26 * look["build"]
            cy = art_h * 0.46
            dpg.draw_circle((w / 2, cy), head_r, fill=skin, color=skin)

            if look["hair_style"] == "long":
                dpg.draw_ellipse((w / 2 - head_r, cy - head_r),
                                 (w / 2 + head_r, cy + head_r * 1.35), fill=hair, color=hair)
                dpg.draw_circle((w / 2, cy + head_r * 0.12), head_r * 0.80,
                                fill=skin, color=skin)
            elif look["hair_style"] == "cap":
                dpg.draw_ellipse((w / 2 - head_r * 1.08, cy - head_r * 1.1),
                                 (w / 2 + head_r * 1.08, cy + head_r * 0.05),
                                 fill=hair, color=hair)
            else:
                dpg.draw_circle((w / 2, cy - head_r * 0.28), head_r * 0.92,
                                fill=hair, color=hair)

            if not blurred:                       # the sharpened copy resolves eyes
                for dx in (-head_r * 0.38, head_r * 0.38):
                    dpg.draw_circle((w / 2 + dx, cy + head_r * 0.05), head_r * 0.13,
                                    fill=(238, 240, 242), color=(238, 240, 242))
                    dpg.draw_circle((w / 2 + dx, cy + head_r * 0.05), head_r * 0.06,
                                    fill=(20, 22, 26), color=(20, 22, 26))
            if landmarks:                         # RetinaFace 5-point marks
                for px, py in ((-0.38, 0.05), (0.38, 0.05), (0.0, 0.42),
                               (-0.26, 0.72), (0.26, 0.72)):
                    dpg.draw_circle((w / 2 + head_r * px, cy + head_r * py), 2.5,
                                    fill=th.GREEN, color=th.GREEN)
            if bbox:                              # the detected face box
                dpg.draw_rectangle((w / 2 - head_r * 1.35, cy - head_r * 1.5),
                                   (w / 2 + head_r * 1.35, cy + head_r * 1.25),
                                   color=th.AMBER, thickness=2)
            if letter:
                dpg.draw_rectangle((6, 6), (24, 24), color=th.BORDER, fill=(28, 34, 40))
                dpg.draw_text((11, 6), letter, size=13, color=th.TEXT_DIM)
        spacer(2)
        if centered:
            center_text(caption, w)
            if sub:
                center_text(sub, w, "faint", "mono_sm", char=6.4)
        else:
            text(caption, "text", "ui_sm", wrap=-1)
            if sub:
                text(sub, "faint", "mono_sm", wrap=-1)
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
