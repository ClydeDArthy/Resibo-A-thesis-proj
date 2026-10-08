from typing import Optional

from .config import ResiboConfig
from .fusion import fuse_scores
from .types import ResolutionResult


class Resolver:
    def __init__(self, config: ResiboConfig):
        config.validate()
        self.config = config

    def resolve(
        self,
        master_id: int,
        candidate_id: Optional[str],
        face_score: Optional[float],
        gait_score: Optional[float],
        face_quality: float = 1.0,
        gait_quality: float = 1.0,
        diagnostic_triggered: bool = False,
        raw_fused_score: Optional[float] = None,
        reanalysis_fused_score: Optional[float] = None,
        diagnostic=None,
    ) -> ResolutionResult:
        fused = reanalysis_fused_score if reanalysis_fused_score is not None else raw_fused_score

        if fused is None:
            state = "unresolved"
        elif face_score is not None and gait_score is not None:
            disagreement = abs(float(face_score) - float(gait_score))
            if disagreement >= self.config.contradiction_margin:
                state = "contradiction" if not diagnostic_triggered else (
                    "resolved" if fused >= self.config.minimum_accept_score else "ambiguous"
                )
            else:
                state = "resolved" if fused >= self.config.minimum_accept_score else "ambiguous"
        else:
            state = "resolved" if fused >= self.config.minimum_accept_score else "ambiguous"

        return ResolutionResult(
            master_id=master_id,
            state=state,
            candidate_id=candidate_id,
            fused_score=fused,
            face_score=face_score,
            gait_score=gait_score,
            diagnostic_triggered=diagnostic_triggered,
            raw_fused_score=raw_fused_score,
            reanalysis_fused_score=reanalysis_fused_score,
            diagnostic=diagnostic or {},
        )
