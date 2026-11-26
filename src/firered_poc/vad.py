from __future__ import annotations

from typing import Protocol

import numpy as np

from .audio import rms
from .config import VadConfig


class VAD(Protocol):
    def is_speech(self, frame: np.ndarray) -> bool: ...


class EnergyVAD:
    """Energy-based VAD for POC; replaceable with Silero VAD later."""

    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold

    def is_speech(self, frame: np.ndarray) -> bool:
        return rms(frame) >= self.threshold


class SileroVAD:
    """Silero VAD via sherpa-onnx; accepts arbitrary frame sizes."""

    def __init__(
        self,
        model: str,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_silence_ms: int = 500,
        min_speech_ms: int = 250,
        max_speech_ms: int = 20000,
        window_size: int = 512,
    ):
        import sherpa_onnx

        config = sherpa_onnx.VadModelConfig(
            silero_vad=sherpa_onnx.SileroVadModelConfig(
                model=model,
                threshold=threshold,
                min_silence_duration=min_silence_ms / 1000,
                min_speech_duration=min_speech_ms / 1000,
                max_speech_duration=max_speech_ms / 1000,
                window_size=window_size,
            ),
            sample_rate=sample_rate,
            num_threads=1,
            provider="cpu",
        )
        self._vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)

    def is_speech(self, frame: np.ndarray) -> bool:
        self._vad.accept_waveform(frame.tolist())
        while not self._vad.empty():
            self._vad.pop()
        return bool(self._vad.is_speech_detected())


def make_vad(cfg: VadConfig, sample_rate: int = 16000) -> VAD:
    if cfg.backend == "energy":
        return EnergyVAD(cfg.energy_threshold)
    if cfg.backend == "silero":
        if not cfg.silero_model:
            raise ValueError("Silero VAD requires vad.silero_model")
        return SileroVAD(
            model=cfg.silero_model,
            sample_rate=sample_rate,
            threshold=cfg.silero_threshold,
            min_silence_ms=cfg.silero_min_silence_ms,
            min_speech_ms=cfg.silero_min_speech_ms,
            max_speech_ms=cfg.silero_max_speech_ms,
            window_size=cfg.silero_window_size,
        )
    raise ValueError(f"unsupported VAD backend: {cfg.backend}")
