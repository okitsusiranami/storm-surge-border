from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from .models import EstimateRow


def write_plot_png(file_path: str, rows: list[EstimateRow]) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    x = [r.timestamp_sec for r in rows]
    y = [r.estimated_border if r.estimated_border is not None else float("nan") for r in rows]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(x, y, linewidth=1.2, color="#1f6aa5", label="estimated_border")
    ax.set_title("Storm Surge Border (Stage 1)")
    ax.set_xlabel("timestamp_sec")
    ax.set_ylabel("estimated_border")
    ax.grid(True, alpha=0.35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)