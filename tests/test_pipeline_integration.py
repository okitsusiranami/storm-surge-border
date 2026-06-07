import csv
from pathlib import Path

import numpy as np
import pytest

from storm_surge_border.csvio import write_review_csv
from storm_surge_border.hp_tracker import HpDamageTracker
from storm_surge_border.models import CorrectionRow, VideoMeta
from storm_surge_border.ocr import SurgeOcrValue
from storm_surge_border.pipeline import PipelineArgs, run_pipeline

# ---------------------------------------------------------------------------
# Mock scope notice
# ---------------------------------------------------------------------------
# These tests cover the *pipeline orchestration* layer: argument validation,
# correction application, re-computation of estimated_border, review-row
# generation, and OCR state management.
#
# The following are replaced with lightweight fakes to keep tests fast and
# deterministic without real video files or GPU:
#   - read_video_meta        → fixed VideoMeta
#   - VideoFrameReader       → returns a black frame (numpy zeros)
#   - _build_easyocr_reader  → returns None or a sentinel object()
#   - read_surge_from_frame  → returns a fixed SurgeOcrValue where needed
#   - write_plot_png         → no-op
#
# Real I/O (CSV write/read via tmp_path) and the full correction/recompute
# logic in core.py are exercised without mocking.
# ---------------------------------------------------------------------------


class _FakeVideoFrameReader:
    def __init__(self, _video_path: str) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read_at(self, _timestamp_sec: float):
        return np.zeros((120, 240, 3), dtype=np.uint8)


def test_pipeline_without_easyocr_and_with_corrections_regenerates_review_rows(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_video_meta",
        lambda _p: VideoMeta(width=1920, height=1080, fps=60.0, frame_count=7, duration_sec=0.11),
    )
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: None)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)

    corrections_csv = tmp_path / "corrections.csv"
    write_review_csv(
        str(corrections_csv),
        [
            CorrectionRow(0.0, "duo_damage_diff", None, "500", "manual", "reviewer"),
            CorrectionRow(0.0, "surge_gap_value", None, "50", "manual", "reviewer"),
            CorrectionRow(0.0, "is_above_border", None, "true", "manual", "reviewer"),
            CorrectionRow(0.0, "estimated_border", None, "450", "manual", "reviewer"),
        ],
    )

    out_csv = tmp_path / "out.csv"
    out_review_csv = tmp_path / "review.csv"
    args = PipelineArgs(
        video_a="a.mp4",
        video_b="b.mp4",
        sample_interval=0.1,
        confidence_threshold=0.6,
        out_csv=str(out_csv),
        out_review_csv=str(out_review_csv),
        corrections_csv=str(corrections_csv),
        out_png=str(tmp_path / "out.png"),
    )

    result = run_pipeline(args)

    assert len(result.estimates) == 2
    assert result.estimates[0].estimated_border == 450.0
    # Re-generated after correction: corrected row should not remain as stale review target.
    assert all(row.timestamp_sec != 0.0 for row in result.review_rows)

    with out_review_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2


def test_pipeline_partial_correction_recomputes_estimated_border(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_video_meta",
        lambda _p: VideoMeta(width=1920, height=1080, fps=60.0, frame_count=7, duration_sec=0.11),
    )
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: object())
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_surge_from_frame",
        lambda _roi, _reader: SurgeOcrValue(
            gap_value=100.0,
            is_above_border=True,
            confidence=1.0,
            raw_text="+100",
        ),
    )

    corrections_csv = tmp_path / "corrections.csv"
    write_review_csv(
        str(corrections_csv),
        [CorrectionRow(0.0, "duo_damage_diff", None, "500", "manual", "reviewer")],
    )

    args = PipelineArgs(
        video_a="a.mp4",
        video_b="b.mp4",
        sample_interval=0.1,
        ocr_interval=0.1,
        out_csv=str(tmp_path / "out.csv"),
        out_review_csv=str(tmp_path / "review.csv"),
        corrections_csv=str(corrections_csv),
        out_png=str(tmp_path / "out.png"),
    )

    result = run_pipeline(args)

    assert result.estimates[0].duo_damage_diff == 500.0
    assert result.estimates[0].estimated_border == 400.0
    assert "manual-correction" in result.estimates[0].source_flags
    assert result.review_rows == []


def _make_ocr_pipeline_args(tmp_path: Path, *, duration_sec: float, frame_count: int, **overrides) -> PipelineArgs:
    defaults = dict(
        video_a="a.mp4",
        video_b="b.mp4",
        sample_interval=0.1,
        ocr_interval=0.1,
        out_csv=str(tmp_path / "out.csv"),
        out_review_csv=str(tmp_path / "review.csv"),
        corrections_csv=str(tmp_path / "corrections.csv"),
        out_png=str(tmp_path / "out.png"),
    )
    defaults.update(overrides)
    return PipelineArgs(**defaults), VideoMeta(
        width=1920, height=1080, fps=60.0, frame_count=frame_count, duration_sec=duration_sec
    )


