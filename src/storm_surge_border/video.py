from __future__ import annotations

from pathlib import Path

import numpy as np

from .models import VideoMeta


def timestamp_to_frame_index(timestamp_sec: float, fps: float, frame_count: int) -> int:
    if fps <= 0:
        raise ValueError("fps must be > 0")
    idx = int(round(max(0.0, timestamp_sec) * fps))
    if frame_count <= 0:
        return max(0, idx)
    return max(0, min(frame_count - 1, idx))


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


class VideoFrameReader:
    """Persistent video reader optimized for increasing timestamps."""

    def __init__(self, video_path: str) -> None:
        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError("opencv-python is required") from exc

        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"video not found: {video_path}")

        self._cv2 = cv2
        self.video_path = video_path
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise RuntimeError(f"failed to open video: {video_path}")

        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.has_known_frame_count = self.frame_count > 0
        if self.fps <= 0.0:
            self.cap.release()
            raise RuntimeError(f"invalid fps in video: {video_path}")
        self._next_index = 0

    def __enter__(self) -> "VideoFrameReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if getattr(self, "cap", None) is not None:
            self.cap.release()

    def read_at(self, timestamp_sec: float) -> np.ndarray | None:
        if not self.has_known_frame_count:
            # Backend may not expose frame count for some codecs/containers.
            self.cap.set(self._cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp_sec) * 1000.0)
            ok, frame = self.cap.read()
            if not ok:
                return None
            return frame

        target = timestamp_to_frame_index(timestamp_sec, self.fps, self.frame_count)
        if target < self._next_index:
            self.cap.set(self._cv2.CAP_PROP_POS_FRAMES, target)
            self._next_index = target

        frame = None
        while self._next_index <= target:
            ok, frame = self.cap.read()
            if not ok:
                return None
            self._next_index += 1
        return frame