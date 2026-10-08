from pathlib import Path

import numpy as np

from obj.config import ObjectConfig
from obj.crop import PersonCropper


def test_cropper():
    frame = np.zeros((100, 80, 3), dtype=np.uint8)
    crop = PersonCropper().crop(frame, (10, 10, 40, 80))
    assert crop is not None
    assert crop.shape == (70, 30, 3)


def test_cropper_rejects_tiny_crop():
    frame = np.zeros((100, 80, 3), dtype=np.uint8)
    crop = PersonCropper(min_width=16, min_height=32).crop(frame, (1, 1, 8, 20))
    assert crop is None


def test_default_tracker_contract_does_not_require_local_yaml():
    config = ObjectConfig(person_weights=Path(__file__))
    config.validate_files()


def test_custom_tracker_path_is_validated(tmp_path):
    config = ObjectConfig(
        person_weights=Path(__file__),
        tracker_config=tmp_path / "missing.yaml",
    )
    try:
        config.validate_files()
    except FileNotFoundError as exc:
        assert "BoT-SORT configuration not found" in str(exc)
    else:
        raise AssertionError("missing custom tracker config must fail")


def test_invalid_crop_stride_is_rejected():
    try:
        ObjectConfig(crop_stride=0)
    except ValueError as exc:
        assert "crop_stride" in str(exc)
    else:
        raise AssertionError("crop_stride=0 must fail")


if __name__ == "__main__":
    test_cropper()
    test_cropper_rejects_tiny_crop()
    test_default_tracker_contract_does_not_require_local_yaml()
    test_custom_tracker_path_is_validated(Path("."))
    test_invalid_crop_stride_is_rejected()
    print("OBJ tests passed.")
