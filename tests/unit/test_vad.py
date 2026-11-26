from __future__ import annotations

import numpy as np

from firered_poc.vad import EnergyVAD


def _tone(size: int = 320, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(size, dtype=np.float32) / 16000
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def test_silence_is_not_speech() -> None:
    vad = EnergyVAD(threshold=0.02)
    assert not vad.is_speech(np.zeros(320, dtype=np.float32))


def test_tone_is_speech() -> None:
    vad = EnergyVAD(threshold=0.02)
    assert vad.is_speech(_tone())


def test_empty_frame_is_not_speech() -> None:
    vad = EnergyVAD(threshold=0.02)
    assert not vad.is_speech(np.empty(0, dtype=np.float32))
