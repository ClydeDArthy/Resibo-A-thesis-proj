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


@dataclass
class TrackSummary:
    """Aggregated metadata for one BoT-SORT master_id trajectory."""

    master_id: int
    first_frame: int
    last_frame: int
    observation_count: int = 0
    crop_count: int = 0
