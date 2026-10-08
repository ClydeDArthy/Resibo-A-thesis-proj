"""Live model state exposed to the existing DearPyGui screens.

The UI reads this module only; model code remains in OBJ/Gait/FR/RESIBO.
No seeded reference-data value is promoted to a live result.
"""
from typing import Any, Dict

_tracks: Dict[int, Dict[str, Any]] = {}
_pipeline_status = {"obj": "idle", "face": "idle", "gait": "idle", "resibo": "idle", "error": None}


def reset() -> None:
    _tracks.clear()
    for key in _pipeline_status:
        _pipeline_status[key] = "idle" if key != "error" else None


def set_pipeline(name: str, status: str, error: str | None = None) -> None:
    _pipeline_status[name] = status
    if error:
        _pipeline_status["error"] = error


def update_track(master_id: int, **values: Any) -> None:
    row = _tracks.setdefault(int(master_id), {"master_id": int(master_id)})
    row.update(values)


def track(master_id: int) -> Dict[str, Any]:
    return dict(_tracks.get(int(master_id), {"master_id": int(master_id)}))


def tracks() -> list[Dict[str, Any]]:
    return [dict(v) for _, v in sorted(_tracks.items())]


def pipeline_status() -> dict:
    return dict(_pipeline_status)


def snapshot() -> dict:
    return {"pipelines": pipeline_status(), "tracks": tracks()}
