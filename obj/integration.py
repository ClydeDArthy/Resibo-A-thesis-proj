"""Small integration helpers for connecting OBJ to Gait/FE/RESIBO."""

from typing import Any, Callable, Optional

from .types import FrameObservation


def dispatch_frame(
    observation: FrameObservation,
    gait_module: Optional[Callable[..., Any]] = None,
    face_module: Optional[Callable[..., Any]] = None,
) -> None:
    """Send each tracked person to downstream modules without deciding identity."""

    for person in observation.people:
        if gait_module is not None and person.crop is not None:
            gait_module(
                person_crop=person.crop,
                master_id=person.master_id,
                frame_index=person.frame_index,
            )

        # FE/face processing can consume the same master_id through its own
        # existing interface. No face result is interpreted here.
        if face_module is not None:
            face_module(
                frame=observation.frame,
                person_box=person.person_box,
                master_id=person.master_id,
                frame_index=person.frame_index,
            )
