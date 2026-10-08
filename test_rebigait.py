from resibo.rebigait import ReBiGait, ReBiGaitComparison


def test_rebigait_preserves_baseline_and_compares_control():
    gallery = {"A": [1.0, 0.0]}

    def model(sequence):
        return sequence

    def compare(embedding):
        x = float(embedding[0])
        return "A", x

    def condition_classifier(sequence, context):
        return "carried_object"

    def intervention(sequence, condition, context):
        return [0.9, 0.1]

    def control(sequence, condition, context):
        return [0.7, 0.3]

    rb = ReBiGait(
        gait_model=model,
        compare_embedding=compare,
        condition_classifier=condition_classifier,
        intervention_builder=intervention,
        control_builder=control,
    )

    baseline = ReBiGaitComparison("A", 0.5, "baseline")
    result = rb.run([0.5, 0.5], baseline, {})

    assert result.triggered
    assert result.condition == "carried_object"
    assert result.baseline.score == 0.5
    assert result.intervention.score == 0.9
    assert result.control.score == 0.7
    assert result.intervention_effect == 0.4
    assert result.control_effect == 0.19999999999999996
    assert abs(result.sensitivity - 0.2) < 1e-8
