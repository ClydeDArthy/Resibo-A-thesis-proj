"""Runtime handoff between tracked observations, biometrics, and RESIBO.

The coordinator deliberately keeps model-specific work injectable. OBJ owns
tracking, FR owns face recognition, Gait owns gait representation, and RESIBO
owns multimodal resolution.
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np
import importlib
import os

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
        gait_stage=None,
    ):
        self.fr_store = fr_store
        self.silhouette_extractor = silhouette_extractor
        self.gait_scorer = gait_scorer
        self.gait_stage = gait_stage
        self.rebigait = self._build_rebigait()
        self.resolver = resolver or ResiboPipeline(
            diagnostic=self._run_rebigait_diagnostic if self.rebigait is not None else None
        )
        self.tracks: Dict[int, RuntimeTrackState] = {}
        self.gait_results: Dict[int, object] = {}

    @staticmethod
    def _load_optional_callable(env_name):
        spec = os.getenv(env_name)
        if not spec:
            return None
        if ":" not in spec:
            raise ValueError(f"{env_name} must be module:function")
        module, function = spec.split(":", 1)
        return getattr(importlib.import_module(module), function)

    def _build_rebigait(self):
        if self.gait_stage is None or self.gait_scorer is None:
            return None
        condition = self._load_optional_callable("RESIBO_GAIT_CONDITION_CLASSIFIER")
        intervention = self._load_optional_callable("RESIBO_GAIT_INTERVENTION")
        control = self._load_optional_callable("RESIBO_GAIT_CONTROL")
        if not all((condition, intervention, control)):
            return None

        from .rebigait import ReBiGait

        def gait_model(sequence):
            result = self.gait_stage.gaitbase.infer(
                np.asarray(sequence), track_id=0
            )
            return result.embedding

        def compare_embedding(embedding):
            observation = self.gait_scorer(0, embedding)
            if observation is None:
                return None, None
            return observation.candidate_id, observation.score

        return ReBiGait(
            gait_model=gait_model,
            compare_embedding=compare_embedding,
            condition_classifier=condition,
            intervention_builder=intervention,
            control_builder=control,
        )

    def _run_rebigait_diagnostic(self, request):
        from .diagnostic import DiagnosticResult

        if self.rebigait is None or self.gait_stage is None:
            return DiagnosticResult(
                triggered=False,
                details={"reason": "ReBiGait backends are not configured."},
            )
        sequence = self.gait_stage.silhouette_sequence(request.master_id)
        if sequence is None or len(sequence) == 0:
            return DiagnosticResult(
                triggered=True,
                details={"reason": "No aligned silhouette sequence is available."},
            )
        baseline = self.rebigait._comparison(sequence, "baseline")
        if request.gait_candidate_id is not None:
            baseline.candidate_id = request.gait_candidate_id
        if request.gait_score is not None:
            baseline.score = float(request.gait_score)
        result = self.rebigait.run(sequence, baseline, request.context)
        if result.intervention is None or result.intervention.score is None:
            return DiagnosticResult(
                triggered=True,
                condition=result.condition,
                sensitivity=result.sensitivity,
                details=result.details,
            )
        return DiagnosticResult(
            triggered=True,
            condition=result.condition,
            sensitivity=result.sensitivity,
            revised_gait_score=result.intervention.score,
            details={
                **result.details,
                "baseline_candidate": result.baseline.candidate_id if result.baseline else None,
                "intervention_candidate": result.intervention.candidate_id,
                "control_candidate": result.control.candidate_id if result.control else None,
                "baseline_representation": result.baseline.representation if result.baseline else None,
                "intervention_representation": result.intervention.representation,
                "control_representation": result.control.representation if result.control else None,
            },
        )

    def _state(self, master_id: int) -> RuntimeTrackState:
        return self.tracks.setdefault(master_id, RuntimeTrackState())

    def update_face_observation(
        self,
        observation: BiometricObservation,
    ) -> BiometricObservation:
        if observation.modality != "face":
            raise ValueError("face observation must have modality='face'")
        state = self._state(observation.master_id)
        state.face = observation
        return observation

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

    def process_person(
        self,
        master_id: int,
        frame_index: int,
        person_crop: np.ndarray,
        face_quality: float = 1.0,
    ) -> Optional[ResolutionResult]:
        """Pass one tracked person through Gait and then RESIBO when possible."""
        if self.gait_stage is None:
            return self.update_track(master_id, person_crop, face_quality=face_quality)

        self.gait_stage.update(master_id, frame_index, person_crop)
        if self.silhouette_extractor is None:
            return self.update_track(master_id, person_crop, face_quality=face_quality)

        silhouette = self.silhouette_extractor(person_crop)
        if silhouette is None:
            return self.update_track(master_id, person_crop, face_quality=face_quality)

        gait_result = self.gait_stage.update_silhouette(master_id, frame_index, silhouette)
        self.gait_results[master_id] = gait_result
        if getattr(gait_result, "status", None) != "inferred":
            return self.update_track(master_id, person_crop, face_quality=face_quality)

        return self.update_track(
            master_id,
            person_crop,
            gait_embedding=gait_result.embedding,
            face_quality=face_quality,
        )

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

        state = self._state(master_id)
        if self.fr_store is not None and state.face is None:
            self.update_face(master_id, quality=face_quality)

        if gait_embedding is not None:
            self.update_gait(master_id, gait_embedding)

        state = self._state(master_id)
        if state.face is None and state.gait is None:
            return None

        candidate_id = state.face.candidate_id if state.face else state.gait.candidate_id
        context = {
            "face_metadata": dict(state.face.metadata) if state.face else {},
            "gait_metadata": dict(state.gait.metadata) if state.gait else {},
        }
        state.resolution = self.resolver.compare(
            master_id=master_id,
            candidate_id=candidate_id,
            face=state.face,
            gait=state.gait,
            context=context,
        )
        return state.resolution

    def get(self, master_id: int) -> RuntimeTrackState:
        return self._state(master_id)

    def clear(self, master_id: int) -> None:
        self.tracks.pop(master_id, None)
