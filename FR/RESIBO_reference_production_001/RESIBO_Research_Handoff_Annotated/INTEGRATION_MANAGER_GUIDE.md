# RESIBO Face Enhancement Integration Guide

## Purpose

This package connects upstream tracked face crops to OSDFace enhancement, AdaFace embeddings, FRMDB reference comparison, and SQLite/DBeaver inspection.

```text
upstream Face/ crops
  -> OSDFace enhancement
  -> AdaFace 512-value embeddings
  -> cosine similarity against FRMDB references
  -> ranked candidates in SQLite
```

## Files To Use

| File | Purpose | Edit? |
|---|---|---|
| `Colab_Research_Restoration.ipynb` | Main Colab workflow and upload/download controls | Only workflow settings |
| `colab_setup_osdface.py` | GPU, OSDFace, AdaFace, checkpoint, and preflight setup | Do not edit for normal runs |
| `osdface_adapter.py` | OSDFace restoration adapter | Do not edit for normal runs |
| `adaface_adapter.py` | AdaFace 512-value normalized embedding adapter | Do not edit for normal runs |
| `colab_worker.py` | Reads a request ZIP, enhances images, embeds references/queries, ranks candidates, writes results ZIP | Do not edit for normal runs |
| `app.py` | Local intake, request export, result import, SQLite verification, and reports | Edit only for integration changes |
| `create_request.py` | One-command intake of upstream `Face/` crops and request ZIP creation | Do not edit for normal runs |
| `schema.sql` | SQLite schema for images, embeddings, and candidates | Edit only with a migration plan |
| `inspect_database.sql` | DBeaver inspection queries | Safe to extend with reporting queries |
| `project_config.example.json` | Portable configuration example | Copy and edit locally |
| `requirements.txt` | Local VS Code dependencies | Edit only when dependencies change |

The runtime ZIP should contain the files above plus this guide. Do not send the local `project_config.json`, full LNS dataset, `.venv`, `__pycache__`, or test output as part of the runtime package.

## Input Folder Contract

The upstream system should provide already-cropped faces in this layout:

```text
Face/
├── TrackedIdentity001/
│   ├── TI001_Frame0001.png
│   └── TI001_Frame0002.png
└── TrackedIdentity002/
    └── TI002_Frame0001.png
```

The folder may contain any number of tracked identities and frames. Preserve the upstream filenames. The importer records the relative path, track ID, and frame number when the naming pattern is present.

The current LNS sample is different: it is a flat, one-image-per-identity dataset. It is usable for pipeline wiring but does not validate temporal tracking or multiple frames per identity. Do not invent frame numbers for LNS.

## Local VS Code Setup

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py hydrate
python app.py verify
```

Reference data is the FRMDB mugshot collection. In this research workflow, FRMDB is the fixed reference gallery used for comparison; it is not an operational criminal-record system, and the sample database does not assert criminal status.

The reference set `frmdb_reference_v1` is intentionally immutable so that every score remains reproducible. The underlying dataset may be expanded or corrected, but do not edit the existing set or replace its images in place. To use a different FRMDB selection or version, ingest it under the appropriate provenance and create a new reference-set ID, for example `frmdb_reference_v2`. Jobs must record which reference-set ID they used.

To intake a manager-provided crop folder and create a request in one command, use a new input dataset ID:

```bash
python create_request.py \
  --input-dir /path/to/Face \
  --dataset UPSTREAM_FACE_INPUT \
  --version upstream_run_001 \
  --url internal://upstream-run-001 \
  --references frmdb_reference_v1 \
  --out exchange/request_upstream_001.zip
```

The directory passed to `--input-dir` must be the directory whose relative paths should be preserved. For the layout above, pass the `Face` directory.

`create_request.py` calls the local intake and export functions for you. It preserves the upstream relative paths and metadata, validates every image, records hashes in SQLite, and creates the request ZIP for Colab. `app.py` remains available for advanced database operations and result import.

## Create A Request

For the controlled AdaFace test used in this project:

```bash
python app.py export \
  --references frmdb_reference_v1 \
  --datasets LNS_INPUT \
  --limit 100 \
  --seed 20261005 \
  --reference-stems Img_13,Img_33,Img_43 \
  --out exchange/request_lns_adaface_test100.zip
