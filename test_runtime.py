import sqlite3

import numpy as np

from resibo import BiometricObservation, ResiboPipeline
from resibo.fr_adapter import FRCandidateStore
from resibo.runtime import ResiboRuntime


def _make_db(path):
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
            reference_subject_id TEXT,
            reference_asset_id TEXT,
            candidate_rank INTEGER NOT NULL,
            cosine_similarity REAL NOT NULL,
            branch TEXT NOT NULL
        );
        """
    )
    db.execute(
        "INSERT INTO assets VALUES (?, ?)",
        ("input-1", '{"track_id": "7"}'),
    )
    db.execute(
        "INSERT INTO candidate_matches VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("job-1", "input-1", "person-A", "ref-1", 1, 0.9, "ENHANCED"),
    )
    db.commit()
    db.close()


def test_runtime_hands_face_and_gait_to_resibo(tmp_path):
    db_path = tmp_path / "fr.sqlite"
    _make_db(db_path)

    def gait_scorer(master_id, embedding):
        assert master_id == 7
        assert embedding.shape == (4,)
        return BiometricObservation(7, "gait", "person-A", 0.82)

    runtime = ResiboRuntime(
        resolver=ResiboPipeline(),
        fr_store=FRCandidateStore(db_path),
        gait_scorer=gait_scorer,
    )

    result = runtime.update_track(7, np.zeros((100, 50, 3), dtype=np.uint8), np.zeros(4))
    assert result is not None
    assert result.state == "resolved"
    assert runtime.get(7).face.candidate_id == "person-A"
    assert runtime.get(7).gait.candidate_id == "person-A"


def test_runtime_does_not_invent_gait_score_without_scorer():
    runtime = ResiboRuntime()
    result = runtime.update_track(
        7, np.zeros((100, 50, 3), dtype=np.uint8), gait_embedding=np.zeros(4)
    )
    assert result is None
    assert runtime.get(7).gait is None


def test_runtime_clears_track_state():
    runtime = ResiboRuntime()
    runtime.tracks[7] = runtime.get(7)
    runtime.clear(7)
    assert 7 not in runtime.tracks


class _FakeGaitResult:
    status = "inferred"
    embedding = np.arange(4, dtype=np.float32)


class _FakeGaitStage:
    def __init__(self):
        self.calls = []

    def update(self, master_id, frame_index, person_crop):
        self.calls.append(("update", master_id, frame_index))

    def update_silhouette(self, master_id, frame_index, silhouette):
        self.calls.append(("silhouette", master_id, frame_index))
        return _FakeGaitResult()


def test_runtime_process_person_uses_matching_gait_stage():
    gait_stage = _FakeGaitStage()

    def gait_scorer(master_id, embedding):
        return BiometricObservation(master_id, "gait", "person-A", 0.82)

    runtime = ResiboRuntime(
        gait_stage=gait_stage,
        silhouette_extractor=lambda crop: np.ones((20, 10), dtype=np.uint8) * 255,
        gait_scorer=gait_scorer,
    )

    result = runtime.process_person(
        7, 12, np.zeros((100, 50, 3), dtype=np.uint8)
    )

    assert result is not None
    assert result.state == "resolved"
    assert gait_stage.calls == [("update", 7, 12), ("silhouette", 7, 12)]
