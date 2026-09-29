import logging
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

import dearpygui.dearpygui as dpg

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import imageio_ffmpeg
    _FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FFMPEG_EXE = None

from . import theme as th, widgets as w

WIN_W, WIN_H = 900, 700
ART_W, ART_H = WIN_W - 40, WIN_H - 100

_log = logging.getLogger("resibo.audit")
_audit_hook = [None]
_open = [False]
_next_tex_id = [0]
_audio_cache = {}        # path -> extracted wav path, or None if it has no audio

_session = {
    "path": None, "thread": None, "stop": None, "pause": None, "queue": None,
    "texture": None, "tex_w": 0, "tex_h": 0, "finished": False, "audio": None,
}


def set_audit_hook(fn):
    _audit_hook[0] = fn


class _AudioPlayer:
    """Plays a decoded WAV through PortAudio, gated by the same pause/stop
    events the video reader uses, so both freeze and resume together."""

    def __init__(self, data, samplerate, start_frame, pause_event, stop_event):
        self.data = data
        self.pos = min(start_frame, len(data))
        self.pause_event = pause_event
        self.stop_event = stop_event
        self.stream = sd.OutputStream(samplerate=samplerate, channels=data.shape[1],
                                      dtype="float32", callback=self._callback)

    def _callback(self, outdata, frames, time_info, status):
        if self.stop_event.is_set() or not self.pause_event.is_set():
            outdata.fill(0)
            return
        n = max(0, min(frames, len(self.data) - self.pos))
        if n:
            outdata[:n] = self.data[self.pos:self.pos + n]
        if n < frames:
            outdata[n:].fill(0)
        self.pos += n

    def start(self):
        self.stream.start()

    def close(self):
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass


def _safe_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _extract_audio(path, stop_event):
    """Decodes the clip's audio track to a temp WAV via a bundled ffmpeg binary.
    Cached per path; interrupted or unavailable extraction returns None
    without caching, so a later attempt can retry."""
    if sf is None or sd is None or not _FFMPEG_EXE:
        return None
    if path in _audio_cache:
        cached = _audio_cache[path]
        if not cached or os.path.isfile(cached):
            return cached

    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="resibo_vid_audio_")
    os.close(fd)
    cmd = [_FFMPEG_EXE, "-y", "-i", path, "-vn", "-ac", "2", "-ar", "44100", "-f", "wav", wav_path]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=flags)
    except OSError:
        _safe_remove(wav_path)
        return None

    started = time.monotonic()
    while proc.poll() is None:
        if stop_event.is_set() or time.monotonic() - started > 60:
            proc.kill()
            proc.wait(timeout=5)
            _safe_remove(wav_path)
            return None
        time.sleep(0.1)

    if proc.returncode != 0:
        _safe_remove(wav_path)
        wav_path = None
    _audio_cache[path] = wav_path
    return wav_path


def _start_audio(wav_path, play_start):
    """Loads the extracted WAV and starts it at the point the video has
    already reached, so a slow extraction doesn't leave audio behind."""
    if sd is None or sf is None:
        return
    pause_event, stop_event = _session["pause"], _session["stop"]
    if pause_event is None or stop_event is None or stop_event.is_set():
        return
    try:
        data, samplerate = sf.read(wav_path, dtype="float32", always_2d=True)
        start_frame = int(max(0.0, time.monotonic() - play_start) * samplerate)
        player = _AudioPlayer(data, samplerate, start_frame, pause_event, stop_event)
        player.start()
    except Exception:
        return
    _session["audio"] = player