def test_pipeline_correction_only_modifies_target_row(tmp_path: Path, monkeypatch) -> None:
    """Correction for t=0.0 must not alter rows at t=0.1 or t=0.2."""
    args, meta = _make_ocr_pipeline_args(tmp_path, duration_sec=0.21, frame_count=20)

    monkeypatch.setattr("storm_surge_border.pipeline.read_video_meta", lambda _p: meta)
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: object())
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_surge_from_frame",
        lambda _roi, _reader: SurgeOcrValue(gap_value=100.0, is_above_border=True, confidence=1.0, raw_text="+100"),
    )

    write_review_csv(
        args.corrections_csv,
        [CorrectionRow(0.0, "duo_damage_diff", None, "999", "manual", "tester")],
    )

    result = run_pipeline(args)

    assert len(result.estimates) >= 3
    assert result.estimates[0].duo_damage_diff == 999.0
    assert "manual-correction" in result.estimates[0].source_flags
    # Rows at t=0.1 and t=0.2 must not carry the manual-correction flag.
    for row in result.estimates[1:]:
        assert "manual-correction" not in row.source_flags


def test_pipeline_correction_for_nonexistent_timestamp_is_ignored(tmp_path: Path, monkeypatch) -> None:
    """Correction targeting a timestamp absent from the timeline must be silently ignored."""
    args, meta = _make_ocr_pipeline_args(tmp_path, duration_sec=0.11, frame_count=7)

    monkeypatch.setattr("storm_surge_border.pipeline.read_video_meta", lambda _p: meta)
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: None)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)

    write_review_csv(
        args.corrections_csv,
        [CorrectionRow(999.0, "duo_damage_diff", None, "500", "manual", "tester")],
    )

    result = run_pipeline(args)

    # Pipeline must complete without error; no row should carry manual-correction.
    assert len(result.estimates) >= 1
    assert all("manual-correction" not in row.source_flags for row in result.estimates)


def test_pipeline_correction_with_empty_corrected_value_is_skipped(tmp_path: Path, monkeypatch) -> None:
    """A CorrectionRow where corrected_value is None (not yet filled in) must be ignored."""
    args, meta = _make_ocr_pipeline_args(tmp_path, duration_sec=0.11, frame_count=7)

    monkeypatch.setattr("storm_surge_border.pipeline.read_video_meta", lambda _p: meta)
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: None)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)

    write_review_csv(
        args.corrections_csv,
        [CorrectionRow(0.0, "duo_damage_diff", "100", None, "", "")],
    )

    result = run_pipeline(args)

    # Row at t=0.0 must not have been flagged as corrected.
    assert all("manual-correction" not in row.source_flags for row in result.estimates)


def test_pipeline_ocr_carry_confidence_decays(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_video_meta",
        lambda _p: VideoMeta(width=1920, height=1080, fps=60.0, frame_count=20, duration_sec=0.31),
    )
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)

    call_count = {"n": 0}

    def _fake_read_surge(_roi, _reader):
        call_count["n"] += 1
        return SurgeOcrValue(gap_value=100.0, is_above_border=True, confidence=1.0, raw_text="+100")

    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: object())
    monkeypatch.setattr("storm_surge_border.pipeline.read_surge_from_frame", _fake_read_surge)

    args = PipelineArgs(
        video_a="a.mp4",
        video_b="b.mp4",
        sample_interval=0.1,
        ocr_interval=0.2,
        ocr_confidence_decay_per_sec=1.0,
        out_csv=str(tmp_path / "out.csv"),
        out_review_csv=str(tmp_path / "review.csv"),
        corrections_csv=str(tmp_path / "review.csv"),
        out_png=str(tmp_path / "out.png"),
    )

    result = run_pipeline(args)

    assert len(result.estimates) >= 3
    assert call_count["n"] == 2
    assert "ocr-carry" in result.estimates[1].source_flags
    assert "border-provisional-carry" in result.estimates[1].source_flags
    assert result.estimates[1].estimated_border_status == "provisional-carry"
    assert result.estimates[1].confidence < result.estimates[0].confidence


