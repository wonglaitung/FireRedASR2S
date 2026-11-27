from __future__ import annotations

import numpy as np

from firered_poc.audio import float_to_int16, resample_linear

SAMPLE_RATE = 16000
FRAME_MS = 20
FRAME_SAMPLES = 320


def convert_capture(
    data: bytes,
    sample_format: str,
    channels: int,
    sample_rate: int,
) -> np.ndarray:
    """Convert raw Qt audio bytes to mono float32 at 16 kHz."""
    fmt = sample_format.lower()
    if fmt in {"int16", "int16le"}:
        dtype, scale = "<i2", 32768.0
    elif fmt in {"int32", "int32le"}:
        dtype, scale = "<i4", 2147483648.0
    elif fmt in {"float", "float32"}:
        dtype, scale = "<f4", 1.0
    elif fmt == "uint8":
        dtype, scale = np.uint8, 1.0
    else:
        raise ValueError(f"unsupported sample format: {sample_format}")

    itemsize = np.dtype(dtype).itemsize
    data = data[: len(data) - (len(data) % itemsize)]
    samples = np.frombuffer(data, dtype=dtype)

    if fmt == "uint8":
        samples = (samples.astype(np.float32) - 128.0) / 128.0
    else:
        samples = samples.astype(np.float32) / scale

    channels = max(1, channels)
    usable = (samples.size // channels) * channels
    samples = samples[:usable]

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    if sample_rate != SAMPLE_RATE:
        samples = resample_linear(samples, sample_rate, SAMPLE_RATE)

    return samples.astype(np.float32, copy=False)


class PcmFramer:
    """Accumulate float samples and emit fixed-size 16-bit PCM frames."""

    def __init__(self, frame_samples: int = FRAME_SAMPLES):
        self.frame_samples = frame_samples
        self._buffer = np.empty(0, dtype=np.float32)

    def push(self, samples: np.ndarray) -> list[bytes]:
        if samples.size:
            self._buffer = np.concatenate(
                [self._buffer, samples.astype(np.float32, copy=False)]
            )
        frames: list[bytes] = []
        while self._buffer.size >= self.frame_samples:
            chunk = self._buffer[: self.frame_samples]
            self._buffer = self._buffer[self.frame_samples :]
            frames.append(float_to_int16(chunk))
        return frames

    def reset(self) -> None:
        self._buffer = np.empty(0, dtype=np.float32)


def level_percent(frame: np.ndarray) -> int:
    if frame.size == 0:
        return 0
    rms = float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))))
    return max(0, min(100, int(round(rms * 300))))
