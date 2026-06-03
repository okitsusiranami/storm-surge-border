from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EstimateRow:
    timestamp_sec: float
    duo_damage_diff: Optional[float]
    surge_gap_value: Optional[float]
    is_above_border: Optional[bool]
    estimated_border: Optional[float]
    confidence: float
    source_flags: str = ""


@dataclass
class CorrectionRow:
    timestamp_sec: float
    field_name: str
    original_value: Optional[str]
    corrected_value: Optional[str]
    reason: str = ""
    reviewer: str = ""


@dataclass
class VideoMeta:
    width: int
    height: int
    fps: float
    frame_count: int
    duration_sec: float


@dataclass
class RoiSet:
    center_bottom_hp: tuple[float, float, float, float]
    center_reticle: tuple[float, float, float, float]
    top_right_surge: tuple[float, float, float, float]


@dataclass
class PipelineResult:
    estimates: list[EstimateRow] = field(default_factory=list)
    review_rows: list[CorrectionRow] = field(default_factory=list)