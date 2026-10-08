import numpy as np

from obj.crop import PersonCropper


def test_cropper():
    frame = np.zeros((100, 80, 3), dtype=np.uint8)
    crop = PersonCropper().crop(frame, (10, 10, 40, 80))
    assert crop is not None
    assert crop.shape == (70, 30, 3)


if __name__ == "__main__":
    test_cropper()
    print("OBJ basic test passed.")
