"""Create a Colab request ZIP directly from an upstream Face/ crop folder."""
from pathlib import Path
import argparse
import json

from app import connect, export_job, ingest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True,
                        help='Upstream Face/ directory; relative paths are preserved')
    parser.add_argument('--dataset', required=True,
                        help='Stable input dataset ID for this upstream run')
    parser.add_argument('--version', required=True,
                        help='Upstream run or source version')
    parser.add_argument('--url', required=True,
                        help='Upstream source or run provenance URL')
    parser.add_argument('--references', required=True,
                        help='Frozen reference-set ID, for example frmdb_reference_v1')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, default=Path('workspace'))
    parser.add_argument('--limit', type=int,
                        help='Optional test-only input sample size')
    parser.add_argument('--seed', type=int,
                        help='Seed for a reproducible test-only sample')
    parser.add_argument('--reference-stems',
                        help='Optional comma-separated test reference filename stems')
    args = parser.parse_args()

    stems = None
    if args.reference_stems:
        stems = [stem.strip() for stem in args.reference_stems.split(',') if stem.strip()]

    workspace = args.workspace.resolve()
    input_dir = args.input_dir.resolve()
    db = connect(workspace)
    try:
        intake = ingest(db, workspace, args.dataset, input_dir, 'input', args.version, args.url)
        job = export_job(db, workspace, args.references, [args.dataset], args.out,
                         args.limit, args.seed, stems)
    finally:
        db.close()
    print(json.dumps({'intake': intake, 'job': job}, indent=2))


if __name__ == '__main__':
    main()
