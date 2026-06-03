from __future__ import annotations

from dataclasses import dataclass

from .core import (
    calculate_estimated_border,
    apply_corrections,
    build_aligned_timeline,
    build_review_rows,
    default_rois,
    roi_to_pixel_rect,
)
from .csvio import read_review_csv, write_estimates_csv, write_review_csv
from .hp import detect_received_damage, estimate_hp_ratio_from_roi
from .models import EstimateRow, PipelineResult
from .ocr import read_surge_from_frame
from .plotting import write_plot_png
from .video import VideoFrameReader, read_video_meta


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
    ocr_interval: float = 1.0


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
    hp_rect_a = roi_to_pixel_rect(meta_a.width, meta_a.height, rois.center_bottom_hp)
    hp_rect_b = roi_to_pixel_rect(meta_b.width, meta_b.height, rois.center_bottom_hp)
    top_right_rect = roi_to_pixel_rect(meta_a.width, meta_a.height, rois.top_right_surge)

    reader = _build_easyocr_reader()
    estimates: list[EstimateRow] = []
    last_ocr_ts: float | None = None
    last_gap_value: float | None = None
    last_side: bool | None = None
    last_conf: float = 0.0
    prev_hp_a: float | None = None
    prev_hp_b: float | None = None
    cumulative_received = 0.0

    with VideoFrameReader(args.video_a) as reader_a, VideoFrameReader(args.video_b) as reader_b:
        for ts in timeline:
            frame_a = reader_a.read_at(ts)
            frame_b = reader_b.read_at(ts - args.offset_sec)

            run_ocr = (
                reader is not None
                and (last_ocr_ts is None or (ts - last_ocr_ts) >= max(args.ocr_interval, 0.1))
            )
            source_flags = []

            hp_roi_a = _crop(frame_a, hp_rect_a)
            hp_roi_b = _crop(frame_b, hp_rect_b)
            hp_ratio_a = estimate_hp_ratio_from_roi(hp_roi_a)
            hp_ratio_b = estimate_hp_ratio_from_roi(hp_roi_b)

            dmg_a = detect_received_damage(prev_hp_a, hp_ratio_a)
            dmg_b = detect_received_damage(prev_hp_b, hp_ratio_b)
            cumulative_received += dmg_a.damage + dmg_b.damage
            source_flags.extend([dmg_a.flag, dmg_b.flag])

            if hp_ratio_a is not None:
                prev_hp_a = hp_ratio_a
            if hp_ratio_b is not None:
                prev_hp_b = hp_ratio_b

            if run_ocr:
                surge_roi = _crop(frame_a, top_right_rect)
                ocr_value = read_surge_from_frame(surge_roi, reader)
                if ocr_value.gap_value is not None:
                    last_gap_value = ocr_value.gap_value
                    source_flags.append("ocr-gap")
                else:
                    source_flags.append("missing-ocr-gap")
                if ocr_value.is_above_border is not None:
                    last_side = ocr_value.is_above_border
                    source_flags.append("ocr-side")
                else:
                    source_flags.append("missing-ocr-side")
                last_conf = ocr_value.confidence
                last_ocr_ts = ts
            else:
                source_flags.append("ocr-carry")

            # Stage-1 now estimates duo damage diff from cumulative received damage.
            duo_damage_diff = -cumulative_received
            estimated_border = None
            if last_gap_value is not None and last_side is not None:
                estimated_border = calculate_estimated_border(
                    duo_damage_diff=duo_damage_diff,
                    surge_gap_value=last_gap_value,
                    is_above_border=last_side,
                )

            estimates.append(
                EstimateRow(
                    timestamp_sec=ts,
                    duo_damage_diff=duo_damage_diff,
                    surge_gap_value=last_gap_value,
                    is_above_border=last_side,
                    estimated_border=estimated_border,
                    confidence=last_conf,
                    source_flags="|".join(source_flags),
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


def _build_easyocr_reader():
    try:
        import easyocr
    except ModuleNotFoundError:
        return None
    return easyocr.Reader(["ja", "en"], gpu=False)


def _crop(frame, rect: tuple[int, int, int, int]):
    if frame is None:
        return None
    x1, y1, x2, y2 = rect
    return frame[y1:y2, x1:x2]