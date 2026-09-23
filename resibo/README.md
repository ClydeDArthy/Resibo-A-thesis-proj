# RESIBO

**A Deep-Learning Based Forensic Surveillance Toolkit for Automated CCTV Evidence Review and Reporting**

Undergraduate thesis — BS Computer Science, Digital Forensics
College of Computing and Information Technologies, National University – Manila

This folder holds the **front-end prototype**: the full interface, built with
[Dear PyGui](https://github.com/hoffstadt/DearPyGui). The analysis models are not
wired in yet — every screen reads from sample data in `resibo_ui/data.py`.

It is one module of the [Resibo-A-thesis-proj](../README.md) solution, alongside
the other pipeline stages (`FE/`, `FR/`, `Gait/`, `df/`, `obj/`).

## Running it

From the repository root:

```bash
pip install -r requirements.txt
python main.py
```

Or standalone, from inside this folder (useful while working on the UI alone):

```bash
pip install -r ../requirements.txt
python Index.py
```

Tested on Windows with Python 3.14.

## What works

The interface is interactive, not a mockup:

- **Case picker** — cards with hover animation; click to select, double click to open
- **New case** — a form that gates evidence intake until the details are complete,
  then hashes the files you add with a real SHA-256 (progress is actual work, and
  Cancel genuinely stops it)
- **Case workspace** — eight workflow steps, each a button that expands its flags
  and opens the stage that produced them
- **Person detection** — annotated frame plus saved identity folders; opening one
  shows its crops or its gait output, and double clicking a crop opens it full size
- **History** — a live audit trail that reflects how far the case has actually run,
  filterable by stage and by flag
- **Four themes** — Dark, Light, Pink, Dark blue, remembered between runs

Export stays disabled until every step of a case has finished.

## Layout

| Path | Purpose |
| --- | --- |
| `Index.py` | Entry point |
| `resibo_ui/app.py` | Shell: nav rail, header, the three stages |
| `resibo_ui/data.py` | Sample case data — replace with real pipeline output |
| `resibo_ui/theme.py` | Palettes and shared themes |
| `resibo_ui/widgets.py` | Shared building blocks |
| `resibo_ui/screens/` | One module per screen |
| `images/` | The approved UI mockups |

## Status

Front-end only. Wiring the back end means replacing `data.py`, and three things
that are not data swaps: running the models on a worker thread so inference does
not freeze the single-threaded UI, decoding video into textures, and rendering
real face crops in place of the drawn placeholders.

The sample figures — case numbers, confidence scores, gait measurements — are
illustrative and must not be cited as results.

## Authors

Maria Edona I. Inocencio · Aliamae Danna S. Garcia · Jersey Mae D. Marisga ·
Roshelle C. Osorio · Keith Clarence V. Peralta

Topic adviser: Rogel M. Labanan
