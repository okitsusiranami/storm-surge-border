import numpy as np

from storm_surge_border.hp import detect_received_damage, estimate_hp_ratio_from_roi


def test_estimate_hp_ratio_from_roi_detects_fill() -> None:
    # Create a synthetic bar-like ROI: left half filled with green.
    roi = np.zeros((40, 200, 3), dtype=np.uint8)
    roi[:, :100] = (0, 255, 0)
    ratio = estimate_hp_ratio_from_roi(roi)
    assert ratio is not None
    assert 0.40 <= ratio <= 0.60


def test_detect_received_damage_from_drop() -> None:
    event = detect_received_damage(prev_ratio=0.80, curr_ratio=0.70)
    assert event.damage > 0
    assert event.flag == "hp-damaged"


def test_detect_received_damage_outlier_drop_is_ignored() -> None:
    event = detect_received_damage(prev_ratio=0.90, curr_ratio=0.10)
    assert event.damage == 0.0
    assert event.flag == "hp-drop-outlier"


def test_estimate_hp_ratio_ignores_single_right_noise() -> None:
    roi = np.zeros((40, 200, 3), dtype=np.uint8)
    roi[:, :100] = (0, 255, 0)
    roi[:, 199] = (0, 255, 0)
    ratio = estimate_hp_ratio_from_roi(roi)
    assert ratio is not None
    assert 0.40 <= ratio <= 0.60


def test_estimate_hp_ratio_uses_inclusive_filled_width() -> None:
    roi = np.zeros((20, 10, 3), dtype=np.uint8)
    roi[:, 0] = (0, 255, 0)
    ratio = estimate_hp_ratio_from_roi(roi)
    assert ratio is not None
    # With smoothing, the detected width can broaden, but should stay positive
    # and well below a half-filled bar for this one-column input.
    assert 0.1 <= ratio < 0.5