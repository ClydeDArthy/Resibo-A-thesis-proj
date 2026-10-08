from dataclasses import dataclass
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


@dataclass
class ObjectConfig:
    """Configuration for YOLO11 person detection + BoT-SORT tracking."""

    person_weights: PathLike = "yolo11s.pt"
    tracker_config: PathLike = "botsort.yaml"
    person_class_id: int = 0
    person_confidence: float = 0.35
    device: Union[int, str, None] = None
    track_buffer: int = 30

    # Person crop handling. The crop is passed to the Gait module;
    # the tracker ID remains a trajectory reference, not an identity.
    crop_padding: float = 0.0
    min_crop_width: int = 16
    min_crop_height: int = 32

    def validate_files(self) -> None:
        if not Path(self.person_weights).is_file():
            raise FileNotFoundError(
                f"YOLO11 person checkpoint not found: {self.person_weights}"
            )
        if not Path(self.tracker_config).is_file():
            raise FileNotFoundError(
                f"BoT-SORT configuration not found: {self.tracker_config}"
            )
