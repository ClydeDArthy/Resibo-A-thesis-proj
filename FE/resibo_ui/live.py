"""Single live state store shared by every model screen."""
from threading import RLock

_lock = RLock()
_pipelines = {"obj": "idle", "face": "idle", "gait": "idle", "resibo": "idle"}
_tracks = {}


def reset():
    with _lock:
        for key in _pipelines:
            _pipelines[key] = "idle"
        _tracks.clear()


def set_pipeline(name, status, error=None):
    with _lock:
        _pipelines[name] = {"status": status, "error": error} if error else status


def update_track(master_id, frame_index, face=None, gait=None, resolution=None):
    with _lock:
        row = _tracks.setdefault(int(master_id), {"master_id": int(master_id)})
        row["frame_index"] = int(frame_index)
        if face is not None:
            row["face"] = dict(face)
        if gait is not None:
            row["gait"] = dict(gait)
        if resolution is not None:
            row["resolution"] = resolution


def track(master_id):
    with _lock:
        return dict(_tracks.get(int(master_id), {"master_id": int(master_id)}))


def tracks():
    with _lock:
        return [dict(v) for v in sorted(_tracks.values(), key=lambda x: x["master_id"])]


def pipeline_status():
    with _lock:
        return dict(_pipelines)


def snapshot():
    return {"pipelines": pipeline_status(), "tracks": tracks()}
