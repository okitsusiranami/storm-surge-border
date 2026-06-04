from __future__ import annotations

import argparse

from .pipeline import PipelineArgs, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="storm-surge-border",
        description="Stage-1 pipeline for storm surge border estimation",
    )
    parser.add_argument("--video-a", required=True, help="Path to player A video (mp4)")
    parser.add_argument("--video-b", required=True, help="Path to player B video (mp4)")
    parser.add_argument(
        "--offset-sec",
        type=float,
        default=0.0,
        help="Manual offset in seconds for alignment (b_time = t - offset)",
    )
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=0.1,
        help="Sampling interval in seconds",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.6,
        help="Threshold to mark rows for manual review",
    )
    parser.add_argument(
        "--out-csv",
        default="outputs/estimated_border.csv",
        help="Output path for estimate csv",
    )
    parser.add_argument(
        "--out-review-csv",
        default="outputs/review_candidates.csv",
        help="Output path for review csv",
    )
    parser.add_argument(
        "--corrections-csv",
        default="outputs/review_candidates.csv",
        help="Input path for manual corrections csv",
    )
    parser.add_argument(
        "--out-png",
        default="outputs/estimated_border.png",
        help="Output path for border chart png",
    )
    parser.add_argument(
        "--ocr-interval",
        type=float,
        default=1.0,
        help="OCR execution interval in seconds",
    )
    parser.add_argument(
        "--hp-max-pool",
        type=float,
        default=200.0,
        help="Maximum HP+shield pool used for received damage estimation",
    )
    parser.add_argument(
        "--hp-min-drop-ratio",
        type=float,
        default=0.005,
        help="Minimum ratio drop to count as damage",
    )
    parser.add_argument(
        "--hp-max-drop-ratio",
        type=float,
        default=0.45,
        help="Maximum ratio drop before treating as outlier",
    )
    parser.add_argument(
        "--hp-confirm-frames",
        type=int,
        default=2,
        help="Frames required to confirm received damage accumulation",
    )
    parser.add_argument(
        "--hp-smoothing-alpha",
        type=float,
        default=0.5,
        help="EMA alpha for HP ratio smoothing (0-1)",
    )
    parser.add_argument(
        "--ocr-confidence-decay-per-sec",
        type=float,
        default=0.03,
        help="Confidence decay applied per second while OCR value is carried forward",
    )
    parser.add_argument(
        "--ocr-stale-timeout-sec",
        type=float,
        default=15.0,
        help="Timeout after which carried OCR values are invalidated",
    )
    parser.add_argument(
        "--ocr-min-confidence-for-border",
        type=float,
        default=0.4,
        help="Minimum OCR confidence required to compute estimated_border",
    )
    parser.add_argument(
        "--surge-source-video",
        choices=["a", "b"],
        default="a",
        help="Video source used for surge OCR (a or b)",
    )
    parser.add_argument(
        "--allow-missing-easyocr",
        action="store_true",
        help="Continue without OCR if easyocr is unavailable",
    )
    return parser


def main() -> int:
    parser = build_parser()
    ns = parser.parse_args()
    args = PipelineArgs(
        video_a=ns.video_a,
        video_b=ns.video_b,
        offset_sec=ns.offset_sec,
        sample_interval=ns.sample_interval,
        confidence_threshold=ns.confidence_threshold,
        out_csv=ns.out_csv,
        out_review_csv=ns.out_review_csv,
        corrections_csv=ns.corrections_csv,
        out_png=ns.out_png,
        ocr_interval=ns.ocr_interval,
        hp_max_pool=ns.hp_max_pool,
        hp_min_drop_ratio=ns.hp_min_drop_ratio,
        hp_max_drop_ratio=ns.hp_max_drop_ratio,
        hp_confirm_frames=ns.hp_confirm_frames,
        hp_smoothing_alpha=ns.hp_smoothing_alpha,
        ocr_confidence_decay_per_sec=ns.ocr_confidence_decay_per_sec,
        ocr_stale_timeout_sec=ns.ocr_stale_timeout_sec,
        ocr_min_confidence_for_border=ns.ocr_min_confidence_for_border,
        allow_missing_easyocr=ns.allow_missing_easyocr,
        surge_source_video=ns.surge_source_video,
    )
    result = run_pipeline(args)
    print(f"done: estimates={len(result.estimates)} review_rows={len(result.review_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())