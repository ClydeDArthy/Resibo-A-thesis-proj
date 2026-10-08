"""Runtime handoff between tracked observations, biometrics, and RESIBO.

The coordinator deliberately keeps model-specific work injectable. OBJ owns
tracking, FR owns face recognition, Gait owns gait representation, and RESIBO
owns multimodal resolution.
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np

from .fr_adapter import FRCandidateStore
from .types import BiometricObservation, ResolutionResult
from .pipeline import ResiboPipeline

GaitScorer = Callable[[int, np.ndarray], Optional[BiometricObservation]]
SilhouetteExtractor = Callable[[np.ndarray], Optional[np.ndarray]]


@dataclass
class RuntimeTrackState:
    face: Optional[BiometricObservation] = None
    gait: Optional[BiometricObservation] = None
    resolution: Optional[ResolutionResult] = None


class ResiboRuntime:
    """Coordinate per-track handoff without moving model logic into RESIBO."""

    def __init__(
        self,
        resolver: Optional[ResiboPipeline] = None,
        fr_store: Optional[FRCandidateStore] = None,
        silhouette_extractor: Optional[SilhouetteExtractor] = None,
        gait_scorer: Optional[GaitScorer] = None,
    ):
        self.resolver = resolver or ResiboPipeline()
        self.fr_store = fr_store
        self.silhouette_extractor = silhouette_extractor
        self.gait_scorer = gait_scorer
        self.tracks: Dict[int, RuntimeTrackState] = {}

    def _state(self, master_id: int) -> RuntimeTrackState:
        return self.tracks.setdefault(master_id, RuntimeTrackState())

    def update_face(self, master_id: int, quality: float = 1.0) -> Optional[BiometricObservation]:
        if self.fr_store is None:
            return None
        candidates = self.fr_store.candidates_for_track(str(master_id))
        if not candidates:
            return None
        observation = self.fr_store.observation_from_candidate(
            candidates[0], master_id=master_id, quality=quality
        )
        self._state(master_id).face = observation
        return observation

    def update_gait(
        self,
        master_id: int,
        embedding: np.ndarray,
    ) -> Optional[BiometricObservation]:
        if self.gait_scorer is None:
            return None
        observation = self.gait_scorer(master_id, embedding)
        if observation is not None:
            if observation.master_id != master_id or observation.modality != "gait":
                raise ValueError("gait_scorer must return a gait observation for the same master_id")
            self._state(master_id).gait = observation
        return observation

    def update_track(
        self,
        master_id: int,
        person_crop: np.ndarray,
        gait_embedding: Optional[np.ndarray] = None,
        face_quality: float = 1.0,
    ) -> Optional[ResolutionResult]:
        """Advance one track and resolve when usable modalities are available.

        The silhouette extractor is an optional hook for the Gait stage; it is
        called here only to provide the next-stage input and never converted
        into a hidden gait decision.
        """
        if self.silhouette_extractor is not None:
            self.silhouette_extractor(person_crop)

        if self.fr_store is not None:
            self.update_face(master_id, quality=face_quality)

        if gait_embedding is not None:
            self.update_gait(master_id, gait_embedding)

        state = self._state(master_id)
        if state.face is None and state.gait is None:
            return None

        candidate_id = state.face.candidate_id if state.face else state.gait.candidate_id
        state.resolution = self.resolver.compare(
            master_id=master_id,
            candidate_id=candidate_id,
            face=state.face,
            gait=state.gait,
        )
        return state.resolution

    def get(self, master_id: int) -> RuntimeTrackState:
        return self._state(master_id)

    def clear(self, master_id: int) -> None:
        self.tracks.pop(master_id, None)
