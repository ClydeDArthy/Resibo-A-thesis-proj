from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np

from .config import GaitConfig
from .gaitbase import GaitBaseAdapter, GaitEmbedding
from .preprocessing import SilhouettePreprocessor
from .sequence import TrackSequenceBuffer


@dataclass
class GaitResult:
    track_id: int
    status: str
    frame_count: int
    embedding: Optional[np.ndarray] = None
    model: str = "GaitBase"
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class GaitPipeline:
    """Detector-facing gait stage.

    The detector calls ``update(master_id, frame_index, person_crop)`` for each
    tracked person.  A separate ``update_silhouette`` call supplies the
    validated silhouette corresponding to the same observation.
    """

    def __init__(self, config: Optional[GaitConfig] = None,
                 gaitbase: Optional[GaitBaseAdapter] = None):
        self.config = config or GaitConfig()
        self.sequences = TrackSequenceBuffer(self.config.sequence_length)
        self.preprocessor = SilhouettePreprocessor(
            width=self.config.silhouette_width,
            height=self.config.silhouette_height,
            min_foreground_ratio=self.config.min_foreground_ratio,
            max_foreground_ratio=self.config.max_foreground_ratio,
        )
        self.gaitbase = gaitbase or GaitBaseAdapter()
        self._silhouettes: Dict[int, Dict[int, np.ndarray]] = {}

    def update(self, master_id: int, frame_index: int, person_crop: np.ndarray) -> GaitResult:
        """Record the detector crop. No gait inference is attempted from RGB."""
        self.sequences.append(master_id, frame_index, person_crop)
        count = len(self.sequences.get(master_id))
        continuous, largest_gap = self.sequences.continuity(
            master_id, self.config.max_frame_gap
        )
        return GaitResult(
            track_id=master_id,
            status="collecting" if count < self.config.min_valid_frames else "awaiting_silhouette",
            frame_count=count,
            diagnostics={
                "largest_frame_gap": largest_gap,
                "track_continuous": continuous,
            },
        )

    def update_silhouette(self, master_id: int, frame_index: int,
                          silhouette: np.ndarray) -> GaitResult:
        """Add one validated silhouette and infer once a full window is ready."""
        item = self.preprocessor.normalize(silhouette)
        count = len(self.sequences.get(master_id))
        if item is None:
            return GaitResult(
                track_id=master_id,
                status="invalid_silhouette",
                frame_count=count,
                diagnostics={"frame_index": frame_index},
            )

        observations = {obs.frame_index for obs in self.sequences.get(master_id)}
        if frame_index not in observations:
            return GaitResult(
                track_id=master_id,
                status="orphan_silhouette",
                frame_count=count,
                diagnostics={"frame_index": frame_index},
            )

        bucket = self._silhouettes.setdefault(master_id, {})
        bucket[frame_index] = item.mask

        # Keep masks aligned to the frames still retained by the RGB track window.
        current_frames = sorted(observations)
        bucket = {frame: bucket[frame] for frame in current_frames if frame in bucket}
        self._silhouettes[master_id] = bucket

        continuous, largest_gap = self.sequences.continuity(
            master_id, self.config.max_frame_gap
        )

        ordered_frames = sorted(bucket)
        if len(ordered_frames) < self.config.min_valid_frames:
            return GaitResult(
                track_id=master_id,
                status="collecting_silhouettes",
                frame_count=count,
                diagnostics={
                    "valid_silhouettes": len(ordered_frames),
                    "largest_frame_gap": largest_gap,
                    "track_continuous": continuous,
                },
            )

        if not continuous:
            return GaitResult(
                track_id=master_id,
                status="track_discontinuity",
                frame_count=count,
                diagnostics={"largest_frame_gap": largest_gap},
            )

        sequence = np.stack([bucket[frame] for frame in ordered_frames[-self.config.sequence_length:]], axis=0)
        embedding: GaitEmbedding = self.gaitbase.infer(sequence, master_id)
        return GaitResult(
            track_id=master_id,
            status="inferred",
            frame_count=count,
            embedding=embedding.embedding,
            diagnostics={
                "valid_silhouettes": len(bucket),
                "sequence_shape": list(sequence.shape),
            },
        )

    def clear(self, master_id: int) -> None:
        self.sequences.clear(master_id)
        self._silhouettes.pop(master_id, None)
