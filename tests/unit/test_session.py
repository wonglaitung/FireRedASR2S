from __future__ import annotations

import numpy as np

from firered_poc.audio import float_to_int16
from firered_poc.config import AppConfig, AudioConfig, VadConfig
from firered_poc.session import build_session

SAMPLE_RATE = 16000


def _tone(seconds: float = 0.5, amplitude: float = 0.5) -> np.ndarray:
    size = int(SAMPLE_RATE * seconds)
    t = np.arange(size, dtype=np.float32) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def test_session_buffers_odd_chunks() -> None:
    cfg = AppConfig(
        audio=AudioConfig(sample_rate=SAMPLE_RATE, frame_ms=20),
        vad=VadConfig(
            pre_roll_ms=300,
            post_roll_ms=300,
            max_end_silence_ms=450,
            min_speech_ms=250,
            hard_max_segment_ms=15000,
        ),
    )
    session = build_session(cfg)

    wave = np.concatenate([_tone(0.5), np.zeros(SAMPLE_RATE, dtype=np.float32)])
    pcm = float_to_int16(wave)

    out = []
    step = 1000
    for offset in range(0, len(pcm), step):
        out.extend(session.push_pcm(pcm[offset : offset + step]))
    out.extend(session.flush())

    assert len(out) == 1
    assert out[0].duration_ms >= 500


def test_empty_chunk_is_noop() -> None:
    cfg = AppConfig(
        audio=AudioConfig(sample_rate=SAMPLE_RATE, frame_ms=20),
        vad=VadConfig(),
    )
    session = build_session(cfg)
    assert session.push_pcm(b"") == []
