from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from .config import ObjectConfig
from .crop import PersonCropper
from .types import FrameObservation, PersonObservation


class ObjectTrackingPipeline:
    """YOLO11 person detection with BoT-SORT track continuity.

    ``master_id`` is the BoT-SORT track reference used to connect observations
    belonging to the same trajectory. It is deliberately not treated as a
    resolved biometric identity.
    """

    def __init__(
        self,
        config: ObjectConfig,
        cropper: Optional[PersonCropper] = None,
    ) -> None:
        config.validate_files()

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required for the object module. "
                "Install the project requirements first."
            ) from exc

        self.config = config
        self.model = YOLO(str(config.person_weights))
        self.cropper = cropper or PersonCropper(
            padding=config.crop_padding,
            min_width=config.min_crop_width,
            min_height=config.min_crop_height,
        )

    def track_video(self, video_path: Path) -> Iterator[FrameObservation]:
        """Yield tracked person observations frame-by-frame."""
        import cv2

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30.0
        capture.release()

        results = self.model.track(
            source=str(video_path),
            tracker=str(self.config.tracker_config),
            classes=[self.config.person_class_id],
            conf=self.config.person_confidence,
            device=self.config.device,
            stream=True,
            persist=True,
            save=False,
            show=False,
            verbose=False,
        )

        for frame_index, result in enumerate(results):
            frame = result.orig_img
            timestamp_ms = (frame_index / fps) * 1000.0
            people = []

            boxes = getattr(result, "boxes", None)
            if boxes is not None and len(boxes) > 0 and boxes.id is not None:
                xyxy = boxes.xyxy.cpu().numpy()
                ids = boxes.id.int().cpu().numpy()
                confs = boxes.conf.cpu().numpy()

                for box, track_id, confidence in zip(xyxy, ids, confs):
                    crop = self.cropper.crop(frame, box)
                    people.append(
                        PersonObservation(
                            master_id=int(track_id),
                            person_box=tuple(float(v) for v in box),
                            confidence=float(confidence),
                            frame_index=frame_index,
                            timestamp_ms=timestamp_ms,
                            crop=crop,
                        )
                    )

            yield FrameObservation(
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                frame=frame,
                people=people,
            )
