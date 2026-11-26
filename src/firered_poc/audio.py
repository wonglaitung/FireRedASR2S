from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def load_wav(path: str | Path, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """Load a WAV file as mono float32 in [-1, 1], resampling if needed."""
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    if width == 1:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported sample width: {width} bytes")

    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)

    if sample_rate != target_sr:
        data = resample_linear(data, sample_rate, target_sr)
        sample_rate = target_sr

    return data.astype(np.float32, copy=False), sample_rate


def resample_linear(samples: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Simple linear resampler for POC use."""
    if sr_in == sr_out or samples.size == 0:
        return samples.astype(np.float32, copy=False)
    n_out = max(1, int(round(samples.size * sr_out / sr_in)))
    t_in = np.arange(samples.size, dtype=np.float64)
    t_out = np.linspace(0.0, samples.size - 1, n_out, dtype=np.float64)
    return np.interp(t_out, t_in, samples).astype(np.float32)


def int16_to_float(pcm: bytes) -> np.ndarray:
    if len(pcm) % 2:
        pcm = pcm[:-1]
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


def float_to_int16(samples: np.ndarray) -> bytes:
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


def rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))))
