import json
import sqlite3

from resibo.fr_adapter import FRCandidateStore


def make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE assets (
            asset_id TEXT PRIMARY KEY,
            metadata_json TEXT NOT NULL
        );
        CREATE TABLE candidate_matches (
            job_id TEXT NOT NULL,
            input_asset_id TEXT NOT NULL,
            branch TEXT NOT NULL,
            candidate_rank INTEGER NOT NULL,
            reference_asset_id TEXT NOT NULL,
            reference_subject_id TEXT,
            cosine_similarity REAL NOT NULL
        );
        """
    )
    db.execute(
        "INSERT INTO assets VALUES (?, ?)",
        ("input-1", json.dumps({"track_id": "master-7"})),
    )
    db.execute(
        "INSERT INTO candidate_matches VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("job-1", "input-1", "ENHANCED", 1, "ref-1", "person-A", 0.80),
    )
    db.commit()
    db.close()


def test_fr_candidate_read_is_read_only(tmp_path):
    db_path = tmp_path / "research.sqlite"
    make_db(db_path)

    store = FRCandidateStore(db_path)
    candidates = store.candidates_for_track("master-7")

    assert len(candidates) == 1
    assert candidates[0].candidate_id == "person-A"
    assert candidates[0].cosine_similarity == 0.80

    observation = store.observation_from_candidate(candidates[0], master_id=7)
    assert observation.master_id == 7
    assert observation.modality == "face"
    assert observation.score == 0.90
    assert observation.metadata["raw_cosine_similarity"] == 0.80

    # The adapter must not add or change database rows.
    with sqlite3.connect(db_path) as db:
        count = db.execute("SELECT COUNT(*) FROM candidate_matches").fetchone()[0]
    assert count == 1


def test_cosine_range_mapping_rejects_invalid_value():
    try:
        FRCandidateStore.cosine_to_unit_score(1.1)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range cosine similarity must fail")
