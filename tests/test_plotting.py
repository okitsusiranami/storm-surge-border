from pathlib import Path

from storm_surge_border.models import EstimateRow
from storm_surge_border.plotting import write_plot_png

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _is_valid_png(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0 and path.read_bytes().startswith(PNG_SIGNATURE)


def test_write_plot_png_creates_non_empty_png(tmp_path: Path) -> None:
    out_path = tmp_path / "border.png"
    rows = [
        EstimateRow(
            timestamp_sec=0.0,
            duo_damage_diff=100.0,
            surge_gap_value=20.0,
            is_above_border=True,
            estimated_border=80.0,
            confidence=0.9,
            source_flags="source-a",
        ),
        EstimateRow(
            timestamp_sec=0.1,
            duo_damage_diff=120.0,
            surge_gap_value=25.0,
            is_above_border=False,
            estimated_border=145.0,
            confidence=0.8,
            source_flags="source-b",
        ),
    ]

    write_plot_png(str(out_path), rows)

    assert _is_valid_png(out_path)


def test_write_plot_png_with_empty_rows_produces_valid_png(tmp_path: Path) -> None:
    """Empty input must not crash; an empty chart PNG should be written."""
    out_path = tmp_path / "empty.png"

    write_plot_png(str(out_path), [])

    assert _is_valid_png(out_path)


def test_write_plot_png_tolerates_none_estimated_border(tmp_path: Path) -> None:
    """Rows where estimated_border is None (pending OCR) must not crash plotting."""
    out_path = tmp_path / "partial.png"
    rows = [
        EstimateRow(
            timestamp_sec=0.0,
            duo_damage_diff=100.0,
            surge_gap_value=20.0,
            is_above_border=True,
            estimated_border=None,
            confidence=0.3,
            source_flags="low-confidence",
        ),
        EstimateRow(
            timestamp_sec=0.1,
            duo_damage_diff=120.0,
            surge_gap_value=25.0,
            is_above_border=False,
            estimated_border=145.0,
            confidence=0.9,
            source_flags="source-b",
        ),
    ]

    write_plot_png(str(out_path), rows)

    assert _is_valid_png(out_path)