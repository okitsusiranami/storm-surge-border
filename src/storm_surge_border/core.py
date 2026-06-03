from __future__ import annotations

from typing import Iterable

from .models import CorrectionRow, EstimateRow, RoiSet


def calculate_estimated_border(
    duo_damage_diff: float, surge_gap_value: float, is_above_border: bool
) -> float:
    if is_above_border:
        return duo_damage_diff - surge_gap_value
    return duo_damage_diff + surge_gap_value


def build_aligned_timeline(
    duration_a_sec: float,
    duration_b_sec: float,
    offset_sec: float,
    sample_interval_sec: float,
) -> list[float]:
    if sample_interval_sec <= 0:
        raise ValueError("sample_interval_sec must be > 0")

    # b_time = t - offset_sec
    start = max(0.0, offset_sec)
    end = min(duration_a_sec, duration_b_sec + offset_sec)
    if end <= start:
        return []

    timeline: list[float] = []
    t = start
    while t < end:
        timeline.append(round(t, 3))
        t += sample_interval_sec
    return timeline


def default_rois() -> RoiSet:
    return RoiSet(
        center_bottom_hp=(0.40, 0.84, 0.60, 0.97),
        center_reticle=(0.43, 0.42, 0.57, 0.58),
        top_right_surge=(0.70, 0.05, 0.98, 0.30),
    )


def roi_to_pixel_rect(
    width: int, height: int, ratio_rect: tuple[float, float, float, float]
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = ratio_rect
    px1 = max(0, min(width - 1, int(width * x1)))
    py1 = max(0, min(height - 1, int(height * y1)))
    px2 = max(px1 + 1, min(width, int(width * x2)))
    py2 = max(py1 + 1, min(height, int(height * y2)))
    return px1, py1, px2, py2


def build_review_rows(
    estimates: Iterable[EstimateRow], confidence_threshold: float
) -> list[CorrectionRow]:
    rows: list[CorrectionRow] = []
    for row in estimates:
        has_missing = (
            row.duo_damage_diff is None
            or row.surge_gap_value is None
            or row.is_above_border is None
            or row.estimated_border is None
        )
        if has_missing or row.confidence < confidence_threshold:
            rows.append(
                CorrectionRow(
                    timestamp_sec=row.timestamp_sec,
                    field_name="estimated_border",
                    original_value=(
                        None
                        if row.estimated_border is None
                        else f"{row.estimated_border:.3f}"
                    ),
                    corrected_value=None,
                    reason="auto-low-confidence-or-missing",
                    reviewer="",
                )
            )
    return rows


def apply_corrections(
    estimates: list[EstimateRow], corrections: Iterable[CorrectionRow]
) -> list[EstimateRow]:
    by_key = {round(row.timestamp_sec, 3): row for row in estimates}
    for corr in corrections:
        if not corr.corrected_value:
            continue
        target = by_key.get(round(corr.timestamp_sec, 3))
        if not target:
            continue
        if corr.field_name == "estimated_border":
            target.estimated_border = float(corr.corrected_value)
            target.source_flags = _merge_flag(target.source_flags, "manual-correction")
            target.confidence = max(target.confidence, 0.95)
        elif corr.field_name == "duo_damage_diff":
            target.duo_damage_diff = float(corr.corrected_value)
            _recompute_if_possible(target)
            target.source_flags = _merge_flag(target.source_flags, "manual-correction")
        elif corr.field_name == "surge_gap_value":
            target.surge_gap_value = float(corr.corrected_value)
            _recompute_if_possible(target)
            target.source_flags = _merge_flag(target.source_flags, "manual-correction")
        elif corr.field_name == "is_above_border":
            target.is_above_border = corr.corrected_value.strip().lower() in {
                "1",
                "true",
                "yes",
            }
            _recompute_if_possible(target)
            target.source_flags = _merge_flag(target.source_flags, "manual-correction")
    return estimates


def _recompute_if_possible(row: EstimateRow) -> None:
    if (
        row.duo_damage_diff is None
        or row.surge_gap_value is None
        or row.is_above_border is None
    ):
        return
    row.estimated_border = calculate_estimated_border(
        duo_damage_diff=row.duo_damage_diff,
        surge_gap_value=row.surge_gap_value,
        is_above_border=row.is_above_border,
    )


def _merge_flag(flags: str, new_flag: str) -> str:
    current = [f for f in flags.split("|") if f]
    if new_flag not in current:
        current.append(new_flag)
    return "|".join(current)