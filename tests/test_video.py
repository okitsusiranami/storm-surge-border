from storm_surge_border.video import timestamp_to_frame_index


def test_timestamp_to_frame_index_basic() -> None:
    assert timestamp_to_frame_index(0.0, 60.0, 600) == 0
    assert timestamp_to_frame_index(1.0, 60.0, 600) == 60


def test_timestamp_to_frame_index_clamps() -> None:
    assert timestamp_to_frame_index(-1.0, 30.0, 300) == 0
    assert timestamp_to_frame_index(99.0, 30.0, 300) == 299