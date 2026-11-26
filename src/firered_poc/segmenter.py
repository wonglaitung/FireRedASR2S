from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

from .audio import float_to_int16
from .config import VadConfig


@dataclass
class Segment:
    pcm: bytes
    start_ms: int
    end_ms: int
    sample_rate: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass
class _Frame:
    start: int
    samples: np.ndarray


class StreamingSegmenter:
    """Turn a stream of fixed frames plus VAD decisions into sentence segments.

    Pre-roll is taken from a small history buffer; post-roll is kept while
    waiting for the end-of-speech silence. Hard max forces a cut for long speech.
    """

    def __init__(self, sample_rate: int, frame_ms: int, cfg: VadConfig):
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.cfg = cfg

        self.pre_roll_samples = int(sample_rate * cfg.pre_roll_ms / 1000)
        self.post_roll_samples = int(sample_rate * cfg.post_roll_ms / 1000)
        self.end_silence_samples = int(sample_rate * cfg.max_end_silence_ms / 1000)
        self.min_speech_samples = int(sample_rate * cfg.min_speech_ms / 1000)
        self.hard_max_samples = int(sample_rate * cfg.hard_max_segment_ms / 1000)

        history_frames = max(1, math.ceil(cfg.pre_roll_ms / frame_ms) + 1)
        self.history: deque[_Frame] = deque(maxlen=history_frames)

        self.current: list[_Frame] = []
        self.speaking = False
        self.processed_samples = 0
        self.first_speech_start = 0
        self.last_speech_end = 0

    def feed(self, samples: np.ndarray, is_speech: bool) -> list[Segment]:
        if samples.size == 0:
            return []

        frame = _Frame(self.processed_samples, np.asarray(samples, dtype=np.float32))
        self.processed_samples += frame.samples.size
        self.history.append(frame)

        out: list[Segment] = []

        if is_speech:
            if not self.speaking:
                self.speaking = True
                self.current = list(self.history)
                self.first_speech_start = frame.start
            else:
                self.current.append(frame)
            self.last_speech_end = frame.start + frame.samples.size
        elif self.speaking:
            self.current.append(frame)
            if self.processed_samples - self.last_speech_end >= self.end_silence_samples:
                segment = self._finalize()
                self._reset()
                if segment is not None:
                    out.append(segment)
                return out

        if self.speaking and self.current:
            current_duration = self.processed_samples - self.current[0].start
            if current_duration >= self.hard_max_samples:
                segment = self._finalize(hard=True)
                self._reset()
                if segment is not None:
                    out.append(segment)

        return out

    def flush(self) -> list[Segment]:
        if not self.speaking:
            return []
        segment = self._finalize()
        self._reset()
        return [segment] if segment is not None else []

    def _finalize(self, hard: bool = False) -> Segment | None:
        if not self.current:
            return None
        if self.last_speech_end <= self.first_speech_start:
            return None
        if self.last_speech_end - self.first_speech_start < self.min_speech_samples:
            return None

        base = self.current[0].start
        seg_start = max(base, self.first_speech_start - self.pre_roll_samples)
        if hard:
            seg_end = min(base + self.hard_max_samples, self.processed_samples)
        else:
            seg_end = min(self.last_speech_end + self.post_roll_samples, self.processed_samples)
        if seg_end <= seg_start:
            return None

        buffer = np.concatenate([frame.samples for frame in self.current])
        lo = max(0, seg_start - base)
        hi = min(buffer.size, seg_end - base)
        chunk = buffer[lo:hi]
        if chunk.size == 0:
            return None

        return Segment(
            pcm=float_to_int16(chunk),
            start_ms=int(round(seg_start / self.sample_rate * 1000)),
            end_ms=int(round(seg_end / self.sample_rate * 1000)),
            sample_rate=self.sample_rate,
        )

    def _reset(self) -> None:
        self.current = []
        self.speaking = False
        self.first_speech_start = 0
        self.last_speech_end = 0


def merge_segments(
    segments: list[Segment],
    sample_rate: int,
    max_gap_ms: int,
    hard_max_ms: int,
) -> list[Segment]:
    """Merge close segments so short pauses do not destroy sentence context.

    Pauses are filled with digital silence to keep timestamps monotonic.
    """
    if not segments or max_gap_ms < 0:
        return list(segments)

    merged = [segments[0]]
    for nxt in segments[1:]:
        cur = merged[-1]
        gap_ms = nxt.start_ms - cur.end_ms
        if gap_ms > max_gap_ms or nxt.end_ms - cur.start_ms > hard_max_ms:
            merged.append(nxt)
            continue

        gap_samples = int(round(max(0, gap_ms) * sample_rate / 1000))
        pcm = cur.pcm + b"\x00\x00" * gap_samples + nxt.pcm
        merged[-1] = Segment(
            pcm=pcm,
            start_ms=cur.start_ms,
            end_ms=nxt.end_ms,
            sample_rate=sample_rate,
        )

    return merged
