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
    )
    result = run_pipeline(args)
    print(f"done: estimates={len(result.estimates)} review_rows={len(result.review_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())