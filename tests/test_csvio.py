from pathlib import Path

from storm_surge_border.csvio import read_review_csv, write_review_csv
from storm_surge_border.models import CorrectionRow


def test_review_csv_roundtrip_preserves_values_and_empty_fields(tmp_path: Path) -> None:
    file_path = tmp_path / "review.csv"
    rows = [
        CorrectionRow(1.234, "estimated_border", None, "321", "manual", "tester"),
        CorrectionRow(2.5, "duo_damage_diff", "500", None, "", ""),
    ]

    write_review_csv(str(file_path), rows)

    loaded = read_review_csv(str(file_path))

    assert len(loaded) == 2
    assert loaded[0] == rows[0]
    assert loaded[1].timestamp_sec == 2.5
    assert loaded[1].field_name == "duo_damage_diff"
    assert loaded[1].original_value == "500"
    assert loaded[1].corrected_value is None
    assert loaded[1].reason == ""
    assert loaded[1].reviewer == ""


def test_read_review_csv_missing_file_returns_empty_list(tmp_path: Path) -> None:
    assert read_review_csv(str(tmp_path / "missing.csv")) == []