class _Reader(threading.Thread):
    def __init__(self, path, frame_q, stop_event, pause_event):
        super().__init__(daemon=True)
        self.path = path
        self.frame_q = frame_q
        self.stop_event = stop_event
        self.pause_event = pause_event      # set() == playing
        self.play_start = 0.0
        self.audio_thread = None

    def run(self):
        capture = cv2.VideoCapture(self.path)   # read-only handle, never written back
        try:
            if not capture.isOpened():
                self._post("error", None)
                return
            fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
            interval = 1.0 / fps if fps > 1 else 1.0 / 25.0

            ok, frame = capture.read()
            if not ok or frame is None:
                self._post("error", None)
                return
            height, width = frame.shape[:2]
            if not self._post("meta", (width, height)):
                return
            if not self._post("frame", _to_texture_data(frame)):
                return

            self.play_start = time.monotonic()
            self.audio_thread = threading.Thread(target=self._load_audio, daemon=True)
            self.audio_thread.start()

            next_due = self.play_start + interval
            while not self.stop_event.is_set():
                if not self.pause_event.is_set():
                    time.sleep(0.05)
                    next_due = time.monotonic() + interval
                    continue
                now = time.monotonic()
                if now < next_due:
                    time.sleep(min(0.01, next_due - now))
                    continue
                ok, frame = capture.read()
                if not ok or frame is None:
                    self._post("done", None)
                    break
                if not self._post("frame", _to_texture_data(frame)):
                    break
                next_due += interval
        finally:
            capture.release()

    def _load_audio(self):
        wav_path = _extract_audio(self.path, self.stop_event)
        if wav_path and not self.stop_event.is_set():
            self._post("audio", (wav_path, self.play_start))

    def _post(self, kind, payload):
        """Retries on a full queue; gives up once stop_event is set."""
        while not self.stop_event.is_set():
            try:
                self.frame_q.put((kind, payload), timeout=0.2)
                return True
            except queue.Full:
                continue
        return False


