from __future__ import annotations

from pathlib import Path

import pytest

from firered_poc.asr import build_asr
from firered_poc.audio import float_to_int16, load_wav
from firered_poc.config import AppConfig

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25"
MODEL = MODEL_DIR / "model.int8.onnx"
TEST_WAV = MODEL_DIR / "test_wavs" / "0.wav"


@pytest.mark.skipif(not MODEL.exists(), reason="FireRedASR2 CTC model not downloaded")
def test_firered_ctc_transcribes_real_audio() -> None:
    cfg = AppConfig.load(ROOT / "configs" / "app.yaml")
    engine = build_asr(cfg.asr)
    samples, sample_rate = load_wav(TEST_WAV, cfg.audio.sample_rate)

    result = engine.transcribe(float_to_int16(samples), sample_rate)

    assert result.text
