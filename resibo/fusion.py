from typing import Optional


def _effective(score: Optional[float], quality: float) -> Optional[float]:
    if score is None:
        return None
    return max(0.0, min(1.0, float(score))) * max(0.0, min(1.0, float(quality)))


def fuse_scores(
    face_score: Optional[float],
    gait_score: Optional[float],
    face_quality: float = 1.0,
    gait_quality: float = 1.0,
    face_weight: float = 0.5,
    gait_weight: float = 0.5,
) -> Optional[float]:
    """Quality-weighted score fusion without inventing a missing modality."""

    values = []
    weights = []

    if face_score is not None:
        values.append(_effective(face_score, face_quality))
        weights.append(max(0.0, face_weight))

    if gait_score is not None:
        values.append(_effective(gait_score, gait_quality))
        weights.append(max(0.0, gait_weight))

    total = sum(weights)
    if total <= 0 or not values:
        return None
    return sum(v * w for v, w in zip(values, weights)) / total
