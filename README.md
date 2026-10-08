# Resibo-A-thesis-proj

## Running it

Install the requirements and run `python main.py`.

The project entry point remains main.py. Development work is kept in feature branches; the default main branch is not modified by the development workflow.

## Layout

| Path | Purpose |
| --- | --- |
| main.py | Entry point — launches the RESIBO front-end |
| FE/ | Existing Dear PyGui front-end |
| FR/ | Face enhancement and face recognition workflow (OSDFace + AdaFace) |
| Gait/ | Gait sequence preparation and GaitBase/OpenGait boundary |
| obj/ | YOLO11 person detection and BoT-SORT tracking |
| resibo/ | Multimodal fusion, resolution, and diagnostic decision loop |
| df/ | Deepfake detection area reserved for the existing project module |

## Development status

The repository separates model-independent orchestration from model checkpoints and external runtimes. Large checkpoints, SQLite runtime workspaces, generated outputs, and experiment artifacts are intentionally not committed.

The automated tests cover the detector crop contract, gait preprocessing/sequence handling, and RESIBO decision logic. Actual YOLO11, OSDFace/AdaFace, and fine-tuned GaitBase execution additionally requires the project checkpoints and runtime data described in their module documentation.
