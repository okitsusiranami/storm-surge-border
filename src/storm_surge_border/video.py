from __future__ import annotations

from pathlib import Path

from .models import VideoMeta


def read_video_meta(video_path: str) -> VideoMeta:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("opencv-python is required") from exc

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"video not found: {video_path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"failed to open video: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()

    if fps <= 0.0:
        raise RuntimeError(f"invalid fps in video: {video_path}")

    return VideoMeta(
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_sec=frame_count / fps,
    )