from dataclasses import dataclass


@dataclass
class ResiboConfig:
    """Configurable decision parameters; values are experimental, not universal."""

    face_weight: float = 0.5
    gait_weight: float = 0.5

    # A low score is not automatically a contradiction. These parameters
    # only define when the prototype requests additional diagnostic analysis.
    contradiction_margin: float = 0.25
    minimum_accept_score: float = 0.60

    def validate(self) -> None:
        if self.face_weight < 0 or self.gait_weight < 0:
            raise ValueError("modality weights cannot be negative")
        if self.face_weight + self.gait_weight <= 0:
            raise ValueError("at least one modality weight is required")
        if not 0 <= self.minimum_accept_score <= 1:
            raise ValueError("minimum_accept_score must be in [0, 1]")
        if not 0 <= self.contradiction_margin <= 1:
            raise ValueError("contradiction_margin must be in [0, 1]")
