from __future__ import annotations

import importlib.machinery
import logging
import os
import re
import sys
import threading
import types
from pathlib import Path

import numpy as np

from ..config import AsrConfig
from ..lm import MixedNgramLM
from .base import ASRResult

logger = logging.getLogger(__name__)


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
        self._lm = None
        if cfg.lm_path:
            lm_path = Path(cfg.lm_path).expanduser()
            if lm_path.exists():
                self._lm = MixedNgramLM.load(lm_path)
            else:
                logger.warning("LM not found at %s; falling back to AED 1-best", lm_path)

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

    def _transcribe_nbest(self, samples: np.ndarray, sample_rate: int) -> list[dict]:
        import torch

        recognizer = self._recognizer
        feats, lengths, _, _, _ = recognizer.feat_extractor(
            [(sample_rate, samples)], ["utt"]
        )
        if feats is None:
            return []
        if self.cfg.use_gpu:
            feats, lengths = feats.cuda(), lengths.cuda()
            if self.cfg.use_half:
                if torch.cuda.is_bf16_supported():
                    feats = feats.bfloat16()
                else:
                    feats = feats.half()
        nbest = max(int(self.cfg.nbest), 1)
        hyps = recognizer.model.transcribe(
            feats,
            lengths,
            self.cfg.beam_size,
            nbest,
            self.cfg.decode_max_len,
            self.cfg.softmax_smoothing,
            self.cfg.aed_length_penalty,
            self.cfg.eos_penalty,
            False,
            recognizer.elm,
            self.cfg.elm_weight,
        )
        if not hyps:
            return []
        candidates = []
        for rank, hyp in enumerate(hyps[0]):
            ids = [int(token) for token in hyp["yseq"].cpu()]
            text = re.sub(r"(<blank>)|(<sil>)", "", recognizer.tokenizer.detokenize(ids))
            candidates.append(
                {
                    "text": text.lower(),
                    "confidence": float(hyp["confidence"].cpu()),
                    "rank": rank,
                }
            )
        return candidates

    @staticmethod
    def _is_code_switch(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text) and re.search(r"[A-Za-z]", text))

    def _rescore(self, candidates: list[dict]) -> dict:
        if not candidates:
            return {"text": "", "confidence": None, "rank": 0}
        if (
            self._lm is None
            or len(candidates) == 1
            or not self._is_code_switch(candidates[0]["text"])
        ):
            return candidates[0]
        return max(
            candidates,
            key=lambda candidate: (
                self.cfg.lm_weight * self._lm.score(candidate["text"])
                - self.cfg.rank_weight * candidate["rank"]
                + self.cfg.confidence_weight * candidate["confidence"]
            ),
        )

    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> ASRResult:
        samples = np.frombuffer(pcm, dtype=np.int16).copy()
        if samples.size == 0:
            return ASRResult(text="")
        with self._lock:
            candidates = self._transcribe_nbest(samples, sample_rate)
            best = self._rescore(candidates)
        return ASRResult(text=best["text"], confidence=best["confidence"])


def build_asr(cfg: AsrConfig) -> FireRedTorchASR:
    return FireRedTorchASR(cfg)
