import json
from pathlib import Path
from typing import Callable, Optional

from .pipeline import ObjectTrackingPipeline
from .types import FrameObservation, TrackSummary


class ObjectRunner:
    """Run OBJ, persist crops/track metadata, and dispatch downstream stages."""

    def __init__(self, pipeline: ObjectTrackingPipeline):
        self.pipeline = pipeline

    def run(
        self,
        video_path: Path,
        output_dir: Path,
        gait_module: Optional[Callable[..., object]] = None,
        face_module: Optional[Callable[..., object]] = None,
        on_frame: Optional[Callable[[FrameObservation], None]] = None,
    ) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        tracks = {}
        frame_count = 0

        try:
            for observation in self.pipeline.track_video(video_path):
                frame_count = observation.frame_index + 1
                for person in observation.people:
                    summary = tracks.get(person.master_id)
                    if summary is None:
                        summary = TrackSummary(
                            master_id=person.master_id,
                            first_frame=person.frame_index,
                            last_frame=person.frame_index,
                            observation_count=0,
                        )
                        tracks[person.master_id] = summary

                    summary.last_frame = person.frame_index
                    summary.observation_count += 1

                    if (
                        self.pipeline.config.save_crops
                        and person.crop is not None
                        and person.frame_index % max(1, self.pipeline.config.crop_stride) == 0
                    ):
                        crop_path = (
                            output_dir / "crops"
                            / ("master_{:04d}".format(person.master_id))
                            / ("frame_{:08d}.jpg".format(person.frame_index))
                        )
                        if self.pipeline.cropper.save(person.crop, crop_path):
                            summary.crop_count += 1

                if gait_module is not None or face_module is not None:
                    from .integration import dispatch_frame
                    dispatch_frame(
                        observation,
                        gait_module=gait_module,
                        face_module=face_module,
                    )

                if on_frame is not None:
                    on_frame(observation)

            result = {
                "source_path": str(video_path),
                "output_dir": str(output_dir),
                "frame_count": frame_count,
                "tracks": {str(k): v.__dict__ for k, v in tracks.items()},
                "status": "completed",
                "error": None,
            }
        except Exception as exc:
            result = {
                "source_path": str(video_path),
                "output_dir": str(output_dir),
                "frame_count": frame_count,
                "tracks": {str(k): v.__dict__ for k, v in tracks.items()},
                "status": "error",
                "error": str(exc),
            }

        with (output_dir / "tracks.json").open("w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)

        if result["status"] == "error":
            raise RuntimeError(result["error"])
        return result
