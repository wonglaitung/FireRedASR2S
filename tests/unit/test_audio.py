from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from firered_poc.audio import float_to_int16, load_wav, resample_linear


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(float_to_int16(samples))


def test_load_wav_roundtrip(tmp_path: Path) -> None:
    sample_rate = 16000
    t = np.arange(sample_rate, dtype=np.float32) / sample_rate
    samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    path = tmp_path / "tone.wav"
    _write_wav(path, samples, sample_rate)

    loaded, got_rate = load_wav(path, sample_rate)

    assert got_rate == sample_rate
    assert loaded.size == samples.size
    assert np.max(np.abs(loaded - samples)) < 1e-3


def test_resample_linear_length() -> None:
    samples = np.zeros(16000, dtype=np.float32)
    out = resample_linear(samples, 16000, 8000)
    assert out.size == 8000


def test_int16_roundtrip_tolerance() -> None:
    samples = np.array([0.0, 0.25, -0.5, 0.999], dtype=np.float32)
    restored = np.frombuffer(float_to_int16(samples), dtype="<i2") / 32767.0
    assert np.max(np.abs(restored - samples)) < 1e-3
