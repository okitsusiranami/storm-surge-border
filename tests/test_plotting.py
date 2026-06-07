from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from storm_surge_border.models import EstimateRow
from storm_surge_border.plotting import write_plot_png


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

    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert out_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")