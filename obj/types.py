from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

Box = Tuple[float, float, float, float]


@dataclass
class PersonObservation:
    """One tracked person observation in one video frame."""

    master_id: int
    person_box: Box
    confidence: float
    frame_index: int
    timestamp_ms: float
    crop: Optional[np.ndarray] = None


@dataclass
class FrameObservation:
    """All tracked-person observations for one frame."""

    frame_index: int
    timestamp_ms: float
    frame: np.ndarray
    people: list[PersonObservation]
