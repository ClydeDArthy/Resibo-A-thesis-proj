# RESIBO Gait module

This package owns tracked-person gait sequence collection and the boundary to the project's OpenGait/GaitBase inference backend.

## Pipeline boundary

`OBJ master_id -> RGB person crops -> gait sequence buffer -> validated silhouettes -> GaitBase embedding`

The RGB crop is **not** silently converted into a silhouette. A silhouette extractor must be supplied explicitly before GaitBase inference is considered ready.

## Main files

- `Gait/config.py` — sequence and preprocessing settings
- `Gait/sequence.py` — per-`master_id` frame buffers and continuity checks
- `Gait/preprocessing.py` — silhouette validation/normalization
- `Gait/gaitbase.py` — OpenGait/GaitBase adapter boundary
- `Gait/pipeline.py` — detector-facing gait pipeline

## Runtime requirement

The repository contains the integration boundary, not a bundled GaitBase checkpoint or a fabricated silhouette extractor. Before live gait inference, connect the project's tested OpenGait/GaitBase backend and a validated silhouette source.
