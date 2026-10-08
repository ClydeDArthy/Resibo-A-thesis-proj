from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class SilhouetteFrame:
    mask: np.ndarray
    foreground_ratio: float


class SilhouettePreprocessor:
    """Validate and normalize externally supplied person silhouettes.

    GaitBase is an appearance-based gait model operating on silhouette
    sequences.  This class deliberately does not guess a silhouette from an
    RGB crop.  The detector's RGB crop and the gait silhouette are separate
    inputs until a validated silhouette extractor is connected.
    """

    def __init__(self, width: int = 64, height: int = 64,
                 min_foreground_ratio: float = 0.05,
                 max_foreground_ratio: float = 0.90):
        self.width = width
        self.height = height
        self.min_foreground_ratio = min_foreground_ratio
        self.max_foreground_ratio = max_foreground_ratio

    def normalize(self, mask: np.ndarray) -> Optional[SilhouetteFrame]:
        if mask is None or mask.size == 0:
            return None

        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

        mask = (mask > 0).astype(np.uint8) * 255
        ratio = float(np.count_nonzero(mask)) / float(mask.shape[0] * mask.shape[1])
        if not self.min_foreground_ratio <= ratio <= self.max_foreground_ratio:
            return None

        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            return None

        x1, x2 = int(xs.min()), int(xs.max()) + 1
        y1, y2 = int(ys.min()), int(ys.max()) + 1
        cropped = mask[y1:y2, x1:x2]
        resized = cv2.resize(cropped, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
        normalized = (resized > 0).astype(np.uint8)
        normalized_ratio = float(np.count_nonzero(normalized)) / normalized.size
        return SilhouetteFrame(normalized, normalized_ratio)

    def stack(self, masks: list[np.ndarray]) -> np.ndarray:
        frames = []
        for mask in masks:
            item = self.normalize(mask)
            if item is not None:
                frames.append(item.mask)
        if not frames:
            raise ValueError("No valid silhouette frames were supplied")
        return np.stack(frames, axis=0).astype(np.uint8)
