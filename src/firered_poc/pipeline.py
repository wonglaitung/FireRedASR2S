from __future__ import annotations

import numpy as np

from .config import AppConfig
from .segmenter import Segment, StreamingSegmenter
from .vad import make_vad


def segment_audio(samples: np.ndarray, sample_rate: int, cfg: AppConfig) -> list[Segment]:
    """Run VAD + segmenter over a completed waveform (used by the CLI)."""
    frame_samples = int(sample_rate * cfg.audio.frame_ms / 1000)
    vad = make_vad(cfg.vad, sample_rate)
    segmenter = StreamingSegmenter(sample_rate, cfg.audio.frame_ms, cfg.vad)

    out: list[Segment] = []
    for offset in range(0, samples.size, frame_samples):
        frame = samples[offset : offset + frame_samples]
        if frame.size < frame_samples:
            frame = np.pad(frame, (0, frame_samples - frame.size))
        out.extend(segmenter.feed(frame, vad.is_speech(frame)))
    out.extend(segmenter.flush())
    return out
