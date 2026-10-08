import numpy as np
from FE.resibo_ui import live
from gait_runtime import GaitGalleryScorer


def test_live_state_has_one_track_clock():
    live.reset()
    assert live.tracks() == []
    live.update_track(7, 12, face={"faces": 1}, gait={"status": "collecting"})
    row = live.track(7)
    assert row["frame_index"] == 12
    assert row["face"]["faces"] == 1
    assert row["gait"]["status"] == "collecting"


def test_gallery_scorer_returns_real_candidate(tmp_path):
    path = tmp_path / "gallery.npz"
    np.savez(path, ids=np.array(["A", "B"]), embeddings=np.array([[1., 0.], [0., 1.]]))
    result = GaitGalleryScorer(path)(7, np.array([0.9, 0.1]))
    assert result.candidate_id == "A"
    assert result.master_id == 7


def test_missing_gallery_does_not_fabricate_gait(tmp_path):
    scorer = GaitGalleryScorer(tmp_path / "missing.npz")
    assert not scorer.ready
    assert scorer(7, np.ones(2)) is None
