# Resibo-A-thesis-proj

**A Deep-Learning Based Forensic Surveillance Toolkit for Automated CCTV Evidence Review and Reporting**

Undergraduate thesis — BS Computer Science, Digital Forensics
College of Computing and Information Technologies, National University – Manila

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
