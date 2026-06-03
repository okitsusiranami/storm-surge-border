from storm_surge_border.core import (
    build_aligned_timeline,
    calculate_estimated_border,
    default_rois,
    roi_to_pixel_rect,
)


def test_border_formula_above_case() -> None:
    assert calculate_estimated_border(duo_damage_diff=500, surge_gap_value=120, is_above_border=True) == 380


def test_border_formula_below_case() -> None:
    assert calculate_estimated_border(duo_damage_diff=500, surge_gap_value=120, is_above_border=False) == 620


def test_build_aligned_timeline_with_positive_offset() -> None:
    timeline = build_aligned_timeline(
        duration_a_sec=10.0,
        duration_b_sec=10.0,
        offset_sec=1.0,
        sample_interval_sec=0.5,
    )
    assert timeline[0] == 1.0
    assert timeline[-1] == 9.5


def test_center_bottom_hp_roi_is_bottom_area() -> None:
    rois = default_rois()
    x1, y1, x2, y2 = roi_to_pixel_rect(1920, 1080, rois.center_bottom_hp)
    assert y1 > 700
    assert y2 > y1
    assert x2 > x1