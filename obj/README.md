# RESIBO OBJ module — build 001

This package isolates the person-detection/tracking responsibility from the rest of RESIBO.

## Pipeline

`video -> YOLO11 person detection -> BoT-SORT -> master_id -> person crop -> downstream modules`

`master_id` is a **track/trajectory reference**, not a biometric identity.

The module does not make face, gait, or final identity decisions.

## Main files

- `obj/config.py` — runtime configuration
- `obj/pipeline.py` — YOLO11 + BoT-SORT tracking
- `obj/crop.py` — clean person crop extraction
- `obj/types.py` — frame/person observation objects
- `obj/integration.py` — downstream dispatch helpers

## Expected dependencies

The project environment must provide `ultralytics`, `opencv-python`, and `numpy`.

## Existing notebook compatibility

The existing detection notebook's conceptual handoff:

`gait_module(person_crop, master_id, frame_index)`

is preserved by `dispatch_frame()`.

This build intentionally does not replace the existing FE/FR implementation or the existing detection notebook. It provides a repository-level OBJ module that can be wired into them after the core packages are assembled.