def _to_texture_data(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
    return (frame.astype("float32") / 255.0).ravel()


def build():
    with dpg.window(tag="video_preview", show=False, no_title_bar=True, no_resize=True,
                    no_move=True, no_collapse=True, no_scrollbar=True,
                    width=WIN_W, height=WIN_H, on_close=hide) as win:
        with dpg.table_row(parent=w.split_row(0)):
            w.font(dpg.add_text("", tag="vidprev_title"), "h2")
            toggle = dpg.add_button(label="Pause", width=90, tag="vidprev_toggle",
                                    callback=_toggle)
            dpg.bind_item_theme(toggle, th.T["btn_ghost"])
            close = dpg.add_button(label="X", width=36, height=30, callback=hide)
            dpg.bind_item_theme(close, th.T["btn_ghost"])
        w.spacer(10)
        dpg.add_drawlist(tag="vidprev_art", width=ART_W, height=ART_H)
    dpg.bind_item_theme(win, th.T["panel"])


def open_video_preview(path):
    if not path or not os.path.isfile(path):
        return
    _stop_reader()
    dpg.set_value("vidprev_title", os.path.basename(path))
    dpg.configure_item("vidprev_toggle", label="Pause", enabled=cv2 is not None)
    dpg.delete_item("vidprev_art", children_only=True)
    _session.update(path=path, texture=None, tex_w=0, tex_h=0, finished=False)

    if cv2 is None:
        w.font(dpg.add_text("OpenCV is not installed - can't play video here.",
                            parent="vidprev_art"), "ui_sm")
    else:
        stop_event = threading.Event()
        pause_event = threading.Event()
        pause_event.set()
        frame_q = queue.Queue(maxsize=3)
        reader = _Reader(path, frame_q, stop_event, pause_event)
        _session.update(thread=reader, stop=stop_event, pause=pause_event, queue=frame_q)
        reader.start()

    width, height = _viewport()
    dpg.configure_item("video_preview", show=True,
                       pos=((width - WIN_W) // 2, max(20, (height - WIN_H) // 2)))
    dpg.focus_item("video_preview")
    _open[0] = True

    if _audit_hook[0]:
        _audit_hook[0](path)
    else:
        _log.info("video previewed user=%s file=%s time=%s",
                  os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
                  os.path.basename(path), time.strftime("%Y-%m-%d %H:%M:%S"))


show = open_video_preview


def hide(sender=None, app_data=None, user_data=None):
    _stop_reader()
    if dpg.does_item_exist("video_preview"):
        dpg.configure_item("video_preview", show=False)
    _open[0] = False


def cleanup():
    """Delete cached extracted-audio temp files. Call once at app shutdown."""
    for wav_path in list(_audio_cache.values()):
        if wav_path:
            _safe_remove(wav_path)
    _audio_cache.clear()


def is_open():
    return _open[0]


def click_outside(mouse_x, mouse_y):
    if not _open[0]:
        return False
    x, y = dpg.get_item_pos("video_preview")
    return not (x <= mouse_x <= x + WIN_W and y <= mouse_y <= y + WIN_H)


def tick():
    """Call once per render frame."""
    if not _open[0]:
        return
    frame_q = _session["queue"]
    if frame_q is None:
        return

    latest_frame = None
    try:
        while True:
            kind, payload = frame_q.get_nowait()
            if kind == "meta":
                _make_texture(*payload)
            elif kind == "frame":
                latest_frame = payload
            elif kind == "audio":
                _start_audio(*payload)
            elif kind == "error":
                _session["finished"] = True
                dpg.delete_item("vidprev_art", children_only=True)
                w.font(dpg.add_text("Could not read this video file.",
                                    parent="vidprev_art"), "ui_sm")
            elif kind == "done":
                _session["finished"] = True
                if dpg.does_item_exist("vidprev_toggle"):
                    dpg.configure_item("vidprev_toggle", label="Replay")
    except queue.Empty:
        pass

    if latest_frame is not None and _session["texture"] and \
            dpg.does_item_exist(_session["texture"]):
        dpg.set_value(_session["texture"], latest_frame)


def _make_texture(width, height):
    if _session["texture"] and dpg.does_item_exist(_session["texture"]):
        dpg.delete_item(_session["texture"])
    _next_tex_id[0] += 1
    tag = "vidprev_tex_{}".format(_next_tex_id[0])
    blank = [0.0] * (width * height * 4)
    with dpg.texture_registry():
        dpg.add_dynamic_texture(width, height, blank, tag=tag)
    _session["texture"], _session["tex_w"], _session["tex_h"] = tag, width, height
    _draw_frame(tag, width, height)


def _draw_frame(tag, tex_w, tex_h):
    scale = min(ART_W / tex_w, ART_H / tex_h)
    draw_w, draw_h = tex_w * scale, tex_h * scale
    left, top = (ART_W - draw_w) / 2, (ART_H - draw_h) / 2
    dpg.delete_item("vidprev_art", children_only=True)
    dpg.push_container_stack("vidprev_art")
    dpg.draw_image(tag, (left, top), (left + draw_w, top + draw_h))
    dpg.pop_container_stack()


def _toggle(sender=None, app_data=None, user_data=None):
    if _session["finished"]:
        open_video_preview(_session["path"])
        return
    pause_event = _session["pause"]
    if pause_event is None:
        return
    if pause_event.is_set():
        pause_event.clear()
        dpg.configure_item("vidprev_toggle", label="Play")
    else:
        pause_event.set()
        dpg.configure_item("vidprev_toggle", label="Pause")


def _stop_reader():
    stop_event = _session["stop"]
    reader = _session["thread"]
    if stop_event:
        stop_event.set()
    if reader and reader.is_alive():
        reader.join(timeout=2.0)
    audio_thread = reader.audio_thread if reader else None
    if audio_thread and audio_thread.is_alive():
        audio_thread.join(timeout=1.0)
    audio = _session["audio"]
    if audio:
        audio.close()
    _session.update(thread=None, stop=None, pause=None, queue=None, audio=None)


def _viewport():
    try:
        return dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
    except Exception:
        return 1500, 940
