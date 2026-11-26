from __future__ import annotations

from firered_poc.segmenter import Segment, merge_segments

SAMPLE_RATE = 16000


def _segment(start_ms: int, end_ms: int, samples: int = 160) -> Segment:
    return Segment(
        pcm=b"\x01\x00" * samples,
        start_ms=start_ms,
        end_ms=end_ms,
        sample_rate=SAMPLE_RATE,
    )


def test_merge_close_segments_fills_gap() -> None:
    merged = merge_segments(
        [_segment(0, 100), _segment(150, 250)],
        SAMPLE_RATE,
        max_gap_ms=100,
        hard_max_ms=1000,
    )

    assert len(merged) == 1
    assert merged[0].start_ms == 0
    assert merged[0].end_ms == 250
    gap_bytes = int(round(50 * SAMPLE_RATE / 1000)) * 2
    assert len(merged[0].pcm) == 320 + gap_bytes + 320


def test_merge_skips_large_gap() -> None:
    merged = merge_segments(
        [_segment(0, 100), _segment(300, 400)],
        SAMPLE_RATE,
        max_gap_ms=100,
        hard_max_ms=1000,
    )
    assert len(merged) == 2


def test_merge_respects_hard_max() -> None:
    merged = merge_segments(
        [_segment(0, 500), _segment(550, 1200)],
        SAMPLE_RATE,
        max_gap_ms=100,
        hard_max_ms=1000,
    )
    assert len(merged) == 2


def test_merge_overlapping_segments_without_gap() -> None:
    merged = merge_segments(
        [_segment(0, 200), _segment(150, 300)],
        SAMPLE_RATE,
        max_gap_ms=100,
        hard_max_ms=1000,
    )
    assert len(merged) == 1
    assert len(merged[0].pcm) == 640


def test_merge_disabled() -> None:
    segments = [_segment(0, 100), _segment(110, 200)]
    assert merge_segments(segments, SAMPLE_RATE, -1, 1000) == segments
