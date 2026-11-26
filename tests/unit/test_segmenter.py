from __future__ import annotations

import numpy as np

from firered_poc.config import VadConfig
from firered_poc.segmenter import Segment, StreamingSegmenter

SAMPLE_RATE = 16000
FRAME_MS = 20
FRAME_SAMPLES = 320


def _tone(amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(FRAME_SAMPLES, dtype=np.float32) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def _make_segmenter() -> StreamingSegmenter:
    cfg = VadConfig(
        pre_roll_ms=300,
        post_roll_ms=300,
        max_end_silence_ms=450,
        min_speech_ms=250,
        hard_max_segment_ms=15000,
    )
    return StreamingSegmenter(SAMPLE_RATE, FRAME_MS, cfg)


def _run(pattern: list[bool]) -> tuple[list[Segment], StreamingSegmenter]:
    segmenter = _make_segmenter()
    out: list[Segment] = []
    for is_speech in pattern:
        frame = _tone() if is_speech else np.zeros(FRAME_SAMPLES, dtype=np.float32)
        out.extend(segmenter.feed(frame, is_speech))
    return out, segmenter


def test_segment_includes_pre_and_post_roll() -> None:
    pattern = [False] * 20 + [True] * 25 + [False] * 30
    out, _ = _run(pattern)

    assert len(out) == 1
    segment = out[0]
    assert 80 <= segment.start_ms <= 140
    assert 1100 <= segment.end_ms <= 1300
    assert segment.duration_ms >= 1000


def test_short_speech_is_dropped() -> None:
    pattern = [False] * 20 + [True] * 5 + [False] * 30
    out, segmenter = _run(pattern)
    out.extend(segmenter.flush())
    assert out == []


def test_hard_max_splits_long_speech() -> None:
    pattern = [True] * 1000
    out, segmenter = _run(pattern)
    out.extend(segmenter.flush())

    assert len(out) >= 2
    assert out[0].end_ms <= 15100
    assert out[0].duration_ms >= 14000


def test_flush_emits_pending_speech() -> None:
    pattern = [True] * 25
    out, segmenter = _run(pattern)
    assert out == []

    out.extend(segmenter.flush())
    assert len(out) == 1
    assert out[0].duration_ms >= 500
