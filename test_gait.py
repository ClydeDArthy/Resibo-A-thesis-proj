import numpy as np

from Gait import GaitConfig, GaitPipeline
from Gait.gaitbase import GaitBaseAdapter


def fake_backend(sequence):
    assert sequence.shape == (4, 64, 64)
    return np.arange(8, dtype=np.float32)


def test_sequence_collection():
    cfg = GaitConfig(sequence_length=4, min_valid_frames=4)
    pipe = GaitPipeline(cfg)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)

    for i in range(4):
        result = pipe.update(7, i, crop)

    assert result.track_id == 7
    assert result.frame_count == 4
    assert result.status == "awaiting_silhouette"


def test_silhouette_normalization_and_inference():
    cfg = GaitConfig(sequence_length=4, min_valid_frames=4)
    pipe = GaitPipeline(cfg, gaitbase=GaitBaseAdapter(fake_backend))
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    mask = np.zeros((100, 50), dtype=np.uint8)
    mask[10:90, 15:35] = 255

    for i in range(4):
        pipe.update(3, i, crop)
        result = pipe.update_silhouette(3, i, mask)

    assert result.status == "inferred"
    assert result.embedding.shape == (8,)
    assert result.diagnostics["sequence_shape"] == [4, 64, 64]


def test_invalid_silhouette_is_rejected():
    cfg = GaitConfig(sequence_length=2, min_valid_frames=2)
    pipe = GaitPipeline(cfg)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    pipe.update(4, 0, crop)

    empty = np.zeros((100, 50), dtype=np.uint8)
    result = pipe.update_silhouette(4, 0, empty)

    assert result.status == "invalid_silhouette"


def test_discontinuous_silhouette_sequence_is_not_inferred():
    cfg = GaitConfig(sequence_length=3, min_valid_frames=3, max_frame_gap=2)
    pipe = GaitPipeline(cfg, gaitbase=GaitBaseAdapter(fake_backend))
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    mask = np.zeros((100, 50), dtype=np.uint8)
    mask[10:90, 15:35] = 255

    for frame in (0, 1, 5):
        pipe.update(9, frame, crop)
        result = pipe.update_silhouette(9, frame, mask)

    assert result.status == "track_discontinuity"


def test_gaitbase_backend_is_explicitly_required_for_inference():
    cfg = GaitConfig(sequence_length=1, min_valid_frames=1)
    pipe = GaitPipeline(cfg)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    mask = np.zeros((100, 50), dtype=np.uint8)
    mask[10:90, 15:35] = 255

    pipe.update(11, 0, crop)

    result = pipe.update_silhouette(11, 0, mask)
    assert result.status == "gaitbase_unconfigured"
    assert "GaitBase backend is not configured" in result.diagnostics["error"]


def test_silhouette_must_match_a_tracked_frame():
    cfg = GaitConfig(sequence_length=2, min_valid_frames=1)
    pipe = GaitPipeline(cfg)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    mask = np.zeros((100, 50), dtype=np.uint8)
    mask[10:90, 15:35] = 255

    pipe.update(12, 10, crop)
    result = pipe.update_silhouette(12, 11, mask)

    assert result.status == "orphan_silhouette"


if __name__ == "__main__":
    test_sequence_collection()
    test_silhouette_normalization_and_inference()
    test_invalid_silhouette_is_rejected()
    test_discontinuous_silhouette_sequence_is_not_inferred()
    test_gaitbase_backend_is_explicitly_required_for_inference()
    print("Gait tests passed.")
