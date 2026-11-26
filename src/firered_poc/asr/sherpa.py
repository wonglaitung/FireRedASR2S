from __future__ import annotations

import threading

from ..audio import int16_to_float
from ..config import AsrConfig
from .base import ASRResult


class SherpaFireRedASR:
    """FireRedASR2 Adapter backed by sherpa-onnx (CTC or AED ONNX)."""

    def __init__(self, cfg: AsrConfig):
        try:
            import sherpa_onnx
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "sherpa-onnx is required for the POC. "
                "Install it with: python3 -m pip install --user sherpa-onnx"
            ) from exc

        self.cfg = cfg
        self._lock = threading.Lock()
        backend = cfg.backend.lower()

        if backend in {"firered_ctc", "ctc"}:
            if not cfg.model or not cfg.tokens:
                raise ValueError("CTC backend requires asr.model and asr.tokens")
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_fire_red_asr_ctc(
                model=cfg.model,
                tokens=cfg.tokens,
                num_threads=cfg.num_threads,
                provider=cfg.provider,
            )
        elif backend in {"firered_aed", "aed"}:
            if not (cfg.encoder and cfg.decoder and cfg.tokens):
                raise ValueError("AED backend requires asr.encoder, asr.decoder and asr.tokens")
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_fire_red_asr(
                encoder=cfg.encoder,
                decoder=cfg.decoder,
                tokens=cfg.tokens,
                num_threads=cfg.num_threads,
                provider=cfg.provider,
            )
        else:
            raise ValueError(f"unsupported ASR backend: {cfg.backend}")

    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> ASRResult:
        samples = int16_to_float(pcm)
        if samples.size == 0:
            return ASRResult(text="")
        with self._lock:
            stream = self._recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples.tolist())
            self._recognizer.decode_stream(stream)
            text = stream.result.text.strip()
        return ASRResult(text=text)


def build_asr(cfg: AsrConfig) -> SherpaFireRedASR:
    return SherpaFireRedASR(cfg)
