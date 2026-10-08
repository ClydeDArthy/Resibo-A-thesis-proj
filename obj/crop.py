from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np


class PersonCropper:
    """Extract clean person crops from tracked bounding boxes."""

    def __init__(
        self,
        padding: float = 0.0,
        min_width: int = 16,
        min_height: int = 32,
    ) -> None:
        self.padding = float(max(0.0, padding))
        self.min_width = int(min_width)
        self.min_height = int(min_height)

    def crop(
        self,
        frame: np.ndarray,
        box: Tuple[float, float, float, float],
    ) -> Optional[np.ndarray]:
        if frame is None or frame.size == 0:
            return None

        height, width = frame.shape[:2]
        x1, y1, x2, y2 = map(float, box)

        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)

        x1 -= bw * self.padding
        x2 += bw * self.padding
        y1 -= bh * self.padding
        y2 += bh * self.padding

        ix1 = max(0, min(width - 1, int(round(x1))))
        iy1 = max(0, min(height - 1, int(round(y1))))
        ix2 = max(ix1 + 1, min(width, int(round(x2))))
        iy2 = max(iy1 + 1, min(height, int(round(y2))))

        if ix2 - ix1 < self.min_width or iy2 - iy1 < self.min_height:
            return None

        crop = frame[iy1:iy2, ix1:ix2]
        return crop.copy() if crop.size else None

    @staticmethod
    def save(crop: np.ndarray, path: Path) -> bool:
        if crop is None or crop.size == 0:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        return bool(cv2.imwrite(str(path), crop))
