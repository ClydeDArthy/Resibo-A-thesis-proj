# Resibo-A-thesis-proj

## Running it

```bash
pip install -r requirements.txt
python main.py
```

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Entry point — launches the [resibo](resibo/) front-end |
| `resibo/` | Front-end prototype (Dear PyGui) — see [resibo/README.md](resibo/README.md) |
| `FE/` | Face enhancement |
| `FR/` | Face recognition |
| `Gait/` | Gait recognition |
| `df/` | Deepfake detection |
| `obj/` | Object/person detection |

Each module folder is wired into `main.py` as its pipeline stage is finished.
