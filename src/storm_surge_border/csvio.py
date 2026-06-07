from __future__ import annotations

import csv
from pathlib import Path

from .models import CorrectionRow, EstimateRow


def write_estimates_csv(file_path: str, rows: list[EstimateRow]) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp_sec",
                "duo_damage_diff",
                "surge_gap_value",
                "is_above_border",
                "estimated_border",
                "confidence",
                "estimated_border_status",
                "source_flags",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    f"{row.timestamp_sec:.3f}",
                    _fmt_optional_float(row.duo_damage_diff),
                    _fmt_optional_float(row.surge_gap_value),
                    "" if row.is_above_border is None else str(row.is_above_border),
                    _fmt_optional_float(row.estimated_border),
                    f"{row.confidence:.3f}",
                    row.estimated_border_status,
                    row.source_flags,
                ]
            )


def write_review_csv(file_path: str, rows: list[CorrectionRow]) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp_sec",
                "field_name",
                "original_value",
                "corrected_value",
                "reason",
                "reviewer",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    f"{row.timestamp_sec:.3f}",
                    row.field_name,
                    "" if row.original_value is None else row.original_value,
                    "" if row.corrected_value is None else row.corrected_value,
                    row.reason,
                    row.reviewer,
                ]
            )


def read_review_csv(file_path: str) -> list[CorrectionRow]:
    path = Path(file_path)
    if not path.exists():
        return []

    rows: list[CorrectionRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for line in reader:
            if not line.get("timestamp_sec") or not line.get("field_name"):
                continue
            try:
                timestamp_sec = float(line["timestamp_sec"])
            except ValueError:
                continue
            rows.append(
                CorrectionRow(
                    timestamp_sec=timestamp_sec,
                    field_name=line["field_name"],
                    original_value=line.get("original_value") or None,
                    corrected_value=line.get("corrected_value") or None,
                    reason=line.get("reason") or "",
                    reviewer=line.get("reviewer") or "",
                )
            )
    return rows


def _fmt_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"