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


def test_diagnostic_reanalysis_is_explicit():
    def diagnostic(request):
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


if __name__ == "__main__":
    test_consistent_multimodal_resolution()
    test_contradiction_is_not_silently_overridden()
    test_diagnostic_reanalysis_is_explicit()
    print("RESIBO tests passed.")
