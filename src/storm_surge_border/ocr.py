from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SurgeOcrValue:
    gap_value: float | None
    is_above_border: bool | None
    confidence: float
    raw_text: str


def extract_surge_from_ocr_results(results: list[tuple]) -> SurgeOcrValue:
    if not results:
        return SurgeOcrValue(None, None, 0.0, "")

    texts: list[str] = []
    confs: list[float] = []
    for item in results:
        if len(item) < 3:
            continue
        text = str(item[1]).strip()
        try:
            conf = float(item[2])
        except (TypeError, ValueError):
            conf = 0.0
        if not text:
            continue
        texts.append(text)
        confs.append(max(0.0, min(1.0, conf)))

    joined = " ".join(texts)
    if not joined:
        return SurgeOcrValue(None, None, 0.0, "")

    number, side = _extract_consistent_number_and_side(joined)
    confidence = (sum(confs) / len(confs)) if confs else 0.0
    return SurgeOcrValue(number, side, confidence, joined)


def read_surge_from_frame(
    frame,
    reader,
) -> SurgeOcrValue:
    import cv2

    if frame is None or reader is None:
        return SurgeOcrValue(None, None, 0.0, "")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    results = reader.readtext(
        binary,
        detail=1,
        paragraph=False,
        allowlist="0123456789+-以上以下",
    )
    return extract_surge_from_ocr_results(results)


def _extract_consistent_number_and_side(text: str) -> tuple[float | None, bool | None]:
    number, side_from_number, has_number_conflict = _extract_number_and_side_from_tokens(text)
    side_from_words, has_word_conflict = _extract_side_from_words(text)

    if has_number_conflict or has_word_conflict:
        return None, None

    if side_from_words is not None and side_from_number is not None:
        if side_from_words != side_from_number:
            return None, None

    side = side_from_words if side_from_words is not None else side_from_number
    return number, side


def _extract_number_and_side_from_tokens(text: str) -> tuple[float | None, bool | None, bool]:
    matches = re.findall(r"([+-]?)(\d+)", text)
    if not matches:
        return None, None, False

    values = [int(num) for _sign, num in matches]
    abs_values = {abs(v) for v in values}
    if len(abs_values) != 1:
        return None, None, True

    explicit_signs = {sign for sign, _num in matches if sign in {"+", "-"}}
    if len(explicit_signs) > 1:
        return None, None, True

    side_from_number: bool | None = None
    if explicit_signs == {"+"}:
        side_from_number = True
    elif explicit_signs == {"-"}:
        side_from_number = False

    return float(next(iter(abs_values))), side_from_number, False


def _extract_side_from_words(text: str) -> tuple[bool | None, bool]:
    has_above = "以上" in text
    has_below = "以下" in text
    if has_above and has_below:
        return None, True
    if has_above:
        return True, False
    if has_below:
        return False, False
    return None, False