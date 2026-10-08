"""Non-blocking bridge between the existing DearPyGui FE and OBJ."""
import os
from pathlib import Path
import threading

from .. import data, db, state

_VIDEO_EXTS = {".mp4", ".dav", ".asf", ".avi", ".mov", ".mkv"}
_lock = threading.Lock()
_thread = None
_key = None
_status = "idle"
_result = None
_error = None
_progress = 0.0
_latest = None


def _case():
    return data.CASES[state.SEL["case"]]


def _video_for_case(case):
    for row in db.evidence_for(case["number"]):
        path = Path(row["path"])
        if path.suffix.lower() not in _VIDEO_EXTS:
            continue
        if path.is_file():
            return path
        base_dir = case.get("base_dir") or ""
        if base_dir:
            candidate = Path(base_dir) / path
            if candidate.is_file():
                return candidate
    return None


def start_for_current_case():
    global _thread, _key, _status, _result, _error, _progress
    case = _case()
    source = _video_for_case(case)
    if source is None:
        with _lock:
            _status = "no_video"
            _error = "No accessible video exhibit is attached to this case."
        return False

    key = (case["number"], str(source))
    with _lock:
        if _thread is not None and _thread.is_alive() and _key == key:
            return True
        if _key == key and _status == "completed":
            return True
        _key = key
        _status = "starting"
        _result = None
        _error = None
        _progress = 0.0
        _thread = threading.Thread(
            target=_worker,
            args=(source, case["number"]),
            daemon=True,
        )
        _thread.start()
    return True


def _worker(source, case_number):
    global _status, _result, _error, _progress, _latest
    try:
        from obj import ObjectConfig, ObjectRunner, ObjectTrackingPipeline

        config = ObjectConfig()
        pipeline = ObjectTrackingPipeline(config)
        runner = ObjectRunner(pipeline)

        output_dir = Path("workspace") / "obj" / case_number / source.stem

        def on_frame(observation):
            global _latest, _progress, _status
            _latest = observation
            _status = "running"

        _result = runner.run(source, output_dir, on_frame=on_frame)
        _status = "completed"
        _progress = 1.0
    except Exception as exc:
        _error = str(exc)
        _status = "error"


def tick():
    """Render-loop seam; deliberately does no blocking work."""
    return status()


def status():
    with _lock:
        return {
            "status": _status,
            "progress": _progress,
            "error": _error,
        }


def latest_result():
    return _result


def latest_observation():
    return _latest