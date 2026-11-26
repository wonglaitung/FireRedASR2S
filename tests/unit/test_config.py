from __future__ import annotations

from pathlib import Path

from firered_poc.config import AppConfig


def test_load_repo_config() -> None:
    root = Path(__file__).resolve().parents[2]
    cfg = AppConfig.load(root / "configs" / "app.yaml")

    assert cfg.audio.sample_rate == 16000
    assert cfg.audio.frame_samples == 320
    assert cfg.vad.max_end_silence_ms == 450
    assert cfg.vad.backend == "silero"
    assert cfg.asr.backend == "firered_aed"
    assert cfg.asr.encoder
