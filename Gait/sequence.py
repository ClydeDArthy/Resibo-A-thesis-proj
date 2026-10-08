from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class GaitObservation:
    frame_index: int
    person_crop: np.ndarray


class TrackSequenceBuffer:
    """Stores observations independently for each BoT-SORT master_id."""

    def __init__(self, maxlen: int = 64):
        self.maxlen = maxlen
        self._tracks: Dict[int, deque] = {}

    def append(self, master_id: int, frame_index: int, person_crop: np.ndarray) -> None:
        if person_crop is None or person_crop.size == 0:
            return
        track = self._tracks.setdefault(master_id, deque(maxlen=self.maxlen))
        track.append(GaitObservation(frame_index, person_crop.copy()))

    def get(self, master_id: int) -> List[GaitObservation]:
        return list(self._tracks.get(master_id, ()))

    def clear(self, master_id: int) -> None:
        self._tracks.pop(master_id, None)

    def continuity(self, master_id: int, max_gap: int = 3) -> Tuple[bool, Optional[int]]:
        observations = self.get(master_id)
        if len(observations) < 2:
            return True, None

        gaps = [b.frame_index - a.frame_index for a, b in zip(observations, observations[1:])]
        largest = max(gaps)
        return largest <= max_gap, largest

    def ready(self, master_id: int, required_frames: int) -> bool:
        return len(self._tracks.get(master_id, ())) >= required_frames
