from typing import Any, Dict, Optional

from .config import ResiboConfig
from .diagnostic import DiagnosticRequest, DiagnosticFn, no_diagnostic
from .fusion import fuse_scores
from .resolver import Resolver
from .types import BiometricObservation, ResolutionResult


class ResiboPipeline:
    """Central multimodal comparison and decision-triggered diagnostic loop."""

    def __init__(self, config: Optional[ResiboConfig] = None,
                 diagnostic: Optional[DiagnosticFn] = None):
        self.config = config or ResiboConfig()
        self.resolver = Resolver(self.config)
        self.diagnostic = diagnostic or no_diagnostic

    def compare(
        self,
        master_id: int,
        candidate_id: Optional[str],
        face: Optional[BiometricObservation],
        gait: Optional[BiometricObservation],
        context: Optional[Dict[str, Any]] = None,
    ) -> ResolutionResult:
        context = context or {}

        face_score = face.score if face else None
        gait_score = gait.score if gait else None
        face_quality = face.quality if face else 0.0
        gait_quality = gait.quality if gait else 0.0

        raw = fuse_scores(
            face_score,
            gait_score,
            face_quality,
            gait_quality,
            self.config.face_weight,
            self.config.gait_weight,
        )

        initial = self.resolver.resolve(
            master_id=master_id,
            candidate_id=candidate_id,
            face_score=face_score,
            gait_score=gait_score,
            face_quality=face_quality,
            gait_quality=gait_quality,
            raw_fused_score=raw,
        )

        # A diagnostic branch is requested only when the initial multimodal
        # comparison is structurally problematic. It is not an automatic
        # GaitBase rerun.
        if initial.state != "contradiction":
            return initial

        request = DiagnosticRequest(
            master_id=master_id,
            face_score=face_score,
            gait_score=gait_score,
            context=context,
        )
        diagnostic = self.diagnostic(request)

        if not diagnostic.triggered or diagnostic.revised_gait_score is None:
            initial.diagnostic_triggered = True
            initial.diagnostic = diagnostic.details or {}
            return initial

        revised = fuse_scores(
            face_score,
            diagnostic.revised_gait_score,
            face_quality,
            gait_quality,
            self.config.face_weight,
            self.config.gait_weight,
        )

        details = dict(diagnostic.details or {})
        details.update({
            "condition": diagnostic.condition,
            "sensitivity": diagnostic.sensitivity,
            "raw_gait_score": gait_score,
            "revised_gait_score": diagnostic.revised_gait_score,
            "raw_fused_score": raw,
            "reanalysis_fused_score": revised,
        })

        return self.resolver.resolve(
            master_id=master_id,
            candidate_id=candidate_id,
            face_score=face_score,
            gait_score=diagnostic.revised_gait_score,
            face_quality=face_quality,
            gait_quality=gait_quality,
            diagnostic_triggered=True,
            raw_fused_score=raw,
            reanalysis_fused_score=revised,
            diagnostic=details,
        )
