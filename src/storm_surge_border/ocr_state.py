from __future__ import annotations

from dataclasses import dataclass

from .ocr import SurgeOcrValue


@dataclass
class OcrStateTracker:
    last_attempt_ts: float | None = None
    last_valid_ts: float | None = None
    last_valid_gap_value: float | None = None
    last_valid_side: bool | None = None
    last_valid_confidence: float = 0.0

    def should_attempt(self, timestamp_sec: float, ocr_interval_sec: float) -> bool:
        if self.last_attempt_ts is None:
            return True
        return (timestamp_sec - self.last_attempt_ts) >= ocr_interval_sec

    def record_attempt(self, timestamp_sec: float, value: SurgeOcrValue) -> list[str]:
        self.last_attempt_ts = timestamp_sec

        # Atomic update: gap and side must be valid together.
        if value.gap_value is not None and value.is_above_border is not None:
            self.last_valid_ts = timestamp_sec
            self.last_valid_gap_value = value.gap_value
            self.last_valid_side = value.is_above_border
            self.last_valid_confidence = value.confidence
            return ["ocr-valid-pair"]

        if value.gap_value is not None or value.is_above_border is not None:
            return ["ocr-partial-invalid"]
        return ["ocr-missing"]

    def effective_value(
        self,
        timestamp_sec: float,
        *,
        decay_per_sec: float,
        stale_timeout_sec: float,
    ) -> tuple[float | None, bool | None, float, list[str]]:
        if self.last_valid_ts is None:
            return None, None, 0.0, ["ocr-no-valid"]

        elapsed = max(0.0, timestamp_sec - self.last_valid_ts)
        if elapsed > stale_timeout_sec:
            self.last_valid_ts = None
            self.last_valid_gap_value = None
            self.last_valid_side = None
            self.last_valid_confidence = 0.0
            return None, None, 0.0, ["ocr-stale-reset"]

        confidence = max(0.0, self.last_valid_confidence - (elapsed * max(0.0, decay_per_sec)))
        if elapsed == 0:
            return self.last_valid_gap_value, self.last_valid_side, confidence, ["ocr-direct"]
        return self.last_valid_gap_value, self.last_valid_side, confidence, ["ocr-carry"]