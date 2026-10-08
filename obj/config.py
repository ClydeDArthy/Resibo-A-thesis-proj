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

    save_crops: bool = True
    crop_stride: int = 1
    crop_padding: float = 0.0
    min_crop_width: int = 16
    min_crop_height: int = 32

    def __post_init__(self):
        if not 0.0 <= self.person_confidence <= 1.0:
            raise ValueError("person_confidence must be in [0, 1]")
        if self.person_class_id < 0:
            raise ValueError("person_class_id cannot be negative")
        if self.crop_stride <= 0:
            raise ValueError("crop_stride must be positive")
        if self.crop_padding < 0:
            raise ValueError("crop_padding cannot be negative")
        if self.min_crop_width <= 0 or self.min_crop_height <= 0:
            raise ValueError("minimum crop dimensions must be positive")

    def validate_files(self) -> None:
        weights = str(self.person_weights)
        # Official Ultralytics weights (e.g. yolo11s.pt) are allowed to be
        # resolved/downloaded by Ultralytics on first model construction.
        # Custom checkpoints must exist locally.
        official = Path(weights).name in {
            "yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt", "yolo11x.pt"
        }
        if not Path(weights).is_file() and not official:
            raise FileNotFoundError(
                f"YOLO11 person checkpoint not found: {self.person_weights}"
            )
        if str(self.tracker_config) != "botsort.yaml" and not Path(self.tracker_config).is_file():
            raise FileNotFoundError(
                f"BoT-SORT configuration not found: {self.tracker_config}"
            )
