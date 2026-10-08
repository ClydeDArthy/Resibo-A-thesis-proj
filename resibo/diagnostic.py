from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class DiagnosticRequest:
    master_id: int
    face_score: Optional[float]
    gait_score: Optional[float]
    context: Dict[str, Any]
    face_candidate_id: Optional[str] = None
    gait_candidate_id: Optional[str] = None


@dataclass
class DiagnosticResult:
    """Result of a condition-aware gait diagnostic branch."""

    triggered: bool
    condition: Optional[str] = None
    sensitivity: Optional[float] = None
    revised_gait_score: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


DiagnosticFn = Callable[[DiagnosticRequest], DiagnosticResult]


def no_diagnostic(request: DiagnosticRequest) -> DiagnosticResult:
    return DiagnosticResult(
        triggered=False,
        details={"reason": "No diagnostic backend configured."},
    )
