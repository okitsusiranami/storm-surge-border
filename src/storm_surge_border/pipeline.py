from __future__ import annotations

from dataclasses import dataclass

from .core import (
    apply_corrections,
    build_aligned_timeline,
    build_review_rows,
    default_rois,
    roi_to_pixel_rect,
)
from .csvio import read_review_csv, write_estimates_csv, write_review_csv
from .models import EstimateRow, PipelineResult
from .plotting import write_plot_png
from .video import read_video_meta


@dataclass
class PipelineArgs:
    video_a: str
    video_b: str
    offset_sec: float = 0.0
    sample_interval: float = 0.1
    confidence_threshold: float = 0.6
    out_csv: str = "outputs/estimated_border.csv"
    out_review_csv: str = "outputs/review_candidates.csv"
    corrections_csv: str = "outputs/review_candidates.csv"
    out_png: str = "outputs/estimated_border.png"


def run_pipeline(args: PipelineArgs) -> PipelineResult:
    meta_a = read_video_meta(args.video_a)
    meta_b = read_video_meta(args.video_b)
    timeline = build_aligned_timeline(
        duration_a_sec=meta_a.duration_sec,
        duration_b_sec=meta_b.duration_sec,
        offset_sec=args.offset_sec,
        sample_interval_sec=args.sample_interval,
    )

    rois = default_rois()
    _ = {
        "center_bottom_hp": roi_to_pixel_rect(meta_a.width, meta_a.height, rois.center_bottom_hp),
        "center_reticle": roi_to_pixel_rect(meta_a.width, meta_a.height, rois.center_reticle),
        "top_right_surge": roi_to_pixel_rect(meta_a.width, meta_a.height, rois.top_right_surge),
    }

    # Stage-1 start: create auditable placeholders until OCR/event extraction is added.
    estimates: list[EstimateRow] = []
    for ts in timeline:
        estimates.append(
            EstimateRow(
                timestamp_sec=ts,
                duo_damage_diff=None,
                surge_gap_value=None,
                is_above_border=None,
                estimated_border=None,
                confidence=0.0,
                source_flags="placeholder|missing-ocr|missing-events",
            )
        )

    review_rows = build_review_rows(estimates, args.confidence_threshold)

    user_corrections = read_review_csv(args.corrections_csv)
    if user_corrections:
        estimates = apply_corrections(estimates, user_corrections)

    write_estimates_csv(args.out_csv, estimates)
    write_review_csv(args.out_review_csv, review_rows)
    write_plot_png(args.out_png, estimates)
    return PipelineResult(estimates=estimates, review_rows=review_rows)