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
from .hp import estimate_hp_ratio_from_roi
from .hp_tracker import HpDamageTracker
from .models import EstimateRow, PipelineResult
from .ocr import read_surge_from_frame
from .ocr_state import OcrStateTracker
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
    hp_max_pool: float = 200.0
    hp_min_drop_ratio: float = 0.005
    hp_max_drop_ratio: float = 0.45
    hp_confirm_frames: int = 2
    hp_smoothing_alpha: float = 0.5
    ocr_confidence_decay_per_sec: float = 0.03
    ocr_stale_timeout_sec: float = 15.0


def run_pipeline(args: PipelineArgs) -> PipelineResult:
    _validate_args(args)

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
    ocr_state = OcrStateTracker()
    hp_a = HpDamageTracker(
        max_pool=args.hp_max_pool,
        min_drop_ratio=args.hp_min_drop_ratio,
        max_drop_ratio=args.hp_max_drop_ratio,
        confirm_frames=args.hp_confirm_frames,
        smoothing_alpha=args.hp_smoothing_alpha,
    )
    hp_b = HpDamageTracker(
        max_pool=args.hp_max_pool,
        min_drop_ratio=args.hp_min_drop_ratio,
        max_drop_ratio=args.hp_max_drop_ratio,
        confirm_frames=args.hp_confirm_frames,
        smoothing_alpha=args.hp_smoothing_alpha,
    )

    estimates: list[EstimateRow] = []
    cumulative_received = 0.0

    with VideoFrameReader(args.video_a) as reader_a, VideoFrameReader(args.video_b) as reader_b:
        for ts in timeline:
            frame_a = reader_a.read_at(ts)
            frame_b = reader_b.read_at(ts - args.offset_sec)

            run_ocr = reader is not None and ocr_state.should_attempt(ts, args.ocr_interval)
            source_flags = []

            hp_roi_a = _crop(frame_a, hp_rect_a)
            hp_roi_b = _crop(frame_b, hp_rect_b)
            curr_raw_a = estimate_hp_ratio_from_roi(hp_roi_a)
            curr_raw_b = estimate_hp_ratio_from_roi(hp_roi_b)
            add_a, flags_a = hp_a.update(curr_raw_a)
            add_b, flags_b = hp_b.update(curr_raw_b)
            cumulative_received += add_a + add_b
            source_flags.extend(flags_a)
            source_flags.extend(flags_b)
            source_flags.append("damage-source-duo")

            if run_ocr:
                surge_roi = _crop(frame_a, top_right_rect)
                ocr_value = read_surge_from_frame(surge_roi, reader)
                source_flags.extend(ocr_state.record_attempt(ts, ocr_value))
            else:
                if reader is None:
                    source_flags.append("missing-easyocr")

            surge_gap_value, is_above_border, frame_confidence, ocr_flags = ocr_state.effective_value(
                ts,
                decay_per_sec=args.ocr_confidence_decay_per_sec,
                stale_timeout_sec=args.ocr_stale_timeout_sec,
            )
            source_flags.extend(ocr_flags)

            # Stage-1 combines duo-received-damage with surge text read from video A.
            duo_damage_diff = -cumulative_received
            estimated_border = None
            if surge_gap_value is not None and is_above_border is not None:
                source_flags.append("surge-source-a")
                estimated_border = calculate_estimated_border(
                    duo_damage_diff=duo_damage_diff,
                    surge_gap_value=surge_gap_value,
                    is_above_border=is_above_border,
                )

            estimates.append(
                EstimateRow(
                    timestamp_sec=ts,
                    duo_damage_diff=duo_damage_diff,
                    surge_gap_value=surge_gap_value,
                    is_above_border=is_above_border,
                    estimated_border=estimated_border,
                    confidence=frame_confidence,
                    source_flags="|".join(source_flags),
                )
            )

    review_rows = build_review_rows(estimates, args.confidence_threshold)

    user_corrections = read_review_csv(args.corrections_csv)
    if user_corrections:
        estimates = apply_corrections(estimates, user_corrections)
        review_rows = build_review_rows(estimates, args.confidence_threshold)

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


def _decay_carry_confidence(
    *,
    base_confidence: float,
    last_ocr_ts: float | None,
    current_ts: float,
    decay_per_sec: float,
) -> float:
    if last_ocr_ts is None:
        return 0.0
    elapsed = max(0.0, current_ts - last_ocr_ts)
    decayed = base_confidence - (elapsed * max(0.0, decay_per_sec))
    return max(0.0, decayed)


def _validate_args(args: PipelineArgs) -> None:
    if args.sample_interval <= 0:
        raise ValueError("sample_interval must be > 0")
    if args.ocr_interval <= 0:
        raise ValueError("ocr_interval must be > 0")
    if args.hp_max_pool <= 0:
        raise ValueError("hp_max_pool must be > 0")
    if not (0.0 <= args.hp_min_drop_ratio < args.hp_max_drop_ratio <= 1.0):
        raise ValueError("hp drop ratios must satisfy 0 <= min < max <= 1")
    if args.hp_confirm_frames < 1:
        raise ValueError("hp_confirm_frames must be >= 1")
    if not (0.0 <= args.hp_smoothing_alpha <= 1.0):
        raise ValueError("hp_smoothing_alpha must be in [0, 1]")
    if args.ocr_confidence_decay_per_sec < 0:
        raise ValueError("ocr_confidence_decay_per_sec must be >= 0")
    if args.ocr_stale_timeout_sec < 0:
        raise ValueError("ocr_stale_timeout_sec must be >= 0")


def _smooth_ratio(prev: float | None, curr: float | None, alpha: float) -> float | None:
    if curr is None:
        return None
    if prev is None:
        return curr
    return (alpha * curr) + ((1.0 - alpha) * prev)