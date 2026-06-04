from storm_surge_border.ocr import SurgeOcrValue
from storm_surge_border.ocr_state import OcrStateTracker


def test_ocr_state_atomic_pair_update_rejects_partial() -> None:
    state = OcrStateTracker()
    state.record_attempt(0.0, SurgeOcrValue(100.0, True, 0.9, "+100"))
    flags = state.record_attempt(1.0, SurgeOcrValue(200.0, None, 0.8, "200"))

    gap, side, conf, eff_flags = state.effective_value(
        1.0,
        decay_per_sec=0.0,
        stale_timeout_sec=10.0,
    )
    assert "ocr-partial-invalid" in flags
    assert gap == 100.0
    assert side is True
    assert conf == 0.9
    assert "ocr-carry" in eff_flags


def test_ocr_state_stale_uses_last_valid_ts() -> None:
    state = OcrStateTracker()
    state.record_attempt(0.0, SurgeOcrValue(100.0, True, 0.9, "+100"))
    # Attempt later but invalid; valid timestamp should remain 0.0.
    state.record_attempt(5.0, SurgeOcrValue(None, None, 0.1, ""))

    gap, side, conf, flags = state.effective_value(
        6.0,
        decay_per_sec=0.0,
        stale_timeout_sec=5.0,
    )
    assert gap is None
    assert side is None
    assert conf == 0.0
    assert "ocr-stale-reset" in flags