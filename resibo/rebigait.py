"""ReBiGait: decision-triggered, condition-aware gait re-analysis.

The module preserves the baseline comparison and, only after RESIBO detects
face/gait disagreement, evaluates an intervention against a matched control.
It never fabricates a condition or a gait score.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Sequence
import numpy as np


@dataclass
class ReBiGaitComparison:
    candidate_id: Optional[str]
    score: Optional[float]
    representation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReBiGaitResult:
    triggered: bool
    condition: Optional[str] = None
    baseline: Optional[ReBiGaitComparison] = None
    intervention: Optional[ReBiGaitComparison] = None
    control: Optional[ReBiGaitComparison] = None
    intervention_effect: Optional[float] = None
    control_effect: Optional[float] = None
    sensitivity: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


class ReBiGait:
    def __init__(
        self,
        gait_model: Callable,
        compare_embedding: Callable,
        condition_classifier: Optional[Callable] = None,
        intervention_builder: Optional[Callable] = None,
        control_builder: Optional[Callable] = None,
    ):
        self.gait_model = gait_model
        self.compare_embedding = compare_embedding
        self.condition_classifier = condition_classifier
        self.intervention_builder = intervention_builder
        self.control_builder = control_builder

    def _comparison(self, sequence, representation):
        embedding = self.gait_model(sequence)
        candidate_id, score = self.compare_embedding(embedding)
        return ReBiGaitComparison(
            candidate_id=candidate_id,
            score=float(score) if score is not None else None,
            representation=representation,
        )

    def diagnose(self, sequence: Sequence, context: Dict[str, Any]):
        if self.condition_classifier is None:
            return None
        condition = self.condition_classifier(sequence, context)
        return str(condition) if condition else None

    def run(
        self,
        sequence: Sequence,
        baseline: ReBiGaitComparison,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReBiGaitResult:
        context = dict(context or {})

        condition = self.diagnose(sequence, context)
        if condition is None:
            return ReBiGaitResult(
                triggered=True,
                baseline=baseline,
                details={"reason": "diagnostic_backend_not_configured"},
            )

        if self.intervention_builder is None or self.control_builder is None:
            return ReBiGaitResult(
                triggered=True,
                condition=condition,
                baseline=baseline,
                details={"reason": "intervention_or_control_backend_not_configured"},
            )

        intervention_sequence = self.intervention_builder(
            sequence, condition, context
        )
        control_sequence = self.control_builder(
            sequence, condition, context
        )

        intervention = self._comparison(
            intervention_sequence,
            representation=f"intervention:{condition}",
        )
        control = self._comparison(
            control_sequence,
            representation=f"control:{condition}",
        )

        if baseline.score is None or intervention.score is None or control.score is None:
            return ReBiGaitResult(
                triggered=True,
                condition=condition,
                baseline=baseline,
                intervention=intervention,
                control=control,
                details={"reason": "incomplete_comparison"},
            )

        intervention_effect = intervention.score - baseline.score
        control_effect = control.score - baseline.score
        sensitivity = intervention_effect - control_effect

        return ReBiGaitResult(
            triggered=True,
            condition=condition,
            baseline=baseline,
            intervention=intervention,
            control=control,
            intervention_effect=float(intervention_effect),
            control_effect=float(control_effect),
            sensitivity=float(sensitivity),
            details={
                "baseline_score": baseline.score,
                "intervention_score": intervention.score,
                "control_score": control.score,
                "intervention_effect": float(intervention_effect),
                "control_effect": float(control_effect),
                "sensitivity": float(sensitivity),
            },
        )
