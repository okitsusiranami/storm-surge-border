from storm_surge_border.core import apply_corrections
from storm_surge_border.models import CorrectionRow, EstimateRow


def test_apply_manual_estimated_border() -> None:
    estimates = [
        EstimateRow(
            timestamp_sec=1.0,
            duo_damage_diff=None,
            surge_gap_value=None,
            is_above_border=None,
            estimated_border=None,
            confidence=0.0,
            source_flags="placeholder",
        )
    ]
    corrections = [
        CorrectionRow(
            timestamp_sec=1.0,
            field_name="estimated_border",
            original_value=None,
            corrected_value="321",
            reason="manual",
            reviewer="tester",
        )
    ]

    updated = apply_corrections(estimates, corrections)
    assert updated[0].estimated_border == 321.0
    assert "manual-correction" in updated[0].source_flags


def test_apply_manual_inputs_and_recompute() -> None:
    estimates = [
        EstimateRow(
            timestamp_sec=2.0,
            duo_damage_diff=None,
            surge_gap_value=None,
            is_above_border=None,
            estimated_border=None,
            confidence=0.0,
            source_flags="placeholder",
        )
    ]
    corrections = [
        CorrectionRow(2.0, "duo_damage_diff", None, "500", "manual", "tester"),
        CorrectionRow(2.0, "surge_gap_value", None, "50", "manual", "tester"),
        CorrectionRow(2.0, "is_above_border", None, "true", "manual", "tester"),
    ]

    updated = apply_corrections(estimates, corrections)
    assert updated[0].estimated_border == 450.0