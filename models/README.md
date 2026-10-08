# Runtime model files

Place model artifacts outside Git when they are large binary checkpoints.

## Supplied in the current RESIBO work package

- `yolov11s-face.pt` — YOLO11-Face detector checkpoint.
  The FE runtime auto-discovers it from:
  - project root
  - `models/`
  - `workspace/models/`

## Required for the complete live pipeline

- YOLO11 person checkpoint, normally `yolo11s.pt`
- YOLO11 segmentation checkpoint, normally `yolo11n-seg.pt`
- ReBiGait fine-tuned GaitBase checkpoint:
  `GaitBase_DA_CCGR_FT-10000.pt`
- OpenGait source tree
- OSDFace pretrained assets and its Stable Diffusion 2.1 local assets
- AdaFace IR50 WebFace4M local model
- Face and gait reference galleries

The repository deliberately does not fabricate any of these missing model outputs.

## ReBiGait checkpoint location

The supplied ReBiGait notebook produces:

`OpenGait/output/CCGR-MINI/Baseline/GaitBase_DA_CCGR_FT/checkpoints/GaitBase_DA_CCGR_FT-10000.pt`

The live adapter now auto-discovers that location as well as:

`workspace/gait/GaitBase_DA_CCGR_FT-10000.pt`

## Face runtime

The YOLO11-Face detector is automatic once `yolov11s-face.pt` is placed in one of the locations above.

OSDFace and AdaFace are not substituted with another model. They require their actual model assets and the existing FR adapters.

## Important

Do not put large model checkpoints into ordinary Git commits. Keep them in the local model directory or use the project's model/artifact storage. The source code records the expected filenames and paths.
