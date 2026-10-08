import numpy as np

from resibo import BiometricObservation
from resibo.runtime import ResiboRuntime


class FakeGaitStage:
    def __init__(self):
        self.calls = 0
        self.gait_results = None

    def update(self, master_id, frame_index, person_crop):
        self.calls += 1

    def update_silhouette(self, master_id, frame_index, silhouette):
        class Result:
            status = "inferred"
            embedding = np.array([1.0, 0.0], dtype=np.float32)
            frame_count = 1
        self.gait_results = Result()
        return self.gait_results


def test_runtime_accepts_live_face_observation():
    runtime = ResiboRuntime()
    obs = BiometricObservation(4, "face", "A", 0.8, quality=0.9)
    runtime.update_face_observation(obs)
    assert runtime.get(4).face.candidate_id == "A"


def test_runtime_retains_inferred_gait_result():
    stage = FakeGaitStage()

    def silhouette(_):
        return np.ones((64, 64), dtype=np.uint8) * 255

    runtime = ResiboRuntime(
        gait_stage=stage,
        silhouette_extractor=silhouette,
    )
    runtime.process_person(4, 10, np.ones((100, 50, 3), dtype=np.uint8))
    assert 4 in runtime.gait_results
    assert runtime.gait_results[4].status == "inferred"
