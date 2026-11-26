from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from firered_poc.audio import load_wav
from firered_poc.config import VadConfig
from firered_poc.vad import make_vad

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25"
SILERO = ROOT / "models" / "silero_vad.onnx"
TEST_WAV = MODEL_DIR / "test_wavs" / "0.wav"

pytestmark = pytest.mark.skipif(
    not (SILERO.exists() and TEST_WAV.exists()),
    reason="Silero VAD or test audio not downloaded",
)


def test_silero_detects_speech_in_real_audio() -> None:
    cfg = VadConfig(backend="silero", silero_model=str(SILERO))
    vad = make_vad(cfg, 16000)
    samples, _ = load_wav(TEST_WAV, 16000)
    frame_samples = 320

    decisions = []
    for offset in range(0, samples.size - frame_samples + 1, frame_samples):
        frame = samples[offset : offset + frame_samples]
        decisions.append(vad.is_speech(frame))

    assert any(decisions)
    assert not all(decisions)


def test_silero_ignores_digital_silence() -> None:
    cfg = VadConfig(backend="silero", silero_model=str(SILERO))
    vad = make_vad(cfg, 16000)
    silence = np.zeros(320, dtype=np.float32)

    decisions = [vad.is_speech(silence) for _ in range(20)]

    assert not any(decisions)
