"""A real frame pulled from a sealed evidence video, shown instead of the mock preview.

Falls back to nothing (the caller keeps the illustrated placeholder) when
OpenCV isn't installed, or the file can't be read.
"""

import os
import dearpygui.dearpygui as dpg

try:
    import cv2
except ImportError:
    cv2 = None

_textures = {}          # (path, fraction) -> (texture_tag, width, height)
_durations = {}


def sealed_path(case_number):
    """The first real video file sealed for this case, if any."""
    from . import db, uploads
    for row in db.evidence_for(case_number):
        if uploads.is_video(row["path"]):
            return row["path"]
    return None


def duration(path):
    """Length of a video in seconds, or 0 if it can't be read."""
    if path in _durations:
        return _durations[path]
    seconds = 0.0
    if cv2 is not None and path and os.path.isfile(path):
        capture = cv2.VideoCapture(path)
        try:
            fps = capture.get(cv2.CAP_PROP_FPS) or 0
            frames = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            seconds = frames / fps if fps > 0 else 0.0
        finally:
            capture.release()
    _durations[path] = seconds
    return seconds


def frame_texture(path, at_fraction=0.0):
    """A DPG texture for one frame of `path`, cached by file and position."""
    if not path:
        return None
    key = (path, round(at_fraction, 3))
    cached = _textures.get(key)
    if cached and dpg.does_item_exist(cached[0]):
        return cached

    if cv2 is None or not os.path.isfile(path):
        return None

    capture = cv2.VideoCapture(path)
    try:
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total > 1:
            capture.set(cv2.CAP_PROP_POS_FRAMES,
                       int(total * min(0.99, max(0.0, at_fraction))))
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok or frame is None:
        return None

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
    height, width = frame.shape[:2]
    data = (frame.astype("float32") / 255.0).ravel().tolist()

    tag = "vid_tex_{}".format(abs(hash(key)))
    with dpg.texture_registry():
        dpg.add_static_texture(width, height, data, tag=tag)
    _textures[key] = (tag, width, height)
    return _textures[key]


def draw(width, height, path, at_fraction=0.0, play_badge=False, subtitle=""):
    """Draw a real frame into a `width` x `height` drawlist; the drawlist's
    item id if it drew one (so the caller can make it clickable), else None."""
    tex = frame_texture(path, at_fraction)
    if not tex:
        return None
    tag, _src_w, _src_h = tex
    from . import widgets
    with dpg.drawlist(width=width, height=height) as dl:
        dpg.draw_image(tag, (0, 0), (width, height))
        if play_badge:
            widgets._draw_play_badge(width / 2, height / 2, r=28)
        if subtitle:
            widgets.draw_subtitle(subtitle, 0, height, width)
    return dl
