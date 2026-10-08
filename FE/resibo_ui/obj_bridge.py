"""Non-blocking live coordinator: OBJ is the frame clock for all downstream models."""
import os
from pathlib import Path
import threading

from .. import data, db, live, state

_VIDEO_EXTS = {".mp4", ".dav", ".asf", ".avi", ".mov", ".mkv"}
_lock = threading.RLock()
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
_generation = 0


def _case():
    return data.CASES[state.SEL["case"]]


def _video_for_case(case):
    for row in db.evidence_for(case["number"]):
        path = Path(row["path"])
        if path.suffix.lower() not in _VIDEO_EXTS:
            continue
        if path.is_file():
            return path
        base = case.get("base_dir") or ""
        candidate = Path(base) / path if base else path
        if candidate.is_file():
            return candidate
    return None


def start_for_current_case():
    global _thread, _key, _status, _result, _error, _progress, _generation
    source = _video_for_case(_case())
    if source is None:
        with _lock:
            _status, _error = "no_video", "No accessible video exhibit is attached to this case."
            live.set_pipeline("obj", _status, _error)
        return False
    key = (_case()["number"], str(source))
    with _lock:
        if _thread and _thread.is_alive() and _key == key:
            return True
        if _key == key and _status == "completed":
            return True
        _generation += 1
        generation = _generation
        _key, _status, _result, _error, _progress = key, "starting", None, None, 0.0
        _gait_results.clear()
        _face_results.clear()
        _resolutions.clear()
        live.reset()
        _thread = threading.Thread(target=_worker, args=(source, _case()["number"], generation), daemon=True)
        _thread.start()
    return True


