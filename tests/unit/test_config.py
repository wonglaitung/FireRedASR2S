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


def test_load_official_aed_config() -> None:
    root = Path(__file__).resolve().parents[2]
    cfg = AppConfig.load(root / "configs" / "app_official.yaml")

    assert cfg.asr.backend == "firered_aed_torch"
    assert cfg.asr.model_dir.endswith("FireRedASR2-AED")
    assert cfg.asr.use_gpu is True
    assert cfg.asr.use_half is True
    assert cfg.asr.beam_size == 10
    assert cfg.asr.nbest == 10
    assert cfg.asr.lm_path.endswith("mce_lm.json")
