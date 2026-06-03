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
    active_cols = np.where(col_density > 0.12)[0]
    if active_cols.size == 0:
        return None

    fill_end = int(active_cols.max())
    ratio = max(0.0, min(1.0, fill_end / max(1, w - 1)))
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