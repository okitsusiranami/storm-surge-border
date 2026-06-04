from __future__ import annotations

from dataclasses import dataclass

from .hp import detect_received_damage


@dataclass
class HpDamageTracker:
    """Track HP-bar drop events with debounce-style confirmation windows.

    Stage-1 heuristic: each contiguous drop sequence is split into windows of
    ``confirm_frames``. When a window closes, the accumulated pending damage is
    emitted. This keeps noise rejection while allowing long continuous drops to
    continue contributing instead of being counted only once.
    """

    max_pool: float
    min_drop_ratio: float
    max_drop_ratio: float
    confirm_frames: int
    smoothing_alpha: float
    _prev_smoothed_ratio: float | None = None
    _streak: int = 0
    _pending: float = 0.0

    def update(self, current_raw_ratio: float | None) -> tuple[float, list[str]]:
        smoothed = self._smooth(current_raw_ratio)
        event = detect_received_damage(
            self._prev_smoothed_ratio,
            smoothed,
            max_pool=self.max_pool,
            min_drop_ratio=self.min_drop_ratio,
            max_drop_ratio=self.max_drop_ratio,
        )

        if smoothed is not None:
            self._prev_smoothed_ratio = smoothed

        add, is_provisional = self._confirm_windowed(event.damage)
        flags = [event.flag]
        if add > 0:
            if is_provisional:
                flags.append("hp-provisional")
            else:
                flags.append("hp-confirmed")
        return add, flags

    def _smooth(self, current_raw_ratio: float | None) -> float | None:
        if current_raw_ratio is None:
            return None

        if self._prev_smoothed_ratio is None:
            return current_raw_ratio

        smoothed = (
            (self.smoothing_alpha * current_raw_ratio)
            + ((1.0 - self.smoothing_alpha) * self._prev_smoothed_ratio)
        )
        return smoothed

    def _confirm_windowed(self, damage: float) -> tuple[float, bool]:
        if damage <= 0:
            if self._streak > 0 and self._streak < self.confirm_frames and self._pending > 0:
                out = self._pending
                self._streak = 0
                self._pending = 0.0
                return out, True
            self._streak = 0
            self._pending = 0.0
            return 0.0, False

        self._streak += 1
        self._pending += damage
        if self._streak >= self.confirm_frames:
            out = self._pending
            self._pending = 0.0
            self._streak = 0
            return out, False
        return 0.0, False