def _worker(source, case_number, generation):
    global _status, _result, _error, _progress, _latest
    try:
        from obj import ObjectConfig, ObjectRunner, ObjectTrackingPipeline
        from Gait import GaitConfig, GaitPipeline
        from Gait.gaitbase import GaitBaseAdapter
        from face_runtime import FaceRuntime
        from gait_runtime import GaitGalleryScorer, SegmentationSilhouetteExtractor, load_callable
        from resibo.runtime import ResiboRuntime
        from resibo import BiometricObservation
        from resibo.fr_adapter import cosine_to_unit_score

        fr_store = None
        fr_db = Path(os.getenv("RESIBO_FR_DB", "FR/workspace/research.sqlite"))
        if fr_db.is_file():
            from resibo.fr_adapter import FRCandidateStore
            fr_store = FRCandidateStore(fr_db)
            fr_store.verify_read_only()

        face_runtime = FaceRuntime(fr_store=fr_store)
        silhouette = SegmentationSilhouetteExtractor()

        gait_backend = None
        gait_error = None
        try:
            gait_backend = load_callable()
            if gait_backend is None:
                checkpoint = Path(os.getenv(
                    "RESIBO_GAIT_CHECKPOINT",
                    "workspace/gait/GaitBase_DA_CCGR_FT-10000.pt",
                ))
                if checkpoint.is_file():
                    from Gait.rebigait_adapter import infer_gaitbase
                    gait_backend = infer_gaitbase
        except Exception as exc:
            gait_error = str(exc)

        gait_scorer = load_callable(os.getenv("RESIBO_GAIT_SCORER")) or GaitGalleryScorer()
        gait_base = GaitBaseAdapter(gait_backend)
        gait_stage = GaitPipeline(GaitConfig(), gaitbase=gait_base)

        runtime = ResiboRuntime(
            fr_store=fr_store,
            silhouette_extractor=silhouette,
            gait_scorer=gait_scorer if getattr(gait_scorer, "ready", True) else None,
            gait_stage=gait_stage,
        )

        config = ObjectConfig(
            person_weights=os.getenv("RESIBO_PERSON_WEIGHTS", "yolo11s.pt"),
            person_confidence=float(os.getenv("RESIBO_PERSON_CONFIDENCE", "0.35")),
        )
        pipeline = ObjectTrackingPipeline(config)
        runner = ObjectRunner(pipeline)

        live.set_pipeline("obj", "starting")
        live.set_pipeline("face", "ready" if face_runtime.detector_ready else "waiting", face_runtime.error or (None if face_runtime.detector_ready else "Face detector checkpoint not configured."))
        if gait_backend and silhouette.ready:
            live.set_pipeline("gait", "ready")
        else:
            live.set_pipeline(
                "gait",
                "waiting",
                gait_error or silhouette.error or "GaitBase backend/silhouette model not configured.",
            )
        resibo_ready = (
            getattr(gait_scorer, "ready", False)
            and (face_runtime.processor is not None or fr_store is not None)
        )
        live.set_pipeline(
            "resibo",
            "ready" if resibo_ready else "waiting",
            None if resibo_ready else "Requires a face result and a gait gallery/scorer.",
        )

        output_dir = Path("workspace") / "obj" / case_number / source.stem

        def on_frame(observation):
            global _latest, _status, _progress
            _latest = observation
            _status = "running"
            live.set_pipeline("obj", "running")

            # One frame clock: every tracked person is processed here.
            if generation != _generation:
                return
            for person in observation.people:
                master_id = int(person.master_id)
                if person.crop is None:
                    continue

                face = face_runtime.process(
                    observation.frame, person.person_box, master_id, person.frame_index
                )
                _face_results[master_id] = face

                # A live face processor is authoritative for this frame. If
                # it returns a candidate/score, hand that observation to the
                # same RESIBO track rather than waiting for the FR database.
                if face.get("candidate") is not None and face.get("score") is not None:
                    raw_face_score = float(face["score"])
                    face_score = (
                        cosine_to_unit_score(raw_face_score)
                        if -1.0 <= raw_face_score <= 1.0
                        else raw_face_score
                    )
                    runtime.update_face_observation(
                        BiometricObservation(
                            master_id=master_id,
                            modality="face",
                            candidate_id=str(face["candidate"]),
                            score=float(face_score),
                            quality=float(face.get("quality") or 0.0),
                            metadata={
                                "source": "live_face_processor",
                                "raw_cosine_similarity": raw_face_score,
                                "frame_index": int(person.frame_index),
                            },
                        )
                    )

                try:
                    resolution = runtime.process_person(
                        master_id, person.frame_index, person.crop,
                        face_quality=float(face.get("quality") or 0.0),
                    )
                except RuntimeError as exc:
                    resolution = None
                    live.set_pipeline("gait", "error", str(exc))

                gait = runtime.gait_results.get(master_id)
                _gait_results[master_id] = gait
                _resolutions[master_id] = resolution

                live.update_track(
                    master_id, person.frame_index, face=face,
                    gait={
                        "status": getattr(gait, "status", "waiting"),
                        "frame_count": getattr(gait, "frame_count", 0),
                        "embedding_ready": getattr(gait, "embedding", None) is not None,
                    },
                    resolution=resolution,
                )

            # UI progress is based on frames actually processed, not seeded values.
            live.set_pipeline("face", "running" if face_runtime.detector_ready else "waiting")
            if gait_backend and silhouette.ready:
                live.set_pipeline("gait", "running")
            elif gait_error or not silhouette.ready:
                live.set_pipeline(
                    "gait",
                    "waiting",
                    gait_error or silhouette.error or "GaitBase backend/silhouette model not configured.",
                )
            if fr_store and getattr(gait_scorer, "ready", False):
                live.set_pipeline("resibo", "running")

        if generation != _generation:
            return
        _result = runner.run(source, output_dir, on_frame=on_frame)
        _progress = 1.0
        _status = "completed"
        live.set_pipeline("obj", "completed")
        if face_runtime.detector_ready:
            live.set_pipeline("face", "completed")
        if gait_backend and silhouette.ready:
            live.set_pipeline("gait", "completed")
        if fr_store and getattr(gait_scorer, "ready", False):
            live.set_pipeline("resibo", "completed")
    except Exception as exc:
        _error = str(exc)
        _status = "error"
        live.set_pipeline("obj", "error", _error)


def tick():
    return status()


def status():
    with _lock:
        return {"status": _status, "progress": _progress, "error": _error}


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
