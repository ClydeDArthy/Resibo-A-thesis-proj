from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BiometricObservation:
    """One modality result associated with a master_id."""

    master_id: int
    modality: str
    candidate_id: Optional[str]
    score: Optional[float]
    quality: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionResult:
    master_id: int
    state: str
    candidate_id: Optional[str]
    fused_score: Optional[float]
    face_score: Optional[float]
    gait_score: Optional[float]
    diagnostic_triggered: bool = False
    raw_fused_score: Optional[float] = None
    reanalysis_fused_score: Optional[float] = None
    diagnostic: Dict[str, Any] = field(default_factory=dict)
