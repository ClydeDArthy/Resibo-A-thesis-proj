# RESIBO live model runtime

The UI now consumes live model state. It does not display the old seeded face/gait reference data as current output.

## 1. Person detection / tracking

OBJ uses Ultralytics YOLO11 + BoT-SORT.

- `RESIBO_PERSON_WEIGHTS` — optional person checkpoint; defaults to `yolo11s.pt`.
- Official YOLO11 weights can be resolved by Ultralytics at first use.
- `RESIBO_PERSON_CONFIDENCE` — detection confidence, default `0.35`.

The People screen displays the actual frame emitted by OBJ and the live BoT-SORT `master_id` boxes.

## 2. Face

Set:

- `RESIBO_FACE_WEIGHTS` — the project's face detector checkpoint, default `yolov11s-face.pt`.
- `RESIBO_FR_DB` — path to the existing FR SQLite result store. Default: `FR/workspace/research.sqlite`.

The face runtime detects faces from the tracked person crop. If the FR result store exists, the UI also reads the ranked OSDFace/AdaFace candidate rows through the read-only RESIBO adapter.

OSDFace/AdaFace themselves remain the existing FR runtime; this repository does not replace their model implementation.

## 3. Gait

Set:

- `RESIBO_SILHOUETTE_WEIGHTS` — optional YOLO11 segmentation checkpoint, default `yolo11n-seg.pt`.
- `RESIBO_GAIT_BACKEND` — Python callable in the form `module:function`. It must accept a normalized `[T, 64, 64]` silhouette tensor and return one GaitBase embedding vector.
- `RESIBO_GAIT_GALLERY` — optional `.npz` gallery containing `ids` `[N]` and `embeddings` `[N,D]` GaitBase reference embeddings.

If `RESIBO_GAIT_SCORER` is supplied, it overrides the built-in cosine gallery scorer and must return a `BiometricObservation` with modality `gait`.

There is deliberately no fake GaitBase fallback. If the trained checkpoint backend is absent, the UI reports that GaitBase is waiting rather than showing the old seeded gait result.

## 4. Runtime behavior

Each tracked `master_id` follows the same path:

YOLO11 + BoT-SORT -> person crop -> face + silhouette -> GaitBase -> RESIBO

Face and gait results stay associated with the same track reference. RESIBO only receives a gait observation after a real GaitBase embedding is produced.

The final UI therefore reports the runtime state instead of silently mixing reference-data values with live model output.
