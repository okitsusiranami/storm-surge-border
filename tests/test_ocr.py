import numpy as np

from storm_surge_border.ocr import extract_surge_from_ocr_results, read_surge_from_frame


def test_extract_surge_with_above_text() -> None:
    res = extract_surge_from_ocr_results(
        [
            ([[0, 0], [1, 0], [1, 1], [0, 1]], "以上", 0.90),
            ([[0, 0], [1, 0], [1, 1], [0, 1]], "+123", 0.80),
        ]
    )
    assert res.gap_value == 123.0
    assert res.is_above_border is True
    assert res.confidence > 0.0


def test_extract_surge_with_below_text() -> None:
    res = extract_surge_from_ocr_results(
        [
            ([[0, 0], [1, 0], [1, 1], [0, 1]], "以下", 0.90),
            ([[0, 0], [1, 0], [1, 1], [0, 1]], "-88", 0.70),
        ]
    )
    assert res.gap_value == 88.0
    assert res.is_above_border is False


def test_extract_surge_no_number() -> None:
    res = extract_surge_from_ocr_results(
        [
            ([[0, 0], [1, 0], [1, 1], [0, 1]], "以上", 0.90),
        ]
    )
    assert res.gap_value is None
    assert res.is_above_border is True


def test_read_surge_from_frame_with_none_reader_returns_empty() -> None:
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    res = read_surge_from_frame(frame, None)
    assert res.gap_value is None
    assert res.is_above_border is None
    assert res.confidence == 0.0