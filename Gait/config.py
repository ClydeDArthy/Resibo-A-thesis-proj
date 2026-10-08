from dataclasses import dataclass
from pathlib import Path


@dataclass
class GaitConfig:
    """Runtime settings for the first RESIBO gait stage.

    The 64-frame buffer matches the existing detector handoff.  It is a
    collection window, not a claim that 64 frames is a universal recognition
    threshold.
    """

    sequence_length: int = 64
    silhouette_height: int = 64
    silhouette_width: int = 64
    min_valid_frames: int = 64
    max_frame_gap: int = 3
    min_foreground_ratio: float = 0.05
    max_foreground_ratio: float = 0.90
    output_root: Path = Path("output/gait")

    def __post_init__(self):
        if self.sequence_length <= 0:
            raise ValueError("sequence_length must be positive")
        if not 0 < self.min_valid_frames <= self.sequence_length:
            raise ValueError("min_valid_frames must be within sequence_length")
        if self.max_frame_gap < 0:
            raise ValueError("max_frame_gap cannot be negative")
        if not 0 < self.min_foreground_ratio < self.max_foreground_ratio < 1:
            raise ValueError("foreground ratio bounds must satisfy 0 < min < max < 1")