```

The `--limit`, `--seed`, and `--reference-stems` options are test-only selections. They are not production limits.

The request ZIP contains `request.json`, input crops, and the selected FRMDB reference images. It does not contain the live SQLite database.

## Complete Module Sequence

Run the modules in this order:

1. `app.py hydrate`: rebuilds reference image files from the reference SQLite BLOBs.
2. `app.py verify`: checks SQLite, image BLOBs, and local file hashes.
3. `create_request.py`: validates the upstream `Face/` folder and creates a Colab request ZIP.
4. `Colab_Research_Restoration.ipynb`: installs/loads OSDFace and AdaFace, processes the request, and downloads a result ZIP plus log.
5. `app.py import`: validates and stores enhanced images, embeddings, and ranked candidates.
6. `app.py verify` and `inspect_database.sql`: confirm the completed database state in VS Code and DBeaver.

The integration manager normally edits only the upstream input folder and the command values (`--dataset`, `--version`, `--url`, and output filename). The model adapters, worker, schema, and importer are processing modules and should remain unchanged unless the integration contract is deliberately revised.

## Colab Run Order

1. Open `Colab_Research_Restoration.ipynb`.
2. Select a GPU runtime.
3. Upload the runtime ZIP when the first upload cell asks for the project package.
4. Set `MODE = 'osdface'`.
5. Run setup and wait for both OSDFace and AdaFace smoke checks to pass.
6. Restart the Colab runtime once.
7. Run the job cell.
8. Upload the request ZIP created by VS Code.
9. Download the result ZIP and its log.

AdaFace preprocessing is intentionally recorded as:

```text
RGB -> 112x112 bicubic resize -> mean/std 0.5 normalization -> normalized 512-value vector
```

This is a resize-only research baseline; it is not landmark alignment validation.

## Return To VS Code

Copy the downloaded result ZIP into `exchange/`, then import it:

```bash
python app.py import --zip exchange/results_adaface_001.zip
python app.py verify
python app.py status
```

The import validates request identity, source/output hashes, completeness, embedding dimensions, reference membership, and candidate references before writing records.

## Database Records

Open `workspace/research.sqlite` in DBeaver. The important tables are:

- `datasets`: source provenance
- `assets`: original, reference, resized, and enhanced image BLOBs
- `reference_sets` / `reference_members`: frozen FRMDB gallery membership
- `jobs` / `job_inputs`: exported processing jobs
- `processing_artifacts`: separate 512x512 model inputs
- `results`: original-to-enhanced links
- `embeddings`: AdaFace vectors and model/preprocessing provenance
- `candidate_matches`: ranked cosine candidates
- `audit_events`: operation history

Run `inspect_database.sql` after refreshing the DBeaver connection.

## Handoff Contents

You should have:

1. The curated runtime ZIP containing this guide, notebook, setup, adapters, worker, local app, schema, and inspection SQL.
2. The reference-only database ZIP containing FRMDB mugshots and `workspace/research.sqlite` if you must inspect or reuse the frozen gallery.
3. The request/result exchange procedure above.
4. Dataset citations and any upstream crop metadata policy.

Won't give complete 25,261-image LNS input but I will give you source links. The current controlled test uses 100 LNS inputs and 201 FRMDB reference images (`Img_13`, `Img_33`, and `Img_43`).

- OSDFace official repository: https://github.comjkwang28/OSDFace

- FRMDB repository and release agreement: https:/github.com/airtlab/
face-recognition-from-mugshots-database
- LNS Human Face Dataset v2: https://data.mendeley.comdatasets/rbczppyyx8/2

- DBeaver SQLite setup: https://dbeaver.com/docsdbeaver/Database-driver-SQLite/

- SQLite backups: https://sqlite.org/backup.html

## Known Scope Limits

- Upstream detection and tracking are external to this package.
- LNS one-image samples do not validate temporal tracking.
- AdaFace scores and candidates are research evidence, not identity decisions.
- No open-set rejection threshold is implemented.
- A larger cosine score is not proof that enhancement preserved identity.
