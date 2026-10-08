"""Minimal detector integration example.

This is intentionally separate from the existing detection notebook so the
working detector is not modified until the gait input contract is verified.
"""

from Gait import GaitPipeline


gait_pipeline = GaitPipeline()


def gait_module(person_crop, master_id, frame_index):
    return gait_pipeline.update(
        master_id=master_id,
        frame_index=frame_index,
        person_crop=person_crop,
    )
