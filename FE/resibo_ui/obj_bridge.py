"""Non-blocking bridge between the existing DearPyGui FE and the live model pipeline."""
import os
from pathlib import Path
import threading

from .. import data, db, state
from .. import live

_VIDEO_EXTS = {".mp4", ".dav", ".asf", ".avi", ".mov", ".mkv"}
_lock = threading.Lock()
_thread = None
_key = None
_status = "idle"
_result = None
_error = None
_progress = 0.0
_latest = None
_gait_results = {}
_face_results = {}
_resolutions = {}


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


def _fr_store():
    database = Path(os.getenv("RESIBO_FR_DB", "FR/workspace/research.sqlite"))
    if not database.is_file():
        return None
    try:
        from resibo.fr_adapter import FRCandidateStore
        store = FRCandidateStore(database)
        store.verify_read_only()
        return store
    except Exception:
        return None


def start_for_current_case():
    global _thread, _key, _status, _result, _error, _progress
    case = _case()
    source = _video_for_case(case)
    if source is None:
        with _lock:
            _status = "no_video"
            _error = "No accessible video exhibit is attached to this case."
            live.set_pipeline("obj", "no_video", _error)
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
        _gait_results.clear()
        _face_results.clear()
        _resolutions.clear()
        live.reset()
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
        from Gait import GaitConfig, GaitPipeline
        from Gait.gaitbase import GaitBaseAdapter
        from gait_runtime import load_callable, silhouette_from_person_crop
        from face_runtime import FaceRuntime
        from resibo.runtime import ResiboRuntime

        fr_store = _fr_store()
        gait_backend = load_callable()
        gait_scorer = load_callable(os.getenv("RESIBO_GAIT_SCORER"))
        gait_pipeline = GaitPipeline(
            GaitConfig(),
            gaitbase=GaitBaseAdapter(gait_backend),
        )
        face_runtime = FaceRuntime(fr_store=fr_store)
        runtime = ResiboRuntime(
            fr_store=fr_store,
            silhouette_extractor=silhouette_from_person_crop,
            gait_scorer=gait_scorer,
            gait_stage=gait_pipeline,
        )

        config = ObjectConfig(
            person_weights=os.getenv("RESIBO_PERSON_WEIGHTS", "yolo11s.pt"),
            person_confidence=float(os.getenv("RESIBO_PERSON_CONFIDENCE", "0.35")),
        )
        pipeline = ObjectTrackingPipeline(config)
        runner = ObjectRunner(pipeline)

        output_dir = Path("workspace") / "obj" / case_number / source.stem
        live.set_pipeline("obj", "starting")
        live.set_pipeline("face", "ready" if face_runtime.detector_ready else "waiting")
        live.set_pipeline("gait", "ready" if gait_backend else "waiting")
        live.set_pipeline("resibo", "ready" if fr_store and gait_scorer else "waiting")

        def on_person(person, frame):
            global _latest
            master_id = int(person.master_id)
            face = face_runtime.process(
                frame, person.person_box, master_id, person.frame_index
            )
            _face_results[master_id] = face
            face_quality = float(face.get("quality") or 0.0)
            if fr_store is not None:
                runtime.update_face(master_id, quality=face_quality)

            try:
                gait = runtime.process_person(
                    master_id,
                    person.frame_index,
                    person.crop,
                    face_quality=face_quality,
                )
            except RuntimeError as exc:
                # A missing trained GaitBase backend must not stop YOLO/face
                # processing or make the UI fall back to seeded gait values.
                from Gait.pipeline import GaitResult
                gait = GaitResult(
                    track_id=master_id,
                    status="backend_error",
                    frame_count=len(gait_pipeline.sequences.get(master_id)),
                    diagnostics={"error": str(exc)},
                )
                live.set_pipeline("gait", "error", str(exc))
            _gait_results[master_id] = gait

            state = runtime.get(master_id)
            resolution = state.resolution
            _resolutions[master_id] = resolution

            live.update_track(
                master_id,
                frame_index=int(person.frame_index),
                face=face,
                gait={
                    "status": getattr(gait, "status", "waiting"),
                    "frame_count": getattr(gait, "frame_count", 0),
                    "embedding_ready": getattr(gait, "embedding", None) is not None,
                },
                resolution=resolution,
            )

        def on_frame(observation):
            global _latest, _progress, _status
            _latest = observation
            _status = "running"
            live.set_pipeline("obj", "running")

        # The runner remains the source of truth for tracks/crops. The live
        # callback below consumes each observation without blocking the UI.
        def on_observation(observation):
            for person in observation.people:
                if person.crop is not None:
                    on_person(person, observation.frame)
            on_frame(observation)

        _result = runner.run(
            source,
            output_dir,
            gait_module=None,
            face_module=None,
            on_frame=on_observation,
        )
        _status = "completed"
        _progress = 1.0
        live.set_pipeline("obj", "completed")
        if gait_backend:
            live.set_pipeline("gait", "completed")
        if fr_store:
            live.set_pipeline("face", "completed")
        if fr_store and gait_scorer:
            live.set_pipeline("resibo", "completed")
    except Exception as exc:
        _error = str(exc)
        _status = "error"
        live.set_pipeline("obj", "error", _error)


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


def gait_results():
    return dict(_gait_results)


def face_results():
    return dict(_face_results)


def resolutions():
    return dict(_resolutions)


def live_snapshot():
    return live.snapshot()
