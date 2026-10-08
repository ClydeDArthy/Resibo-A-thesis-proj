import numpy as np

from Gait import GaitConfig, GaitPipeline


def test_sequence_collection():
    cfg = GaitConfig(sequence_length=4, min_valid_frames=4)
    pipe = GaitPipeline(cfg)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    for i in range(4):
        result = pipe.update(7, i, crop)
    assert result.track_id == 7
    assert result.frame_count == 4
    assert result.status == "awaiting_silhouette"


def test_silhouette_normalization():
    cfg = GaitConfig(sequence_length=2, min_valid_frames=2)
    pipe = GaitPipeline(cfg)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    mask = np.zeros((100, 50), dtype=np.uint8)
    mask[10:90, 15:35] = 255
    pipe.update(3, 0, crop)
    pipe.update(3, 1, crop)
    pipe.update_silhouette(3, 0, mask)
    result = pipe.update_silhouette(3, 1, mask)
    assert result.status == "inferred" or result.status.startswith("collecting")
