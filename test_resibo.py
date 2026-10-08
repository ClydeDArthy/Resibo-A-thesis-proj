from resibo import BiometricObservation, ResiboConfig, ResiboPipeline
from resibo.diagnostic import DiagnosticResult


def test_consistent_multimodal_resolution():
    pipe = ResiboPipeline(ResiboConfig(minimum_accept_score=0.60))
    result = pipe.compare(
        master_id=7,
        candidate_id="person-A",
        face=BiometricObservation(7, "face", "person-A", 0.82),
        gait=BiometricObservation(7, "gait", "person-A", 0.78),
    )
    assert result.state == "resolved"
    assert result.diagnostic_triggered is False


def test_contradiction_is_not_silently_overridden():
    pipe = ResiboPipeline(ResiboConfig(contradiction_margin=0.20))
    result = pipe.compare(
        master_id=7,
        candidate_id="person-A",
        face=BiometricObservation(7, "face", "person-A", 0.90),
        gait=BiometricObservation(7, "gait", "person-A", 0.40),
    )
    assert result.state == "contradiction"
    assert result.raw_fused_score is not None
    assert result.diagnostic_triggered is True


def test_diagnostic_reanalysis_can_resolve_when_disagreement_is_reduced():
    def diagnostic(request):
        assert request.face_candidate_id == "person-A"
        assert request.gait_candidate_id == "person-A"
        return DiagnosticResult(
            triggered=True,
            condition="carried_object",
            sensitivity=0.31,
            revised_gait_score=0.72,
            details={"source": "test"},
        )

    pipe = ResiboPipeline(
        ResiboConfig(contradiction_margin=0.20),
        diagnostic=diagnostic,
    )
    result = pipe.compare(
        master_id=7,
        candidate_id="person-A",
        face=BiometricObservation(7, "face", "person-A", 0.90),
        gait=BiometricObservation(7, "gait", "person-A", 0.40),
    )
    assert result.state == "resolved"
    assert result.diagnostic_triggered is True
    assert result.raw_fused_score < result.reanalysis_fused_score
    assert result.diagnostic["condition"] == "carried_object"


def test_candidate_identity_disagreement_remains_contradiction():
    pipe = ResiboPipeline(ResiboConfig(contradiction_margin=0.20))
    result = pipe.compare(
        master_id=7,
        candidate_id=None,
        face=BiometricObservation(7, "face", "person-A", 0.91),
        gait=BiometricObservation(7, "gait", "person-B", 0.91),
    )
    assert result.state == "contradiction"


def test_missing_modality_is_not_fabricated():
    pipe = ResiboPipeline(ResiboConfig(minimum_accept_score=0.60))
    result = pipe.compare(
        master_id=7,
        candidate_id="person-A",
        face=BiometricObservation(7, "face", "person-A", 0.85),
        gait=None,
    )
    assert result.gait_score is None
    assert result.state == "resolved"


def test_invalid_configuration_is_rejected():
    try:
        ResiboConfig(face_weight=0.0, gait_weight=0.0).validate()
    except ValueError:
        pass
    else:
        raise AssertionError("zero total modality weight must be rejected")


if __name__ == "__main__":
    test_consistent_multimodal_resolution()
    test_contradiction_is_not_silently_overridden()
    test_diagnostic_reanalysis_can_resolve_when_disagreement_is_reduced()
    test_candidate_identity_disagreement_remains_contradiction()
    test_missing_modality_is_not_fabricated()
    test_invalid_configuration_is_rejected()
    print("RESIBO tests passed.")
