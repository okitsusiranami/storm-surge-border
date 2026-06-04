from storm_surge_border.video import timestamp_to_frame_index
from storm_surge_border.video import VideoFrameReader


def test_timestamp_to_frame_index_basic() -> None:
    assert timestamp_to_frame_index(0.0, 60.0, 600) == 0
    assert timestamp_to_frame_index(1.0, 60.0, 600) == 60


def test_timestamp_to_frame_index_clamps() -> None:
    assert timestamp_to_frame_index(-1.0, 30.0, 300) == 0
    assert timestamp_to_frame_index(99.0, 30.0, 300) == 299


def test_timestamp_to_frame_index_unknown_frame_count_defaults_zero() -> None:
    # Unknown frame_count keeps timestamp-based index without upper clamp.
    assert timestamp_to_frame_index(3.0, 30.0, 0) == 90


def test_video_frame_reader_unknown_frame_count_uses_msec_seek(monkeypatch, tmp_path) -> None:
    from storm_surge_border import video as video_mod

    class _FakeCap:
        def __init__(self) -> None:
            self.props = {
                1: 60.0,
                2: 0,
            }
            self.set_calls = []

        def isOpened(self):
            return True

        def get(self, prop):
            return self.props.get(prop, 0)

        def set(self, prop, value):
            self.set_calls.append((prop, value))
            return True

        def read(self):
            return True, object()

        def release(self):
            return None

    class _FakeCV2:
        CAP_PROP_FPS = 1
        CAP_PROP_FRAME_COUNT = 2
        CAP_PROP_POS_MSEC = 3
        CAP_PROP_POS_FRAMES = 4

        def __init__(self):
            self.cap = _FakeCap()

        def VideoCapture(self, _path):
            return self.cap

    _fake_cv2 = _FakeCV2()
    monkeypatch.setitem(__import__("sys").modules, "cv2", _fake_cv2)

    fake_file = tmp_path / "x.mp4"
    fake_file.write_text("x", encoding="utf-8")

    with VideoFrameReader(str(fake_file)) as r:
        frame = r.read_at(1.5)
        assert frame is not None
        assert any(call[0] == _fake_cv2.CAP_PROP_POS_MSEC for call in _fake_cv2.cap.set_calls)


def test_video_frame_reader_backward_seek_uses_frame_seek(monkeypatch, tmp_path) -> None:
    class _FakeCap:
        def __init__(self) -> None:
            self.props = {1: 10.0, 2: 100}
            self.set_calls = []
            self.current = 0

        def isOpened(self):
            return True

        def get(self, prop):
            return self.props.get(prop, 0)

        def set(self, prop, value):
            self.set_calls.append((prop, value))
            if prop == 4:
                self.current = int(value)
            return True

        def read(self):
            self.current += 1
            return True, object()

        def release(self):
            return None

    class _FakeCV2:
        CAP_PROP_FPS = 1
        CAP_PROP_FRAME_COUNT = 2
        CAP_PROP_POS_MSEC = 3
        CAP_PROP_POS_FRAMES = 4

        def __init__(self):
            self.cap = _FakeCap()

        def VideoCapture(self, _path):
            return self.cap

    _fake_cv2 = _FakeCV2()
    monkeypatch.setitem(__import__("sys").modules, "cv2", _fake_cv2)

    fake_file = tmp_path / "x2.mp4"
    fake_file.write_text("x", encoding="utf-8")

    with VideoFrameReader(str(fake_file)) as r:
        assert r.read_at(3.0) is not None
        assert r.read_at(1.0) is not None

    assert any(call[0] == _fake_cv2.CAP_PROP_POS_FRAMES for call in _fake_cv2.cap.set_calls)