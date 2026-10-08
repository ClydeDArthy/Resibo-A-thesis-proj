import numpy as np

from gait_runtime import GaitGalleryScorer
from FE.resibo_ui import live


def test_live_state_tracks_are_not_seeded():
    live.reset()
    assert live.tracks() == []
    live.update_track(7, frame_index=12, face={"faces": 1})
    assert live.track(7)["face"]["faces"] == 1


def test_gait_gallery_scores_embedding(tmp_path):
    path = tmp_path / "gallery.npz"
    embeddings = np.array([[1, 0], [0, 1]], dtype=np.float32)
    np.savez(path, ids=np.array(["A", "B"]), embeddings=embeddings)
    scorer = GaitGalleryScorer(path)
    result = scorer(7, np.array([0.9, 0.1], dtype=np.float32))
    assert result is not None
    assert result.candidate_id == "A"
    assert result.master_id == 7


def test_missing_gait_gallery_does_not_fabricate_result(tmp_path):
    scorer = GaitGalleryScorer(tmp_path / "missing.npz")
    assert scorer.ready is False
    assert scorer(7, np.ones(4, dtype=np.float32)) is None
