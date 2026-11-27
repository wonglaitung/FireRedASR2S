from __future__ import annotations

import numpy as np

from firered_recorder.audio import PcmFramer, convert_capture, level_percent


def _sine(size: int, sample_rate: int = 16000, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(size, dtype=np.float32) / sample_rate
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def test_convert_int16_mono() -> None:
    samples = (_sine(320) * 32767).astype("<i2")
    out = convert_capture(samples.tobytes(), "Int16", 1, 16000)
    expected = samples.astype(np.float32) / 32768.0
    assert out.shape == (320,)
    assert np.max(np.abs(out - expected)) < 1e-6


def test_convert_stereo_mixes_to_mono() -> None:
    mono = (_sine(320) * 32767).astype("<i2")
    stereo = np.column_stack([mono, mono]).reshape(-1)
    out = convert_capture(stereo.tobytes(), "Int16", 2, 16000)
    assert out.shape == (320,)
    assert np.max(np.abs(out - mono.astype(np.float32) / 32768.0)) < 1e-6


def test_convert_resamples_to_16k() -> None:
    samples = (_sine(160, sample_rate=8000) * 32767).astype("<i2")
    out = convert_capture(samples.tobytes(), "Int16", 1, 8000)
    assert out.shape == (320,)


def test_framer_emits_fixed_frames() -> None:
    framer = PcmFramer(frame_samples=320)
    assert framer.push(np.zeros(100, dtype=np.float32)) == []

    frames = framer.push(np.zeros(220, dtype=np.float32))
    assert len(frames) == 1
    assert len(frames[0]) == 640

    frames = framer.push(np.zeros(700, dtype=np.float32))
    assert len(frames) == 2


def test_level_percent() -> None:
    assert level_percent(np.zeros(320, dtype=np.float32)) == 0
    assert level_percent(_sine(320, amplitude=0.5)) > 0
