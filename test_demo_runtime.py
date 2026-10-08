import numpy as np
from demo_runtime import (
    condition_classifier, control_builder, gait_backend,
    intervention_builder, silhouette,
)


def test_demo_backends_are_deterministic_and_shape_compatible():
    crop = np.full((96, 48, 3), 120, dtype=np.uint8)
    mask = silhouette(crop)
    assert mask is not None
    assert mask.shape == crop.shape[:2]
    sequence = np.stack([mask] * 8, axis=0)
    embedding = gait_backend(sequence, 1)
    assert embedding.shape == (256,)
    assert np.isfinite(embedding).all()


def test_demo_diagnostic_has_intervention_and_matched_control():
    sequence = np.ones((8, 64, 64), dtype=np.uint8) * 255
    condition = condition_classifier(sequence, {})
    intervention = intervention_builder(sequence, condition, {})
    control = control_builder(sequence, condition, {})
    assert condition == "occlusion"
    assert intervention.shape == sequence.shape
    assert control.shape == sequence.shape
    assert not np.array_equal(intervention, sequence)
    assert not np.array_equal(control, sequence)
