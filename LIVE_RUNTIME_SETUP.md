# Live runtime on branch tst

The UI is driven by the same runtime state as the models.

YOLO11 + BoT-SORT -> master_id/person crop -> face + silhouette -> GaitBase -> RESIBO -> UI

## Required local model/runtime artifacts

- RESIBO_PERSON_WEIGHTS: YOLO11 person checkpoint. Defaults to yolo11s.pt.
- RESIBO_FACE_WEIGHTS: face detector checkpoint. Defaults to yolov11s-face.pt.
- RESIBO_SILHOUETTE_WEIGHTS: YOLO11 segmentation checkpoint. Defaults to yolo11n-seg.pt.
- RESIBO_GAIT_BACKEND: trained GaitBase callable as module:function.
- RESIBO_GAIT_GALLERY: optional .npz with ids and embeddings.
- RESIBO_FR_DB: existing FR SQLite result store. Defaults to FR/workspace/research.sqlite.

The code does not manufacture a GaitBase embedding when the trained backend is absent. Walking explicitly shows GaitBase waiting/error.

## What to see

1. Open a case with a real video exhibit.
2. Person detection shows the actual current video frame and live YOLO11/BoT-SORT master_id boxes.
3. Face enhancement shows the same master_id rows and live face/FR state.
4. Walking shows the same master_id, growing frame count, silhouette state, and GaitBase inference when configured.
5. Progress shows all four live pipeline states from the same runtime.
6. When face and gait observations are usable, RESIBO shows the resolution state/candidate for that same master_id.

The interface never substitutes seeded face/gait reference values for live model output.

## Gait model from rebigait.py

The live adapter now targets the **fine-tuned GaitBase model produced by rebigait.py**, not a generic/fake GaitBase backend.

Expected local layout:

```
OpenGait/                         # cloned OpenGait repository
workspace/gait/
└── GaitBase_DA_CCGR_FT-10000.pt
```

Optional environment variables:

```
RESIBO_OPENGAIT_ROOT=OpenGait
RESIBO_GAIT_CHECKPOINT=workspace/gait/GaitBase_DA_CCGR_FT-10000.pt
RESIBO_GAIT_DEVICE=cuda
```

The adapter is `Gait/rebigait_adapter.py`. It loads the OpenGait Baseline architecture used by the notebook, accepts the live 64x64 silhouette sequence, and returns the native `[16, 256]` GaitBase embedding.

The live path is therefore:

```
YOLO11 person crop
    -> YOLO11 segmentation
    -> validated 64x64 silhouettes
    -> TrackSequenceBuffer
    -> rebigait GaitBase checkpoint
    -> [16,256] embedding
    -> gait scorer/gallery
    -> RESIBO
```

A missing checkpoint or incompatible OpenGait installation is reported as a gait error/waiting state. No synthetic gait identity is generated.
