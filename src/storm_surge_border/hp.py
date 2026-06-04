from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DamageEvent:
    damage: float
    flag: str


def estimate_hp_ratio_from_roi(roi) -> float | None:
    """Estimate combined HP/shield fill ratio from a center-bottom HUD ROI."""
    import cv2
    import numpy as np

    if roi is None or roi.size == 0:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Broad mask to capture health/shield bar colors.
    mask_green = cv2.inRange(hsv, (35, 30, 40), (95, 255, 255))
    mask_blue = cv2.inRange(hsv, (85, 20, 40), (145, 255, 255))
    mask_white = cv2.inRange(hsv, (0, 0, 180), (179, 60, 255))
    mask = cv2.bitwise_or(mask_green, mask_blue)
    mask = cv2.bitwise_or(mask, mask_white)

    h, w = mask.shape
    if h < 3 or w < 8:
        return None

    col_density = (mask > 0).mean(axis=0)

    # Smooth horizontal density to reduce isolated single-column noise.
    kernel = np.ones(7, dtype=float) / 7.0
    smooth = np.convolve(col_density, kernel, mode="same")
    active = smooth > 0.12
    if not np.any(active):
        return None

    # Use the right edge of the longest contiguous run instead of max(active).
    run_start = 0
    run_len = 0
    best_start = 0
    best_len = 0
    for i, is_on in enumerate(active):
        if is_on:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len = run_len
                best_start = run_start
        else:
            run_len = 0

    if best_len < max(4, int(w * 0.04)):
        return None

    # Use inclusive filled width to avoid off-by-one underestimation.
    filled_width = best_start + best_len
    ratio = max(0.0, min(1.0, filled_width / max(1, w)))
    return float(ratio)


def detect_received_damage(
    prev_ratio: float | None,
    curr_ratio: float | None,
    *,
    max_pool: float = 200.0,
    min_drop_ratio: float = 0.005,
    max_drop_ratio: float = 0.45,
) -> DamageEvent:
    if prev_ratio is None or curr_ratio is None:
        return DamageEvent(0.0, "hp-missing")

    drop = prev_ratio - curr_ratio
    if drop <= min_drop_ratio:
        return DamageEvent(0.0, "hp-no-drop")
    if drop >= max_drop_ratio:
        return DamageEvent(0.0, "hp-drop-outlier")

    return DamageEvent(max(0.0, drop * max_pool), "hp-damaged")