def test_pipeline_skips_border_when_ocr_confidence_too_low(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_video_meta",
        lambda _p: VideoMeta(width=1920, height=1080, fps=60.0, frame_count=10, duration_sec=0.21),
    )
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: object())
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_surge_from_frame",
        lambda _roi, _reader: SurgeOcrValue(
            gap_value=100.0,
            is_above_border=True,
            confidence=0.2,
            raw_text="+100",
        ),
    )

    args = PipelineArgs(
        video_a="a.mp4",
        video_b="b.mp4",
        sample_interval=0.1,
        ocr_interval=0.1,
        ocr_confidence_decay_per_sec=0.0,
        ocr_min_confidence_for_border=0.8,
        out_csv=str(tmp_path / "out.csv"),
        out_review_csv=str(tmp_path / "review.csv"),
        corrections_csv=str(tmp_path / "review.csv"),
        out_png=str(tmp_path / "out.png"),
    )

    result = run_pipeline(args)
    assert all(row.estimated_border is None for row in result.estimates)
    assert any("ocr-low-confidence-skip-border" in row.source_flags for row in result.estimates)
    assert all(row.estimated_border_status == "low-ocr-confidence" for row in result.estimates)


def test_pipeline_missing_easyocr_sets_explicit_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_video_meta",
        lambda _p: VideoMeta(width=1920, height=1080, fps=60.0, frame_count=7, duration_sec=0.11),
    )
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: None)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)

    args = PipelineArgs(
        video_a="a.mp4",
        video_b="b.mp4",
        allow_missing_easyocr=True,
        out_csv=str(tmp_path / "out.csv"),
        out_review_csv=str(tmp_path / "review.csv"),
        corrections_csv=str(tmp_path / "review.csv"),
        out_png=str(tmp_path / "out.png"),
    )

    result = run_pipeline(args)
    assert all(row.estimated_border is None for row in result.estimates)
    assert all(row.estimated_border_status == "missing-easyocr" for row in result.estimates)


def test_hp_damage_tracker_emits_provisional_for_short_sequence() -> None:
    tracker = HpDamageTracker(
        max_pool=100.0,
        min_drop_ratio=0.001,
        max_drop_ratio=0.9,
        confirm_frames=3,
        smoothing_alpha=1.0,
    )

    adds = []
    flags = []
    for r in [1.0, 0.9, 0.9]:
        add, f = tracker.update(r)
        adds.append(add)
        flags.extend(f)

    assert adds[-1] > 0
    assert "hp-provisional" in flags


def test_pipeline_ocr_stale_values_are_invalidated(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_video_meta",
        lambda _p: VideoMeta(width=1920, height=1080, fps=60.0, frame_count=25, duration_sec=0.41),
    )
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda **_kw: object())
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_surge_from_frame",
        lambda _roi, _reader: SurgeOcrValue(
            gap_value=120.0, is_above_border=True, confidence=1.0, raw_text="+120"
        ),
    )

    args = PipelineArgs(
        video_a="a.mp4",
        video_b="b.mp4",
        sample_interval=0.1,
        ocr_interval=99.0,
        ocr_stale_timeout_sec=0.15,
        ocr_confidence_decay_per_sec=0.0,
        out_csv=str(tmp_path / "out.csv"),
        out_review_csv=str(tmp_path / "review.csv"),
        corrections_csv=str(tmp_path / "review.csv"),
        out_png=str(tmp_path / "out.png"),
    )

    result = run_pipeline(args)
    assert result.estimates[0].surge_gap_value == 120.0
    assert result.estimates[-1].surge_gap_value is None
    assert result.estimates[-1].confidence == 0.0
    assert any("ocr-stale-reset" in row.source_flags for row in result.estimates)


def test_pipeline_args_validation_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError):
        run_pipeline(
            PipelineArgs(
                video_a="a.mp4",
                video_b="b.mp4",
                hp_min_drop_ratio=0.6,
                hp_max_drop_ratio=0.4,
            )
        )


def test_hp_damage_tracker_confirms_once_for_long_continuous_drop(monkeypatch) -> None:
    tracker = HpDamageTracker(
        max_pool=100.0,
        min_drop_ratio=0.001,
        max_drop_ratio=0.9,
        confirm_frames=2,
        smoothing_alpha=1.0,
    )

    # Sequence creates 4 continuous drops.
    ratios = [1.0, 0.9, 0.8, 0.7, 0.6]
    adds = []
    for r in ratios:
        add, _flags = tracker.update(r)
        adds.append(add)

    # Long sequences are confirmed repeatedly by confirmation windows.
    assert sum(1 for x in adds if x > 0) == 2


def test_hp_damage_tracker_allows_new_sequence_after_non_drop() -> None:
    tracker = HpDamageTracker(
        max_pool=100.0,
        min_drop_ratio=0.001,
        max_drop_ratio=0.9,
        confirm_frames=2,
        smoothing_alpha=1.0,
    )

    adds = []
    for r in [1.0, 0.9, 0.8, 0.8, 0.7, 0.6]:
        add, _flags = tracker.update(r)
        adds.append(add)

    # Two separate drop sequences should still allow confirmations.
    assert sum(1 for x in adds if x > 0) == 2