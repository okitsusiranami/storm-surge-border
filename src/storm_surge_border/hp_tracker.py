from __future__ import annotations

from dataclasses import dataclass

from .hp import detect_received_damage


@dataclass
class HpDamageTracker:
    max_pool: float
    min_drop_ratio: float
    max_drop_ratio: float
    confirm_frames: int
    smoothing_alpha: float
    _prev_raw_ratio: float | None = None
    _prev_smoothed_ratio: float | None = None
    _streak: int = 0
    _pending: float = 0.0
    _confirmed_in_sequence: bool = False

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

        add = self._confirm_once(event.damage)
        flags = [event.flag]
        if add > 0:
            flags.append("hp-confirmed")
        return add, flags

    def _smooth(self, current_raw_ratio: float | None) -> float | None:
        if current_raw_ratio is None:
            return None

        if self._prev_raw_ratio is None:
            self._prev_raw_ratio = current_raw_ratio
            return current_raw_ratio

        smoothed = (
            (self.smoothing_alpha * current_raw_ratio)
            + ((1.0 - self.smoothing_alpha) * self._prev_raw_ratio)
        )
        self._prev_raw_ratio = current_raw_ratio
        return smoothed

    def _confirm_once(self, damage: float) -> float:
        if damage <= 0:
            self._streak = 0
            self._pending = 0.0
            self._confirmed_in_sequence = False
            return 0.0

        if self._confirmed_in_sequence:
            return 0.0

        self._streak += 1
        self._pending += damage
        if self._streak == self.confirm_frames:
            out = self._pending
            self._pending = 0.0
            self._confirmed_in_sequence = True
            return out
        return 0.0