from pathlib import Path

import matplotlib.image as mpimg

from storm_surge_border.models import EstimateRow
from storm_surge_border.plotting import write_plot_png

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _is_loadable_png(path: Path) -> bool:
    """Return True only if the file is a non-empty, valid PNG loadable by matplotlib."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    if not path.read_bytes().startswith(PNG_SIGNATURE):
        return False
    img = mpimg.imread(str(path))
    return img is not None and img.size > 0


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

    assert _is_loadable_png(out_path)


def test_write_plot_png_with_empty_rows_produces_valid_png(tmp_path: Path) -> None:
    """Empty input must not crash; an empty chart PNG should be written."""
    out_path = tmp_path / "empty.png"

    write_plot_png(str(out_path), [])

    assert _is_loadable_png(out_path)


def test_write_plot_png_tolerates_none_estimated_border(tmp_path: Path) -> None:
    """Rows where estimated_border is None must be rendered as NaN gaps, not crash.

    This test validates the plotting.py change that converts None → float('nan')
    so that missing-OCR rows produce visual gaps in the chart rather than
    raising a TypeError when matplotlib processes the y-axis data.
    """
    out_path = tmp_path / "partial.png"
    rows = [
        EstimateRow(
            timestamp_sec=0.0,
            duo_damage_diff=100.0,
            surge_gap_value=20.0,
            is_above_border=True,
            estimated_border=None,  # OCR not yet available
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

    # Must not raise despite None in estimated_border.
    write_plot_png(str(out_path), rows)

    assert _is_loadable_png(out_path)


def test_write_plot_png_all_none_estimated_border_is_stable(tmp_path: Path) -> None:
    """All-None estimated_border (e.g. easyocr absent) must produce a valid empty chart."""
    out_path = tmp_path / "all_none.png"
    rows = [
        EstimateRow(
            timestamp_sec=t,
            duo_damage_diff=None,
            surge_gap_value=None,
            is_above_border=None,
            estimated_border=None,
            confidence=0.0,
            source_flags="missing-easyocr",
        )
        for t in [0.0, 0.1, 0.2]
    ]

    write_plot_png(str(out_path), rows)

    assert _is_loadable_png(out_path)