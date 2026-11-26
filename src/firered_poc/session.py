from __future__ import annotations

import numpy as np

from .audio import int16_to_float
from .config import AppConfig
from .segmenter import Segment, StreamingSegmenter
from .vad import VAD, make_vad


class Session:
    """Buffer arbitrary PCM chunks into fixed frames and emit sentence segments."""

    def __init__(self, vad: VAD, segmenter: StreamingSegmenter, frame_samples: int):
        self.vad = vad
        self.segmenter = segmenter
        self.frame_samples = frame_samples
        self._remainder = np.empty(0, dtype=np.float32)

    def push_pcm(self, pcm: bytes) -> list[Segment]:
        return self.push_samples(int16_to_float(pcm))

    def push_samples(self, samples: np.ndarray) -> list[Segment]:
        if samples.size:
            self._remainder = np.concatenate(
                [self._remainder, samples.astype(np.float32, copy=False)]
            )
        out: list[Segment] = []
        while self._remainder.size >= self.frame_samples:
            frame = self._remainder[: self.frame_samples]
            self._remainder = self._remainder[self.frame_samples :]
            out.extend(self.segmenter.feed(frame, self.vad.is_speech(frame)))
        return out

    def flush(self) -> list[Segment]:
        out: list[Segment] = []
        if self._remainder.size:
            pad = np.zeros(self.frame_samples - self._remainder.size, dtype=np.float32)
            frame = np.concatenate([self._remainder, pad])
            self._remainder = np.empty(0, dtype=np.float32)
            out.extend(self.segmenter.feed(frame, self.vad.is_speech(frame)))
        out.extend(self.segmenter.flush())
        return out


def build_session(cfg: AppConfig) -> Session:
    vad = make_vad(cfg.vad)
    segmenter = StreamingSegmenter(cfg.audio.sample_rate, cfg.audio.frame_ms, cfg.vad)
    return Session(vad, segmenter, cfg.audio.frame_samples)
