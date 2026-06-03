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

    number = _extract_number(joined)
    side = _extract_side(joined)
    confidence = (sum(confs) / len(confs)) if confs else 0.0
    return SurgeOcrValue(number, side, confidence, joined)


def read_surge_from_frame(
    frame,
    reader,
) -> SurgeOcrValue:
    import cv2

    if frame is None:
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


def _extract_number(text: str) -> float | None:
    m = re.search(r"[-+]?\d+", text)
    if not m:
        return None
    return float(abs(int(m.group(0))))


def _extract_side(text: str) -> bool | None:
    if "以上" in text:
        return True
    if "以下" in text:
        return False
    if "+" in text:
        return True
    if "-" in text:
        return False
    return None