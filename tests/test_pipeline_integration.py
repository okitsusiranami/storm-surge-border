import csv
from pathlib import Path

import numpy as np
import pytest

from storm_surge_border.csvio import write_review_csv
from storm_surge_border.models import CorrectionRow, VideoMeta
from storm_surge_border.ocr import SurgeOcrValue
from storm_surge_border.pipeline import PipelineArgs, run_pipeline


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
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda: None)
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

    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda: object())
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
    assert result.estimates[1].confidence < result.estimates[0].confidence


def test_pipeline_ocr_stale_values_are_invalidated(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "storm_surge_border.pipeline.read_video_meta",
        lambda _p: VideoMeta(width=1920, height=1080, fps=60.0, frame_count=25, duration_sec=0.41),
    )
    monkeypatch.setattr("storm_surge_border.pipeline.VideoFrameReader", _FakeVideoFrameReader)
    monkeypatch.setattr("storm_surge_border.pipeline.write_plot_png", lambda _p, _r: None)
    monkeypatch.setattr("storm_surge_border.pipeline._build_easyocr_reader", lambda: object())
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