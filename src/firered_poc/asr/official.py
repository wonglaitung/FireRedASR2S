from __future__ import annotations

import importlib.machinery
import os
import sys
import threading
import types
from pathlib import Path

import numpy as np

from ..config import AsrConfig
from .base import ASRResult


class FireRedTorchASR:
    """Official FireRedASR2-AED PyTorch adapter (BF16/beam/n-best)."""

    def __init__(self, cfg: AsrConfig):
        self.cfg = cfg
        self._lock = threading.Lock()

        if not cfg.model_dir:
            raise ValueError("official AED backend requires asr.model_dir")
        model_dir = Path(cfg.model_dir).expanduser()
        if not model_dir.exists():
            raise FileNotFoundError(f"official AED model_dir not found: {model_dir}")

        repo_path = cfg.repo_path or os.environ.get("FIREREDASR2S_HOME", "")
        if repo_path:
            repo = Path(repo_path).expanduser()
            if not repo.exists():
                raise FileNotFoundError(f"FireRedASR2S repo_path not found: {repo}")
            # Import the self-contained fireredasr2 package directly so the
            # optional VAD/LID/Punc dependencies are not required.
            package_dir = repo / "fireredasr2s"
            sys.path.insert(0, str(package_dir if package_dir.exists() else repo))

        self._install_torchaudio_stub()

        try:
            from fireredasr2 import FireRedAsr2, FireRedAsr2Config
        except ImportError:
            try:
                from fireredasr2s.fireredasr2 import FireRedAsr2, FireRedAsr2Config
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "official FireRedASR2 is not installed. Clone the upstream repo, "
                    "set FIREREDASR2S_HOME, or install it in the active environment."
                ) from exc

        asr_config = FireRedAsr2Config(
            use_gpu=cfg.use_gpu,
            use_half=cfg.use_half,
            beam_size=cfg.beam_size,
            nbest=cfg.nbest,
            decode_max_len=cfg.decode_max_len,
            softmax_smoothing=cfg.softmax_smoothing,
            aed_length_penalty=cfg.aed_length_penalty,
            eos_penalty=cfg.eos_penalty,
            return_timestamp=False,
            elm_dir=cfg.elm_dir,
            elm_weight=cfg.elm_weight,
        )
        self._recognizer = FireRedAsr2.from_pretrained("aed", str(model_dir), asr_config)

    @staticmethod
    def _install_torchaudio_stub() -> None:
        """Allow timestamp-free inference when torchaudio is unavailable."""
        try:
            import torchaudio  # noqa: F401
            return
        except Exception:
            sys.modules.pop("torchaudio", None)
        module = types.ModuleType("torchaudio")
        module.__spec__ = importlib.machinery.ModuleSpec("torchaudio", loader=None)
        module.__version__ = "0.0.0-stub"
        module.functional = types.SimpleNamespace()
        sys.modules["torchaudio"] = module

    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> ASRResult:
        samples = np.frombuffer(pcm, dtype=np.int16).copy()
        if samples.size == 0:
            return ASRResult(text="")
        with self._lock:
            results = self._recognizer.transcribe(
                ["utt"], [(sample_rate, samples)]
            )
        if not results:
            return ASRResult(text="")
        return ASRResult(
            text=results[0].get("text", ""),
            confidence=results[0].get("confidence"),
        )


def build_asr(cfg: AsrConfig) -> FireRedTorchASR:
    return FireRedTorchASR(cfg)
