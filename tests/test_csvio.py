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


def test_review_csv_roundtrip_with_special_characters(tmp_path: Path) -> None:
    """Values containing commas and double-quotes must survive CSV encoding."""
    file_path = tmp_path / "special.csv"
    rows = [
        CorrectionRow(
            timestamp_sec=3.0,
            field_name="estimated_border",
            original_value='value "quoted"',
            corrected_value="value, with comma",
            reason='reason: a, b "c"',
            reviewer="",
        ),
    ]

    write_review_csv(str(file_path), rows)
    loaded = read_review_csv(str(file_path))

    assert len(loaded) == 1
    assert loaded[0].original_value == 'value "quoted"'
    assert loaded[0].corrected_value == "value, with comma"
    assert loaded[0].reason == 'reason: a, b "c"'


def test_read_review_csv_skips_rows_with_empty_timestamp(tmp_path: Path) -> None:
    """Rows where timestamp_sec is blank must be silently skipped."""
    file_path = tmp_path / "partial.csv"
    rows = [
        CorrectionRow(1.0, "estimated_border", None, "100", "manual", "tester"),
        CorrectionRow(2.0, "duo_damage_diff", None, "200", "manual", "tester"),
    ]
    write_review_csv(str(file_path), rows)

    # Append a malformed row with an empty timestamp_sec.
    content = file_path.read_text(encoding="utf-8")
    content += ",estimated_border,,,manual,tester\n"
    file_path.write_text(content, encoding="utf-8")

    loaded = read_review_csv(str(file_path))
    assert len(loaded) == 2


def test_read_review_csv_ignores_extra_columns(tmp_path: Path) -> None:
    """Extra columns added by an external tool must not break parsing."""
    file_path = tmp_path / "extra.csv"
    file_path.write_text(
        "timestamp_sec,field_name,original_value,corrected_value,reason,reviewer,notes\n"
        "1.000,estimated_border,,100.0,manual,tester,extra-note\n",
        encoding="utf-8",
    )

    loaded = read_review_csv(str(file_path))
    assert len(loaded) == 1
    assert loaded[0].timestamp_sec == 1.0
    assert loaded[0].corrected_value == "100.0"


def test_read_review_csv_skips_rows_with_invalid_timestamp(tmp_path: Path) -> None:
    """Rows where timestamp_sec cannot be parsed as float must be silently skipped.

    Human-edited CSVs may contain typos (e.g. "abc", "1.2.3").
    The spec is: skip the malformed row rather than raising.
    """
    file_path = tmp_path / "bad_ts.csv"
    file_path.write_text(
        "timestamp_sec,field_name,original_value,corrected_value,reason,reviewer\n"
        "1.000,estimated_border,,100.0,manual,tester\n"
        "abc,duo_damage_diff,,200.0,manual,tester\n"
        "2.000,estimated_border,,150.0,manual,tester\n",
        encoding="utf-8",
    )

    loaded = read_review_csv(str(file_path))

    # The "abc" row must be dropped; the two valid rows must be returned.
    assert len(loaded) == 2
    assert loaded[0].timestamp_sec == 1.0
    assert loaded[1].timestamp_sec == 2.0